import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).parent

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./kfz_kontakt.db"
    SECRET_KEY: str = "kfz-kontakt-secret-key-change-in-production"
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    BASE_URL: str = "https://kfz-kontakt.michaely.de"
    DASHBOARD_PASSWORD: str = "Schmelz112"
    UPLOAD_DIR: str = str(BASE_DIR.parent / "uploads")
    MAX_FILE_SIZE: int = 5 * 1024 * 1024  # 5MB

    # Twilio Configuration
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    TWILIO_WHATSAPP_NUMBER: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
