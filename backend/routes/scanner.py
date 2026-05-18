from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from models import QRCode, Message, Category, User
from database import get_db
from pydantic import BaseModel
from services.telegram_service import TelegramService
from services.twilio_service import twilio_service
from services.tracking_service import tracking_service
from config import settings
from slowapi import Limiter
from slowapi.util import get_remote_address
import asyncio
import logging
import json

limiter = Limiter(key_func=get_remote_address)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["scanner"])

class MessageSubmit(BaseModel):
    sender_name: str
    sender_contact: str = None
    category_id: int = None
    message: str

class ContactRequest(BaseModel):
    message_id: int

class TelegramChatRegister(BaseModel):
    chat_id: str
    username: str = None

class ScanTrackingData(BaseModel):
    latitude: float = None
    longitude: float = None
    accuracy: float = None

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

@router.post("/qr/{unique_id}/track")
def track_qr_scan(unique_id: str, data: ScanTrackingData, request: Request, db: Session = Depends(get_db)):
    """
    Registriere QR-Code Scan mit Geolocation und Device-Informationen
    """
    try:
        # Verifiziere QR-Code existiert
        qr = db.query(QRCode).filter(QRCode.unique_id == unique_id).first()
        if not qr:
            logger.warning(f"Track: QR-Code {unique_id} nicht gefunden")
            return {"status": "error", "message": "QR-Code nicht gefunden"}

        # Extrahiere User-Agent und IP
        user_agent = request.headers.get("user-agent", "")
        ip_address = tracking_service.extract_ip_from_request(request)

        # Parse User-Agent
        device_type, browser_name = tracking_service.parse_user_agent(user_agent)

        # Extrahiere Geolocation aus Request Header (X-Geoip Fallback)
        country = request.headers.get("CF-IPCountry")  # Cloudflare Geolocation
        city = None

        # Erstelle Scan-Record
        scan = tracking_service.create_scan_record(
            db=db,
            qr_code_id=qr.id,
            latitude=data.latitude,
            longitude=data.longitude,
            accuracy=data.accuracy,
            ip_address=ip_address,
            country=country,
            city=city,
            user_agent=user_agent,
            device_type=device_type,
            browser_name=browser_name,
            referrer=request.headers.get("referer"),
            is_returning_visitor=False  # TODO: Implementiere Cookie-basierte Returning Visitor Detection
        )

        if not scan:
            return {"status": "error", "message": "Fehler beim Speichern des Scans"}

        logger.info(f"QR Scan tracked: {unique_id} from {device_type}/{browser_name}/{country}")
        return {"status": "success", "scan_id": scan.id}

    except Exception as e:
        logger.error(f"Error tracking scan: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}

@router.post("/qr/{unique_id}/message")
@limiter.limit("5/minute")
async def submit_message(unique_id: str, data: MessageSubmit, request: Request, db: Session = Depends(get_db)):
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

    # Telegram-Benachrichtigung im Hintergrund senden
    try:
        logger.info(f"Sending Telegram notification for message {message.id}...")
        await TelegramService.send_new_message_notification(
            qr_label=qr.label or f"QR-{qr.id}",
            sender=data.sender_name or "Anonym",
            sender_contact=data.sender_contact,
            message=data.message,
            category=category_name,
            vehicle_image_path=qr.vehicle_image_path,
            db=db
        )
        logger.info(f"Telegram notification sent for message {message.id}")
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {str(e)}", exc_info=True)

    return {"status": "success", "message_id": message.id}

@router.delete("/message/{message_id}")
def delete_message(message_id: int, db: Session = Depends(get_db)):
    """Lösche eine Nachricht aus der Datenbank"""
    logger.info(f"Delete message: message_id={message_id}")

    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Nachricht nicht gefunden")

    try:
        db.delete(message)
        db.commit()
        logger.info(f"Message {message_id} deleted successfully")
        return {"status": "success", "message": f"Nachricht {message_id} gelöscht"}
    except Exception as e:
        logger.error(f"Error deleting message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fehler beim Löschen: {str(e)}")

@router.post("/qr/{unique_id}/contact/sms")
def send_sms_contact(unique_id: str, data: ContactRequest, db: Session = Depends(get_db)):
    """SMS-Versand via Twilio für anonyme Kontaktmöglichkeit"""
    logger.info(f"SMS contact: message_id={data.message_id}")

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
    logger.info(f"SMS Debug - message.category_id: {message.category_id}, message.category: {message.category}")
    category_text = f"[{message.category.name}] " if message.category else ""
    sender_info = f" ({message.sender_name})" if message.sender_name else ""
    contact_info = f" - {message.sender_contact}" if message.sender_contact else ""
    sms_text = f"KFZ Kontakt: {category_text}{message.message}{sender_info}{contact_info}"
    logger.info(f"SMS Text: {sms_text}")

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
    logger.info(f"WhatsApp contact: message_id={data.message_id}")

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
    logger.info(f"WhatsApp Debug - message.category_id: {message.category_id}, message.category: {message.category}")
    category_text = f"[{message.category.name}] " if message.category else ""
    sender_info = f" ({message.sender_name})" if message.sender_name else ""
    contact_info = f" - {message.sender_contact}" if message.sender_contact else ""
    whatsapp_text = f"KFZ Kontakt: {category_text}{message.message}{sender_info}{contact_info}"
    logger.info(f"WhatsApp Text: {whatsapp_text}")

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

@router.post("/telegram/register")
def register_telegram_chat(data: TelegramChatRegister, db: Session = Depends(get_db)):
    """Registriere Telegram Chat ID für den Admin-Benutzer"""
    try:
        logger.info(f"Registriere Telegram Chat ID: {data.chat_id}")

        # Finde oder erstelle Admin-User
        user = db.query(User).filter(User.name == "Admin").first()

        if not user:
            user = User(
                name="Admin",
                telegram_chat_id=data.chat_id,
                telegram_username=data.username
            )
            db.add(user)
            logger.info(f"Neuer Admin-User erstellt mit Chat ID: {data.chat_id}")
        else:
            user.telegram_chat_id = data.chat_id
            if data.username:
                user.telegram_username = data.username
            logger.info(f"Admin-User aktualisiert mit Chat ID: {data.chat_id}")

        db.commit()
        db.refresh(user)

        return {
            "status": "success",
            "message": f"Telegram Chat ID registriert: {data.chat_id}",
            "user_id": user.id
        }
    except Exception as e:
        logger.error(f"Fehler bei Telegram-Registrierung: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Registrierungsfehler: {str(e)}")

@router.post("/webhooks/telegram")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    """Webhook für Telegram Bot Updates (z.B. /start Befehl)"""
    try:
        data = await request.json()
        logger.info(f"Telegram Webhook empfangen: {json.dumps(data, indent=2)}")

        # Extrahiere Chat ID und Username
        if "message" in data:
            message = data["message"]
            chat_id = str(message.get("chat", {}).get("id"))
            username = message.get("chat", {}).get("username", "")
            text = message.get("text", "")

            logger.info(f"Telegram Message: chat_id={chat_id}, username={username}, text={text}")

            # Wenn /start Befehl
            if text and text.startswith("/start"):
                logger.info(f"Registriere Chat ID automatisch: {chat_id}")

                # Finde oder erstelle Admin-User
                user = db.query(User).filter(User.name == "Admin").first()

                if not user:
                    user = User(
                        name="Admin",
                        telegram_chat_id=chat_id,
                        telegram_username=username
                    )
                    db.add(user)
                    logger.info(f"Neuer Admin-User erstellt mit Chat ID: {chat_id}")
                else:
                    user.telegram_chat_id = chat_id
                    if username:
                        user.telegram_username = username
                    logger.info(f"Admin-User aktualisiert mit Chat ID: {chat_id}")

                db.commit()

                # Sende Bestätigungs-Nachricht zurück
                await TelegramService.send_message(
                    f"✅ Deine Telegram Chat ID wurde registriert!\n\nChat ID: {chat_id}\n\nDu erhältst jetzt Benachrichtigungen über neue Nachrichten vom QR-Code.",
                    chat_id=chat_id
                )

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Fehler bei Telegram Webhook: {str(e)}")
        return {"status": "error", "message": str(e)}
