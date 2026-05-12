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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
