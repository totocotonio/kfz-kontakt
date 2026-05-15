import aiohttp
import requests
from config import settings
import logging

logger = logging.getLogger(__name__)

class TelegramService:
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
    async def send_photo(photo_url: str, caption: str, chat_id: str = None, db=None):
        logger.info(f"📸 TelegramService.send_photo called - chat_id={chat_id}")

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
        payload = {
            "chat_id": target_chat_id,
            "photo": photo_url,
            "caption": caption,
            "parse_mode": "HTML"
        }

        try:
            logger.info(f"Sending Telegram photo to {target_chat_id}...")
            response = requests.post(url, json=payload, timeout=15)
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

        # Wenn Fahrzeugbild vorhanden, sende als Foto mit Caption
        if vehicle_image_path:
            # Konstruiere öffentliche URL zum Bild
            photo_url = f"https://kfz-kontakt.michaely.de{vehicle_image_path}"
            logger.info(f"Sending notification with photo: {photo_url}")
            result = await TelegramService.send_photo(photo_url, text, db=db)
        else:
            # Fallback: nur Text-Nachricht
            result = await TelegramService.send_message(text, db=db)

        logger.info(f"Notification send result: {result}")
        return result
