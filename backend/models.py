from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    telegram_chat_id = Column(String(255), unique=True)
    telegram_username = Column(String(255), nullable=True)
    whatsapp_number = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    qr_codes = relationship("QRCode", back_populates="user")
    messages = relationship("Message", back_populates="user")


class QRCode(Base):
    __tablename__ = "qr_codes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    unique_id = Column(String(50), unique=True, index=True)
    label = Column(String(255), nullable=True)
    title = Column(String(255), nullable=True)
    design = Column(String(50), default="default")
    background_color = Column(String(7), default="#f5f5f5")
    logo = Column(String(500), nullable=True)
    license_plate = Column(String(50), nullable=True)
    vehicle_image_path = Column(String(500), nullable=True)
    icon_type = Column(String(50), default="phone")
    icon_position = Column(String(50), default="bottom")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="qr_codes")
    messages = relationship("Message", back_populates="qr_code")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)

    messages = relationship("Message", back_populates="category")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    qr_code_id = Column(Integer, ForeignKey("qr_codes.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    sender_name = Column(String(255), nullable=True)
    sender_contact = Column(String(255), nullable=True)
    message = Column(Text)
    read = Column(Boolean, default=False)
    responded = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    qr_code = relationship("QRCode", back_populates="messages")
    user = relationship("User", back_populates="messages")
    category = relationship("Category", back_populates="messages")
