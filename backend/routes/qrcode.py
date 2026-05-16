# -*- coding: utf-8 -*-
# © 2026 Torsten Michaely - KFZ Kontakt QR-Code System
# Mit WhatsApp-Integration für flexible Kontaktmöglichkeiten
# All rights reserved

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from models import QRCode, User
from database import get_db
from pydantic import BaseModel
from typing import Optional
from services.qr_service import QRService
from services.file_service import save_vehicle_image, delete_vehicle_image
from config import settings
from auth import verify_dashboard_auth
from io import BytesIO
import io

router = APIRouter(prefix="/api", tags=["qrcode"])

class QRCodeCreate(BaseModel):
    label: str = ""  # Benutzer definiert (z.B. Auto-Marke)
    title: str = "KONTAKT FAHRZEUGHALTER"
    design: str = "professional"  # Professional Design mit grüner Farbe
    background_color: str = "#1b7a4a"  # Professionelles Grün
    license_plate: Optional[str] = None
    vehicle_image_path: Optional[str] = None
    icon_type: str = "phone"
    icon_position: str = "bottom"

@router.post("/qrcode/generate")
def generate_qrcode(data: QRCodeCreate, db: Session = Depends(get_db), auth: bool = Depends(verify_dashboard_auth)):
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")

    unique_id = QRService.generate_unique_id()
    qr_code = QRCode(
        user_id=user.id,
        unique_id=unique_id,
        label=data.label,
        title=data.title,
        design=data.design,
        background_color=data.background_color,
        license_plate=data.license_plate,
        vehicle_image_path=data.vehicle_image_path,
        icon_type=data.icon_type,
        icon_position=data.icon_position
    )
    db.add(qr_code)
    db.commit()
    db.refresh(qr_code)

    return {
        "id": qr_code.id,
        "unique_id": qr_code.unique_id,
        "label": qr_code.label,
        "qr_url": f"/qr/{qr_code.unique_id}"
    }

@router.get("/qrcode/{qr_id}/image")
def get_qr_image(qr_id: int, request: Request, db: Session = Depends(get_db)):
    qr = db.query(QRCode).filter(QRCode.id == qr_id).first()
    if not qr:
        raise HTTPException(status_code=404, detail="QR-Code nicht gefunden")

    # Always use external URL for QR codes (kfz-kontakt.michaely.de)
    # This ensures QR codes work globally, not just on local network
    qr_data = f"{settings.EXTERNAL_URL}/qr/{qr.unique_id}"

    qr_image = QRService.generate_qr_code(qr_data)
    sticker = QRService.generate_sticker_with_design(
        qr_image,
        design=qr.design,
        label=qr.label,
        title=qr.title,
        background_color=qr.background_color,
        icon_type=qr.icon_type,
        icon_position=qr.icon_position
    )

    img_io = io.BytesIO()
    sticker.save(img_io, "PNG")
    img_io.seek(0)

    return StreamingResponse(
        io.BytesIO(img_io.getvalue()),
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename=qr_sticker_{qr.id}.png"}
    )

@router.get("/qrcodes/list")
def list_qrcodes(db: Session = Depends(get_db), auth: bool = Depends(verify_dashboard_auth)):
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")

    qr_codes = db.query(QRCode).filter(QRCode.user_id == user.id).all()
    return {
        "qrcodes": [
            {
                "id": qr.id,
                "label": qr.label,
                "title": qr.title,
                "unique_id": qr.unique_id,
                "design": qr.design,
                "background_color": qr.background_color,
                "icon_type": qr.icon_type,
                "icon_position": qr.icon_position,
                "license_plate": qr.license_plate,
                "vehicle_image_path": qr.vehicle_image_path,
                "created_at": qr.created_at
            }
            for qr in qr_codes
        ]
    }

@router.patch("/qrcode/{qr_id}")
def update_qrcode(qr_id: int, data: QRCodeCreate, db: Session = Depends(get_db), auth: bool = Depends(verify_dashboard_auth)):
    qr = db.query(QRCode).filter(QRCode.id == qr_id).first()
    if not qr:
        raise HTTPException(status_code=404, detail="QR-Code nicht gefunden")

    qr.label = data.label
    qr.title = data.title
    qr.design = data.design
    qr.background_color = data.background_color
    qr.icon_type = data.icon_type
    qr.icon_position = data.icon_position
    if data.license_plate is not None:
        qr.license_plate = data.license_plate
    db.commit()
    db.refresh(qr)

    return {"status": "success", "id": qr.id}

@router.get("/qrcode/{qr_id}")
def get_qrcode(qr_id: int, db: Session = Depends(get_db), auth: bool = Depends(verify_dashboard_auth)):
    qr = db.query(QRCode).filter(QRCode.id == qr_id).first()
    if not qr:
        raise HTTPException(status_code=404, detail="QR-Code nicht gefunden")

    return {
        "id": qr.id,
        "label": qr.label,
        "title": qr.title,
        "unique_id": qr.unique_id,
        "design": qr.design,
        "background_color": qr.background_color,
        "icon_type": qr.icon_type,
        "icon_position": qr.icon_position,
        "license_plate": qr.license_plate,
        "vehicle_image_path": qr.vehicle_image_path,
        "created_at": qr.created_at
    }

@router.post("/qrcode/{qr_id}/upload-image")
async def upload_vehicle_image(qr_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), auth: bool = Depends(verify_dashboard_auth)):
    qr = db.query(QRCode).filter(QRCode.id == qr_id).first()
    if not qr:
        raise HTTPException(status_code=404, detail="QR-Code nicht gefunden")

    try:
        # Speichere Bild
        image_path = save_vehicle_image(file, qr.unique_id)

        # Update QR-Code mit Bildpfad
        qr.vehicle_image_path = image_path
        db.commit()
        db.refresh(qr)

        return {
            "status": "success",
            "vehicle_image_path": qr.vehicle_image_path,
            "message": "Fahrzeugbild erfolgreich hochgeladen"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Fehler beim Upload: {str(e)}"
        )

@router.delete("/qrcode/{qr_id}")
def delete_qrcode(qr_id: int, db: Session = Depends(get_db), auth: bool = Depends(verify_dashboard_auth)):
    qr = db.query(QRCode).filter(QRCode.id == qr_id).first()
    if not qr:
        raise HTTPException(status_code=404, detail="QR-Code nicht gefunden")

    # Lösche Fahrzeugbild, falls vorhanden
    if qr.unique_id:
        delete_vehicle_image(qr.unique_id)

    db.delete(qr)
    db.commit()

    return {"status": "success"}
