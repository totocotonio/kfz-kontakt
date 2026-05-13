import os
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from config import settings
import shutil

def ensure_upload_dir():
    """Erstellt das Upload-Verzeichnis, falls nicht vorhanden"""
    upload_path = Path(settings.UPLOAD_DIR)
    upload_path.mkdir(parents=True, exist_ok=True)

def save_vehicle_image(file: UploadFile, unique_id: str) -> str:
    """
    Speichert das Fahrzeugbild auf der Festplatte
    Returns: Pfad zum Bild (z.B. /uploads/{unique_id}/vehicle.jpg)
    """
    ensure_upload_dir()

    # Prüfe Dateigröße
    if file.size and file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Datei zu groß. Maximum: {settings.MAX_FILE_SIZE / 1024 / 1024:.0f}MB"
        )

    # Erstelle Verzeichnis für diesen QR-Code
    qr_dir = Path(settings.UPLOAD_DIR) / unique_id
    qr_dir.mkdir(parents=True, exist_ok=True)

    # Bestimme Dateityp und Speicherpfad
    allowed_extensions = [".jpg", ".jpeg", ".png", ".webp"]
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dateityp nicht erlaubt. Erlaubte Typen: {', '.join(allowed_extensions)}"
        )

    # Speichere mit standardisierten Namen
    file_path = qr_dir / "vehicle.jpg"

    try:
        with open(file_path, "wb") as f:
            content = file.file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Speichern der Datei: {str(e)}"
        )

    # Gebe relativen Pfad zurück
    return f"/uploads/{unique_id}/vehicle.jpg"

def delete_vehicle_image(unique_id: str) -> bool:
    """
    Löscht das Fahrzeugbild und das Verzeichnis
    Returns: True wenn erfolgreich, False wenn nicht vorhanden
    """
    qr_dir = Path(settings.UPLOAD_DIR) / unique_id

    if not qr_dir.exists():
        return False

    try:
        shutil.rmtree(qr_dir)
        return True
    except Exception:
        return False

def get_vehicle_image_path(unique_id: str) -> str | None:
    """
    Gibt den Dateipfad zum Fahrzeugbild zurück, wenn vorhanden
    Returns: Vollständiger Pfad oder None
    """
    file_path = Path(settings.UPLOAD_DIR) / unique_id / "vehicle.jpg"

    if file_path.exists() and file_path.is_file():
        return str(file_path)

    return None
