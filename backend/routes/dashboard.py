from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import Message, QRCode, User, Category
from database import get_db
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["dashboard"])

class MessageUpdate(BaseModel):
    read: bool = None
    responded: bool = None

class PhoneUpdate(BaseModel):
    phone_number: str

class WhatsAppUpdate(BaseModel):
    whatsapp_number: str

@router.get("/dashboard/messages")
def get_messages(db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")

    messages = db.query(Message).filter(Message.user_id == user.id).order_by(Message.created_at.desc()).all()
    return {
        "messages": [
            {
                "id": msg.id,
                "qr_label": msg.qr_code.label if msg.qr_code else "N/A",
                "sender_name": msg.sender_name or "Anonym",
                "sender_contact": msg.sender_contact,
                "category": msg.category.name if msg.category else None,
                "message": msg.message,
                "read": msg.read,
                "responded": msg.responded,
                "created_at": msg.created_at.isoformat()
            }
            for msg in messages
        ]
    }

@router.get("/dashboard/messages/{message_id}")
def get_message(message_id: int, db: Session = Depends(get_db)):
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Nachricht nicht gefunden")

    message.read = True
    db.commit()

    return {
        "id": message.id,
        "qr_label": message.qr_code.label if message.qr_code else "N/A",
        "sender_name": message.sender_name or "Anonym",
        "sender_contact": message.sender_contact,
        "category": message.category.name if message.category else None,
        "message": message.message,
        "read": message.read,
        "responded": message.responded,
        "created_at": message.created_at.isoformat()
    }

@router.patch("/dashboard/messages/{message_id}")
def update_message(message_id: int, data: MessageUpdate, db: Session = Depends(get_db)):
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Nachricht nicht gefunden")

    if data.read is not None:
        message.read = data.read
    if data.responded is not None:
        message.responded = data.responded

    db.commit()
    return {"status": "success"}

@router.get("/dashboard/stats")
def get_stats(db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")

    total_messages = db.query(Message).filter(Message.user_id == user.id).count()
    unread_messages = db.query(Message).filter(
        Message.user_id == user.id,
        Message.read == False
    ).count()
    responded_messages = db.query(Message).filter(
        Message.user_id == user.id,
        Message.responded == True
    ).count()

    return {
        "total_messages": total_messages,
        "unread_messages": unread_messages,
        "responded_messages": responded_messages
    }

@router.get("/dashboard/categories")
def get_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).all()
    return {
        "categories": [
            {
                "id": cat.id,
                "name": cat.name,
                "description": cat.description,
                "icon": cat.icon
            }
            for cat in categories
        ]
    }

@router.get("/dashboard/phone")
def get_phone(db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")

    return {"phone_number": user.phone_number or ""}

@router.patch("/dashboard/phone")
def update_phone(data: PhoneUpdate, db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")

    user.phone_number = data.phone_number
    db.commit()

    return {"status": "success", "phone_number": user.phone_number}

@router.get("/dashboard/whatsapp")
def get_whatsapp(db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")

    return {"whatsapp_number": user.whatsapp_number or ""}

@router.patch("/dashboard/whatsapp")
def update_whatsapp(data: WhatsAppUpdate, db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")

    user.whatsapp_number = data.whatsapp_number
    db.commit()

    return {"status": "success", "whatsapp_number": user.whatsapp_number}

@router.get("/whatsapp")
def get_whatsapp_public(db: Session = Depends(get_db)):
    """Öffentlicher Endpoint für WhatsApp-Nummer (keine Auth erforderlich)"""
    user = db.query(User).first()
    if not user:
        return {"whatsapp_number": ""}

    return {"whatsapp_number": user.whatsapp_number or ""}
