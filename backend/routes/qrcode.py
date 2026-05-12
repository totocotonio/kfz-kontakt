from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from models import QRCode, User
from database import get_db
from pydantic import BaseModel
from services.qr_service import QRService
from io import BytesIO
import io

router = APIRouter(prefix="/api", tags=["qrcode"])

class QRCodeCreate(BaseModel):
    label: str = "Mein Auto"
    design: str = "default"

@router.post("/qrcode/generate")
def generate_qrcode(data: QRCodeCreate, db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")

    unique_id = QRService.generate_unique_id()
    qr_code = QRCode(
        user_id=user.id,
        unique_id=unique_id,
        label=data.label,
        design=data.design
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
def get_qr_image(qr_id: int, db: Session = Depends(get_db)):
    qr = db.query(QRCode).filter(QRCode.id == qr_id).first()
    if not qr:
        raise HTTPException(status_code=404, detail="QR-Code nicht gefunden")

    base_url = "http://localhost:8000"
    qr_data = f"{base_url}/qr/{qr.unique_id}"

    qr_image = QRService.generate_qr_code(qr_data)
    sticker = QRService.generate_sticker_with_design(
        qr_image,
        design=qr.design,
        label=qr.label
    )

    img_io = io.BytesIO()
    sticker.save(img_io, "PNG")
    img_io.seek(0)

    return FileResponse(
        io.BytesIO(img_io.getvalue()),
        media_type="image/png",
        filename=f"qr_sticker_{qr.id}.png"
    )

@router.get("/qrcodes/list")
def list_qrcodes(db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")

    qr_codes = db.query(QRCode).filter(QRCode.user_id == user.id).all()
    return {
        "qrcodes": [
            {
                "id": qr.id,
                "label": qr.label,
                "unique_id": qr.unique_id,
                "design": qr.design,
                "created_at": qr.created_at
            }
            for qr in qr_codes
        ]
    }
