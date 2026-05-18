from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import Message, QRCode, User, Category, QRCodeScan
from database import get_db
from pydantic import BaseModel
from services.tracking_service import tracking_service

router = APIRouter(prefix="/api", tags=["dashboard"])

class MessageUpdate(BaseModel):
    read: bool = None
    responded: bool = None

class ContactUpdate(BaseModel):
    phone_number: str

class ContactMethodsUpdate(BaseModel):
    enable_telegram: bool = True
    enable_sms: bool = False
    enable_whatsapp: bool = False

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

    # Hole den zeitlich nächsten Scan zu dieser Nachricht
    scan = None
    if message.qr_code_id:
        from datetime import timedelta

        # Hole alle Scans für diesen QR-Code
        all_scans = db.query(QRCodeScan)\
            .filter(QRCodeScan.qr_code_id == message.qr_code_id)\
            .all()

        # Finde den Scan mit der kleinsten zeitlichen Differenz
        closest_scan = None
        min_diff = timedelta.max

        for s in all_scans:
            diff = abs((s.created_at - message.created_at).total_seconds())
            if diff < min_diff.total_seconds():
                min_diff = timedelta(seconds=diff)
                closest_scan = s

        if closest_scan:
            scan = {
                "id": closest_scan.id,
                "latitude": closest_scan.latitude,
                "longitude": closest_scan.longitude,
                "country": closest_scan.country,
                "city": closest_scan.city,
                "device_type": closest_scan.device_type,
                "browser_name": closest_scan.browser_name,
                "created_at": closest_scan.created_at.isoformat(),
                "accuracy": closest_scan.accuracy
            }

    return {
        "id": message.id,
        "qr_label": message.qr_code.label if message.qr_code else "N/A",
        "sender_name": message.sender_name or "Anonym",
        "sender_contact": message.sender_contact,
        "category": message.category.name if message.category else None,
        "message": message.message,
        "read": message.read,
        "responded": message.responded,
        "created_at": message.created_at.isoformat(),
        "scan": scan
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

    # Zähle Total Scans über alle QR-Codes
    user_qr_codes = db.query(QRCode).filter(QRCode.user_id == user.id).all()
    total_scans = 0
    for qr in user_qr_codes:
        scans = db.query(QRCodeScan).filter(QRCodeScan.qr_code_id == qr.id).count()
        total_scans += scans

    # Conversion Rate: Messages / Scans (max 100%)
    conversion_rate = 0
    if total_scans > 0:
        conversion_rate = min(100, round((total_messages / total_scans) * 100, 2))

    return {
        "total_messages": total_messages,
        "unread_messages": unread_messages,
        "responded_messages": responded_messages,
        "total_scans": total_scans,
        "conversion_rate": conversion_rate
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

@router.get("/dashboard/contact")
def get_contact(db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")

    return {
        "phone_number": user.phone_number or "",
        "enable_telegram": user.enable_telegram,
        "enable_sms": user.enable_sms,
        "enable_whatsapp": user.enable_whatsapp
    }

@router.patch("/dashboard/contact")
def update_contact(data: ContactUpdate, db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")

    user.phone_number = data.phone_number
    db.commit()

    return {"status": "success", "phone_number": user.phone_number}

@router.patch("/dashboard/contact-methods")
def update_contact_methods(data: ContactMethodsUpdate, db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")

    user.enable_telegram = data.enable_telegram
    user.enable_sms = data.enable_sms
    user.enable_whatsapp = data.enable_whatsapp
    db.commit()

    return {"status": "success"}

@router.get("/dashboard/qr-stats/{qr_id}")
def get_qr_stats(qr_id: int, db: Session = Depends(get_db)):
    """Hole Scan-Statistiken für einen spezifischen QR-Code"""
    qr = db.query(QRCode).filter(QRCode.id == qr_id).first()
    if not qr:
        raise HTTPException(status_code=404, detail="QR-Code nicht gefunden")

    # Hole Scan-Statistiken vom TrackingService
    stats = tracking_service.get_scan_stats(db, qr_id)

    # Zähle Messages für diesen QR-Code
    messages_count = db.query(Message).filter(Message.qr_code_id == qr_id).count()

    # Conversion Rate: Messages / Scans (max 100%)
    conversion_rate = 0
    if stats["total_scans"] > 0:
        conversion_rate = min(100, round((messages_count / stats["total_scans"]) * 100, 2))

    return {
        **stats,  # Include all tracking stats
        "qr_label": qr.label,
        "messages_count": messages_count,
        "conversion_rate": conversion_rate
    }

@router.get("/whatsapp")
def get_whatsapp_public(db: Session = Depends(get_db)):
    """Öffentlicher Endpoint für WhatsApp-Nummer (keine Auth erforderlich)"""
    user = db.query(User).first()
    if not user:
        return {"whatsapp_number": ""}

    return {"whatsapp_number": user.whatsapp_number or ""}
