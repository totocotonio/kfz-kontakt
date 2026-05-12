from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import QRCode, Message, Category
from database import get_db
from pydantic import BaseModel
from services.telegram_service import TelegramService
import asyncio

router = APIRouter(prefix="/api", tags=["scanner"])

class MessageSubmit(BaseModel):
    sender_name: str
    sender_contact: str = None
    category_id: int = None
    message: str

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
