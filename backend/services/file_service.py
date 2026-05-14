import os
import shutil
from pathlib import Path
from fastapi import UploadFile, HTTPException
from config import settings
from PIL import Image
import io

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def _get_vehicle_folder(unique_id: str) -> Path:
    """Erstellt und gibt den Pfad zum Fahrzeug-Ordner zurück"""
    vehicle_folder = Path(settings.UPLOAD_DIR) / unique_id
    vehicle_folder.mkdir(parents=True, exist_ok=True)
    return vehicle_folder

def _validate_image(file_content: bytes) -> bool:
    """Validiert, dass die Datei ein gültiges Bild ist"""
    try:
        img = Image.open(io.BytesIO(file_content))
        img.verify()
        return True
    except Exception:
        return False

def save_vehicle_image(file: UploadFile, unique_id: str) -> str:
    """
    Speichert das Fahrzeugbild im Dateisystem

    Args:
        file: UploadFile Objekt
        unique_id: Eindeutige QR-Code ID

    Returns:
        Relativer Pfad zur gespeicherten Datei

    Raises:
        HTTPException: Bei ungültigen Dateiarten oder zu großen Dateien
    """
    # Validiere Dateityp
    if not file.filename:
        raise HTTPException(status_code=400, detail="Dateiname fehlt")

    file_ext = file.filename.rsplit(".", 1)[-1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Nur PNG, JPG oder WebP erlaubt"
        )

    # Lese Dateiinhalt
    try:
        file_content = file.file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Fehler beim Lesen der Datei: {str(e)}")

    # Validiere Dateigröße
    if len(file_content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Datei zu groß (max. {settings.MAX_FILE_SIZE / 1024 / 1024:.0f}MB)"
        )

    # Validiere dass es ein echtes Bild ist
    if not _validate_image(file_content):
        raise HTTPException(status_code=400, detail="Ungültige oder beschädigte Bilddatei")

    # Erstelle Fahrzeug-Ordner
    vehicle_folder = _get_vehicle_folder(unique_id)

    # Speichere Datei (immer als vehicle.jpg, unabhängig vom Original-Format)
    filename = "vehicle.jpg"
    filepath = vehicle_folder / filename

    try:
        # Konvertiere zu JPG falls nötig (für Standardisierung)
        img = Image.open(io.BytesIO(file_content))
        if img.mode in ("RGBA", "LA", "P"):
            # Konvertiere transparent zu weiß
            rgb_img = Image.new("RGB", img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            rgb_img.save(filepath, "JPEG", quality=90)
        else:
            img.save(filepath, "JPEG", quality=90)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler beim Speichern: {str(e)}")

    # Gebe relativen Pfad zurück
    return f"/uploads/{unique_id}/{filename}"

def delete_vehicle_image(unique_id: str) -> bool:
    """
    Löscht den kompletten Fahrzeug-Ordner

    Args:
        unique_id: Eindeutige QR-Code ID

    Returns:
        True wenn erfolgreich gelöscht, False wenn nicht vorhanden
    """
    vehicle_folder = Path(settings.UPLOAD_DIR) / unique_id

    if not vehicle_folder.exists():
        return False

    try:
        shutil.rmtree(vehicle_folder)
        return True
    except Exception as e:
        print(f"Fehler beim Löschen von {vehicle_folder}: {str(e)}")
        return False

def get_vehicle_image_path(unique_id: str) -> str:
    """
    Gibt den absoluten Dateipfad zum Fahrzeugbild zurück

    Args:
        unique_id: Eindeutige QR-Code ID

    Returns:
        Absoluter Dateipfad oder None
    """
    filepath = Path(settings.UPLOAD_DIR) / unique_id / "vehicle.jpg"

    if filepath.exists():
        return str(filepath)

    return None
