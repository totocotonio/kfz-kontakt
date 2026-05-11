from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import Request
from sqlalchemy.orm import Session
from models import User
import os
import secrets

SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "60"))  # 60 Min Inaktivität

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def authenticate_user(db: Session, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(request: Request, db: Session):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        return None
    # Sitzungs-Timeout prüfen
    if user.last_seen:
        from datetime import timezone
        now = datetime.now(timezone.utc)
        last = user.last_seen
        if last.tzinfo is None:
            from zoneinfo import ZoneInfo
            last = last.replace(tzinfo=ZoneInfo("Europe/Berlin"))
        inaktiv = (now - last).total_seconds() / 60
        if inaktiv > SESSION_TIMEOUT_MINUTES:
            return None  # Sitzung abgelaufen
    return user
