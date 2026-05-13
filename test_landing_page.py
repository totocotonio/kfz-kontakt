#!/usr/bin/env python3
"""
Test-Script zum Überprüfen und Beheben des Landing Page Problems
"""
import sys
sys.path.insert(0, './backend')

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from backend.database import SessionLocal
from backend.models import QRCode
from backend.config import settings
import os

print(f"[DIR] UPLOAD_DIR: {settings.UPLOAD_DIR}")

# Erstelle uploads Verzeichnis
upload_path = Path(settings.UPLOAD_DIR)
upload_path.mkdir(parents=True, exist_ok=True)
print(f"[OK] Upload-Verzeichnis erstellt: {upload_path}")

# Öffne Datenbank
db = SessionLocal()

try:
    # Finde den neuesten QR-Code (der mit der ID d0be11ae-9dd oder einen beliebigen)
    qr_codes = db.query(QRCode).all()
    print(f"\n[DB] QR-Codes in Datenbank: {len(qr_codes)}")

    if qr_codes:
        latest_qr = qr_codes[-1]
        print(f"\n[QR] Letzter QR-Code:")
        print(f"   ID: {latest_qr.id}")
        print(f"   unique_id: {latest_qr.unique_id}")
        print(f"   label: {latest_qr.label}")
        print(f"   license_plate: {latest_qr.license_plate}")
        print(f"   vehicle_image_path (BEFORE): {latest_qr.vehicle_image_path}")

        # Erstelle ein Test-Fahrzeugbild
        unique_id = latest_qr.unique_id
        qr_dir = Path(settings.UPLOAD_DIR) / unique_id
        qr_dir.mkdir(parents=True, exist_ok=True)

        # Erstelle ein einfaches Test-Bild
        img = Image.new('RGB', (400, 300), color='lightblue')
        draw = ImageDraw.Draw(img)

        # Schreibe Text
        try:
            # Versuche, eine Standard-Schriftart zu nutzen
            font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()

        draw.text((50, 100), "Test Fahrzeugbild", fill='black', font=font)
        draw.text((50, 150), f"Kennzeichen: {latest_qr.license_plate}", fill='black', font=font)

        # Speichere Bild
        image_path = qr_dir / "vehicle.jpg"
        img.save(image_path, 'JPEG')
        print(f"\n[IMG] Test-Bild erstellt: {image_path}")

        # Aktualisiere Datenbank
        db_image_path = f"/uploads/{unique_id}/vehicle.jpg"
        latest_qr.vehicle_image_path = db_image_path
        db.commit()

        print(f"[OK] Datenbank aktualisiert:")
        print(f"   vehicle_image_path (AFTER): {latest_qr.vehicle_image_path}")

        print(f"\n[URL] Test-URL zum Scannen:")
        print(f"   http://localhost:8000/qr/{unique_id}")
        print(f"\n[TIP] Wenn die Landing Page nicht angezeigt wird, pruefe:")
        print(f"   1. Server muss neu gestartet werden!")
        print(f"   2. /uploads/{unique_id}/vehicle.jpg sollte existieren")
        print(f"   3. QR-Code muss vehicle_image_path in DB haben")

    else:
        print("\n[ERR] Keine QR-Codes in der Datenbank!")

finally:
    db.close()
