from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from models import QRCode, Message, Category, User
from database import get_db
from pydantic import BaseModel
from services.telegram_service import TelegramService
from services.twilio_service import twilio_service
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["scanner"])

class MessageSubmit(BaseModel):
    sender_name: str
    sender_contact: str = None
    category_id: int = None
    message: str

class ContactRequest(BaseModel):
    message_id: int

@router.get("/qr/{unique_id}/info")
def get_qr_info(unique_id: str, db: Session = Depends(get_db)):
    qr = db.query(QRCode).filter(QRCode.unique_id == unique_id).first()
    if not qr:
        raise HTTPException(status_code=404, detail="QR-Code nicht gefunden")

    categories = db.query(Category).all()
    return {
        "qr_id": qr.id,
        "label": qr.label,
        "categories": [{"id": c.id, "name": c.name} for c in categories]
    }

@router.post("/qr/{unique_id}/message")
async def submit_message(unique_id: str, data: MessageSubmit, db: Session = Depends(get_db)):
    qr = db.query(QRCode).filter(QRCode.unique_id == unique_id).first()
    if not qr:
        raise HTTPException(status_code=404, detail="QR-Code nicht gefunden")

    category = None
    if data.category_id:
        category = db.query(Category).filter(Category.id == data.category_id).first()

    message = Message(
        qr_code_id=qr.id,
        user_id=qr.user_id,
        category_id=data.category_id,
        sender_name=data.sender_name,
        sender_contact=data.sender_contact,
        message=data.message
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    category_name = category.name if category else "Allgemein"
    await TelegramService.send_new_message_notification(
        qr_label=qr.label or f"QR-{qr.id}",
        sender=data.sender_name or "Anonym",
        message=data.message,
        category=category_name
    )

    return {"status": "success", "message_id": message.id}

@router.post("/qr/{unique_id}/contact/sms")
def send_sms_contact(unique_id: str, data: ContactRequest, db: Session = Depends(get_db)):
    """SMS-Versand via Twilio für anonyme Kontaktmöglichkeit"""
    # QR-Code finden
    qr = db.query(QRCode).filter(QRCode.unique_id == unique_id).first()
    if not qr:
        raise HTTPException(status_code=404, detail="QR-Code nicht gefunden")

    # Message finden
    message = db.query(Message).filter(Message.id == data.message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Nachricht nicht gefunden")

    # Admin-Telefonnummer holen
    user = db.query(User).filter(User.id == qr.user_id).first()
    if not user or not user.phone_number:
        raise HTTPException(status_code=400, detail="Admin hat keine Telefonnummer hinterlegt")

    # Nachrichtentext für SMS
    sender_info = f" ({message.sender_name})" if message.sender_name else ""
    contact_info = f" - Kontakt: {message.sender_contact}" if message.sender_contact else ""
    sms_text = f"KFZ Kontakt: {message.message}{sender_info}{contact_info}"

    # SMS versenden
    result = twilio_service.send_sms(
        message_id=data.message_id,
        phone_number=user.phone_number,
        message_text=sms_text,
        db=db
    )

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return result

@router.post("/qr/{unique_id}/contact/whatsapp")
def send_whatsapp_contact(unique_id: str, data: ContactRequest, db: Session = Depends(get_db)):
    """WhatsApp-Versand via Twilio für anonyme Kontaktmöglichkeit"""
    # QR-Code finden
    qr = db.query(QRCode).filter(QRCode.unique_id == unique_id).first()
    if not qr:
        raise HTTPException(status_code=404, detail="QR-Code nicht gefunden")

    # Message finden
    message = db.query(Message).filter(Message.id == data.message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Nachricht nicht gefunden")

    # Admin-Telefonnummer holen
    user = db.query(User).filter(User.id == qr.user_id).first()
    if not user or not user.phone_number:
        raise HTTPException(status_code=400, detail="Admin hat keine Telefonnummer hinterlegt")

    # Nachrichtentext für WhatsApp
    sender_info = f" ({message.sender_name})" if message.sender_name else ""
    contact_info = f" - Kontakt: {message.sender_contact}" if message.sender_contact else ""
    whatsapp_text = f"KFZ Kontakt: {message.message}{sender_info}{contact_info}"

    # WhatsApp versenden
    result = twilio_service.send_whatsapp(
        message_id=data.message_id,
        phone_number=user.phone_number,
        message_text=whatsapp_text,
        db=db
    )

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return result

@router.post("/webhooks/twilio")
async def twilio_webhook(request: Request, db: Session = Depends(get_db)):
    """Webhook für Twilio Status-Updates (SMS/WhatsApp Delivery)"""
    try:
        form_data = await request.form()
        sms_sid = form_data.get("MessageSid")
        status = form_data.get("MessageStatus")

        if sms_sid and status:
            twilio_service.handle_webhook(sms_sid, status, db)
            logger.info(f"Twilio Webhook: {sms_sid} → {status}")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Fehler bei Twilio Webhook: {str(e)}")
        return {"status": "error", "message": str(e)}
