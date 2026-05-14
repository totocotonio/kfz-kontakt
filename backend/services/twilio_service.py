# -*- coding: utf-8 -*-
# © 2026 Torsten Michaely - KFZ Kontakt Twilio Service
# Mit SMS/WhatsApp-Integration für anonyme Kontaktmöglichkeiten
# All rights reserved

import logging
from typing import Optional
from sqlalchemy.orm import Session
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from datetime import datetime
from config import settings
from models import Message

logger = logging.getLogger(__name__)


class TwilioService:
    """Service für SMS und WhatsApp-Versand via Twilio"""

    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.phone_number = settings.TWILIO_PHONE_NUMBER
        self.whatsapp_number = settings.TWILIO_WHATSAPP_NUMBER

        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
        else:
            self.client = None
            logger.warning("Twilio nicht konfiguriert - SMS/WhatsApp funktioniert nicht")

    def send_sms(self, message_id: int, phone_number: str, message_text: str, db: Session) -> dict:
        """
        SMS via Twilio versenden

        Args:
            message_id: ID der Message in der Datenbank
            phone_number: Zieltelefonnummer (z.B. +49...)
            message_text: SMS-Text
            db: Database Session

        Returns:
            dict mit status und sms_sid
        """
        if not self.client or not self.phone_number:
            logger.error("Twilio nicht konfiguriert")
            return {"status": "error", "message": "SMS-Service nicht verfügbar"}

        try:
            # SMS versenden
            message = self.client.messages.create(
                body=message_text,
                from_=self.phone_number,
                to=phone_number,
                status_callback=f"{settings.BASE_URL}/webhooks/twilio"
            )

            # Message in DB aktualisieren
            db_message = db.query(Message).filter(Message.id == message_id).first()
            if db_message:
                db_message.sms_sid = message.sid
                db_message.sms_status = "queued"
                db_message.status_updated_at = datetime.utcnow()
                db.commit()
                logger.info(f"SMS queued: {message.sid} für Nachricht {message_id}")

            return {
                "status": "queued",
                "sms_sid": message.sid,
                "message": "SMS wird versendet an Admin..."
            }

        except TwilioRestException as e:
            logger.error(f"Twilio SMS Error: {e.msg} (Code {e.code})")
            return {
                "status": "error",
                "message": f"SMS konnte nicht versendet werden: {e.msg}"
            }
        except Exception as e:
            logger.error(f"Unerwarteter Fehler beim SMS-Versand: {str(e)}")
            return {
                "status": "error",
                "message": "Unerwarteter Fehler beim SMS-Versand"
            }

    def send_whatsapp(self, message_id: int, phone_number: str, message_text: str, db: Session) -> dict:
        """
        WhatsApp via Twilio versenden

        Args:
            message_id: ID der Message in der Datenbank
            phone_number: Zieltelefonnummer (z.B. +49...)
            message_text: WhatsApp-Text
            db: Database Session

        Returns:
            dict mit status und whatsapp_sid
        """
        if not self.client or not self.whatsapp_number:
            logger.error("Twilio WhatsApp nicht konfiguriert")
            return {"status": "error", "message": "WhatsApp-Service nicht verfügbar"}

        try:
            # WhatsApp-Nachricht versenden
            # Format: whatsapp:+49... (aus dem whatsapp_number)
            message = self.client.messages.create(
                body=message_text,
                from_=f"whatsapp:{self.whatsapp_number}",
                to=f"whatsapp:{phone_number}",
                status_callback=f"{settings.BASE_URL}/webhooks/twilio"
            )

            # Message in DB aktualisieren
            db_message = db.query(Message).filter(Message.id == message_id).first()
            if db_message:
                db_message.whatsapp_sid = message.sid
                db_message.whatsapp_status = "queued"
                db_message.status_updated_at = datetime.utcnow()
                db.commit()
                logger.info(f"WhatsApp queued: {message.sid} für Nachricht {message_id}")

            return {
                "status": "queued",
                "whatsapp_sid": message.sid,
                "message": "WhatsApp wird versendet an Admin..."
            }

        except TwilioRestException as e:
            logger.error(f"Twilio WhatsApp Error: {e.msg} (Code {e.code})")
            return {
                "status": "error",
                "message": f"WhatsApp konnte nicht versendet werden: {e.msg}"
            }
        except Exception as e:
            logger.error(f"Unerwarteter Fehler beim WhatsApp-Versand: {str(e)}")
            return {
                "status": "error",
                "message": "Unerwarteter Fehler beim WhatsApp-Versand"
            }

    def handle_webhook(self, sms_sid: str, status: str, db: Session) -> None:
        """
        Webhook-Handler für Twilio Delivery Status Updates

        Args:
            sms_sid: Twilio Message SID
            status: Status (queued, sending, sent, failed, delivered, undelivered)
            db: Database Session
        """
        try:
            # Message suchen
            db_message = db.query(Message).filter(
                (Message.sms_sid == sms_sid) | (Message.whatsapp_sid == sms_sid)
            ).first()

            if db_message:
                # Status aktualisieren
                if db_message.sms_sid == sms_sid:
                    db_message.sms_status = status
                elif db_message.whatsapp_sid == sms_sid:
                    db_message.whatsapp_status = status

                db_message.status_updated_at = datetime.utcnow()
                db.commit()
                logger.info(f"Status aktualisiert für {sms_sid}: {status}")
            else:
                logger.warning(f"Message für SID {sms_sid} nicht gefunden")

        except Exception as e:
            logger.error(f"Fehler bei Webhook-Verarbeitung: {str(e)}")


# Singleton-Instanz
twilio_service = TwilioService()
