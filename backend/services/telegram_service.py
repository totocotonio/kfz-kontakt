import aiohttp
from config import settings

class TelegramService:
    @staticmethod
    async def send_message(message: str, chat_id: str = None, db=None):
        if not settings.TELEGRAM_BOT_TOKEN:
            print("⚠️ Telegram Bot Token nicht konfiguriert")
            return False

        target_chat_id = chat_id

        # Falls keine Chat ID übergeben, versuche aus Datenbank zu laden
        if not target_chat_id and db:
            try:
                from models import User
                user = db.query(User).filter(User.name == "Admin").first()
                if user and user.telegram_chat_id and user.telegram_chat_id != "0":
                    target_chat_id = user.telegram_chat_id
            except:
                pass

        # Fallback auf Config-Variable (deprecated)
        if not target_chat_id:
            target_chat_id = settings.TELEGRAM_CHAT_ID

        if not target_chat_id or target_chat_id == "0":
            print("⚠️ Telegram Chat ID nicht konfiguriert")
            return False

        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": target_chat_id,
            "text": message,
            "parse_mode": "HTML"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    return resp.status == 200
        except Exception as e:
            print(f"❌ Telegram Error: {e}")
            return False

    @staticmethod
    async def send_new_message_notification(qr_label: str, sender: str, message: str, category: str = None, db=None):
        text = f"""
<b>🚗 Neue Nachricht über QR-Code: {qr_label}</b>

<b>Von:</b> {sender}
"""
        if category:
            text += f"<b>Kategorie:</b> {category}\n"

        text += f"""
<b>Nachricht:</b>
{message}

<b>Antworte:</b> Rufe den Sender an oder antworte per WhatsApp/Telegram
        """
        return await TelegramService.send_message(text, db=db)
