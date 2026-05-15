import aiohttp
import requests
from config import settings
import logging
import base64
import os
from io import BytesIO

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

logger = logging.getLogger(__name__)

class TelegramService:
    @staticmethod
    def compress_image(image_data: bytes, max_width: int = 400, quality: int = 70) -> bytes:
        """Komprimiere und verkleinere ein Bild für Telegram"""
        if not HAS_PIL:
            logger.warning("PIL not available, returning original image")
            return image_data

        try:
            # Öffne Bild aus Bytes
            img = Image.open(BytesIO(image_data))

            # Konvertiere zu RGB falls RGBA
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background

            # Verkleiner Bild wenn nötig
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

            # Speichere mit Kompression
            output = BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            compressed = output.getvalue()

            logger.info(f"Image compressed: {len(image_data)} -> {len(compressed)} bytes")
            return compressed
        except Exception as e:
            logger.warning(f"Error compressing image: {e}, using original")
            return image_data
    @staticmethod
    async def send_message(message: str, chat_id: str = None, db=None):
        logger.info(f"🔵 TelegramService.send_message called - chat_id={chat_id}")

        if not settings.TELEGRAM_BOT_TOKEN:
            logger.warning("⚠️ Telegram Bot Token nicht konfiguriert")
            return False

        target_chat_id = chat_id

        # Falls keine Chat ID übergeben, versuche aus Datenbank zu laden
        if not target_chat_id and db:
            try:
                from models import User
                user = db.query(User).filter(User.name == "Admin").first()
                logger.info(f"Admin user from DB: {user}")
                if user and user.telegram_chat_id and user.telegram_chat_id != "0":
                    target_chat_id = user.telegram_chat_id
                    logger.info(f"Got chat_id from DB: {target_chat_id}")
            except Exception as e:
                logger.warning(f"Failed to get chat_id from DB: {e}")

        # Fallback auf Config-Variable (deprecated)
        if not target_chat_id:
            target_chat_id = settings.TELEGRAM_CHAT_ID
            logger.info(f"Using TELEGRAM_CHAT_ID from config: {target_chat_id}")

        if not target_chat_id or target_chat_id == "0":
            logger.warning("⚠️ Telegram Chat ID nicht konfiguriert")
            return False

        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": target_chat_id,
            "text": message,
            "parse_mode": "HTML"
        }

        try:
            logger.info(f"Sending Telegram message to {target_chat_id}...")
            # Use requests instead of aiohttp for better reliability
            response = requests.post(url, json=payload, timeout=15)
            logger.info(f"Telegram response status: {response.status_code}")
            if response.status_code == 200:
                logger.info(f"Telegram message sent successfully to {target_chat_id}")
                return True
            else:
                logger.warning(f"Telegram error: status {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Telegram Error: {e}")
            return False

    @staticmethod
    async def send_photo(photo_data: bytes, caption: str, chat_id: str = None, db=None):
        logger.info(f"📸 TelegramService.send_photo called - chat_id={chat_id}, data_size={len(photo_data) if photo_data else 0}")

        if not settings.TELEGRAM_BOT_TOKEN:
            logger.warning("⚠️ Telegram Bot Token nicht konfiguriert")
            return False

        target_chat_id = chat_id

        # Falls keine Chat ID übergeben, versuche aus Datenbank zu laden
        if not target_chat_id and db:
            try:
                from models import User
                user = db.query(User).filter(User.name == "Admin").first()
                if user and user.telegram_chat_id and user.telegram_chat_id != "0":
                    target_chat_id = user.telegram_chat_id
            except Exception as e:
                logger.warning(f"Failed to get chat_id from DB: {e}")

        # Fallback auf Config-Variable
        if not target_chat_id:
            target_chat_id = settings.TELEGRAM_CHAT_ID

        if not target_chat_id or target_chat_id == "0":
            logger.warning("⚠️ Telegram Chat ID nicht konfiguriert")
            return False

        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendPhoto"

        try:
            logger.info(f"Sending Telegram photo to {target_chat_id}...")
            # Komprimiere Bild
            compressed_data = TelegramService.compress_image(photo_data, max_width=400, quality=70)
            logger.info(f"Photo size: {len(photo_data)} -> {len(compressed_data)} bytes")
            # Sende Bild als Datei-Upload
            files = {
                'photo': ('vehicle.jpg', compressed_data, 'image/jpeg')
            }
            data = {
                'chat_id': target_chat_id,
                'caption': caption,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, files=files, data=data, timeout=15)
            logger.info(f"Telegram photo response status: {response.status_code}")
            if response.status_code == 200:
                logger.info(f"Telegram photo sent successfully to {target_chat_id}")
                return True
            else:
                logger.warning(f"Telegram photo error: status {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Telegram photo error: {e}")
            return False

    @staticmethod
    async def send_new_message_notification(qr_label: str, sender: str, message: str, category: str = None, sender_contact: str = None, vehicle_image_path: str = None, db=None):
        logger.error(f"🔔 NOTIFICATION START: qr_label={qr_label}, sender={sender}, has_image={bool(vehicle_image_path)}")
        logger.info(f"🔔 send_new_message_notification: qr_label={qr_label}, sender={sender}, contact={sender_contact}, category={category}")

        text = f"""
<b>🚗 Neue Nachricht über QR-Code: {qr_label}</b>

<b>Von:</b> {sender}
"""
        if sender_contact:
            text += f"<b>Kontakt:</b> {sender_contact}\n"

        if category:
            text += f"<b>Kategorie:</b> {category}\n"

        text += f"""
<b>Nachricht:</b>
{message}

<b>Antworte:</b> Rufe den Sender an oder antworte per WhatsApp/Telegram
        """

        # Wenn Fahrzeugbild vorhanden, versuche als Foto zu senden
        if vehicle_image_path:
            try:
                # Konstruiere lokalen Pfad zur Bilddatei
                # vehicle_image_path ist bereits relativ wie: "/uploads/975488b6-ed6/vehicle.jpg"
                # Verwende absoluten Pfad direkt statt UPLOAD_DIR
                from pathlib import Path
                image_full_path = Path("/opt/kfz-kontakt") / vehicle_image_path.lstrip('/')

                logger.info(f"Reading image from: {image_full_path}")
                if image_full_path.exists():
                    with open(image_full_path, 'rb') as f:
                        photo_data = f.read()
                    logger.info(f"Image loaded, size: {len(photo_data)} bytes")
                    result = await TelegramService.send_photo(photo_data, text, db=db)
                    # Wenn Foto-Versand fehlschlägt, fallback auf Text
                    if not result:
                        logger.info("Photo sending failed, falling back to text message")
                        result = await TelegramService.send_message(text, db=db)
                else:
                    logger.warning(f"Image file not found: {image_full_path}")
                    result = await TelegramService.send_message(text, db=db)
            except Exception as e:
                logger.error(f"Error reading image: {e}")
                result = await TelegramService.send_message(text, db=db)
        else:
            # Fallback: nur Text-Nachricht
            result = await TelegramService.send_message(text, db=db)

        logger.info(f"Notification send result: {result}")
        return result
