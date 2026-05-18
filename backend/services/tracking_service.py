# -*- coding: utf-8 -*-
# Tracking Service für QR-Code Scans
# Registriert Besucher, User-Agent, Geolocation und Device-Informationen

import logging
from datetime import datetime
from user_agents import parse
from sqlalchemy.orm import Session
from models import QRCodeScan, QRCode

logger = logging.getLogger(__name__)


class TrackingService:
    """Service für QR-Code Scan-Tracking und Analytics"""

    @staticmethod
    def parse_user_agent(user_agent_string: str) -> tuple[str, str]:
        """
        Parse User-Agent String und extrahiere Device-Type und Browser-Name

        Returns:
            Tuple of (device_type, browser_name)
            device_type: "mobile", "tablet", "desktop", "unknown"
            browser_name: "Chrome", "Safari", "Firefox", etc.
        """
        try:
            ua = parse(user_agent_string)

            # Device Type bestimmen
            device_type = "unknown"
            if ua.is_mobile:
                device_type = "mobile"
            elif ua.is_tablet:
                device_type = "tablet"
            elif ua.is_pc:
                device_type = "desktop"

            # Browser Name extrahieren
            browser_name = ua.browser.family if ua.browser.family else "unknown"

            return device_type, browser_name
        except Exception as e:
            logger.warning(f"Error parsing user-agent: {str(e)}")
            return "unknown", "unknown"

    @staticmethod
    def extract_ip_from_request(request) -> str:
        """
        Extrahiere IP-Adresse aus Request
        Berücksichtigt X-Forwarded-For Header für Proxies
        """
        try:
            # Versuche X-Forwarded-For Header (Proxy)
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                # Nimm erste IP aus der Liste
                return forwarded.split(",")[0].strip()

            # Fallback: client host
            if request.client:
                return request.client.host

            return None
        except Exception as e:
            logger.warning(f"Error extracting IP: {str(e)}")
            return None

    @staticmethod
    def get_ip_geolocation(ip_address: str) -> dict[str, str]:
        """
        Extrahiere Geolocation aus IP-Adresse
        Nutzt ip-api.com oder geojs.io als Fallback (optional)

        Returns:
            Dict mit "country" und "city" Keys
            Aktuell: nur Placeholder, kann mit API erweitert werden
        """
        # Placeholder für IP-Geolocation
        # In der Praxis würde man hier eine API wie ip-api.com nutzen
        # Für MVP reicht es vorerst, nur die Browser-Geolocation zu nutzen
        return {"country": None, "city": None}

    @staticmethod
    def create_scan_record(
        db: Session,
        qr_code_id: int,
        latitude: float = None,
        longitude: float = None,
        accuracy: float = None,
        ip_address: str = None,
        country: str = None,
        city: str = None,
        user_agent: str = None,
        device_type: str = "unknown",
        browser_name: str = None,
        referrer: str = None,
        is_returning_visitor: bool = False
    ) -> QRCodeScan:
        """
        Erstelle einen neuen QRCodeScan Record in der Datenbank

        Args:
            db: SQLAlchemy Session
            qr_code_id: ID des QR-Codes
            latitude: Browser Geolocation Latitude
            longitude: Browser Geolocation Longitude
            accuracy: Genauigkeit in Metern
            ip_address: IP-Adresse des Besuchers
            country: Land (aus Browser-Geo oder IP)
            city: Stadt (aus Browser-Geo oder IP)
            user_agent: User-Agent String
            device_type: "mobile", "tablet", "desktop"
            browser_name: Browser Name
            referrer: HTTP Referrer
            is_returning_visitor: Ist ein wiederholter Besucher?

        Returns:
            QRCodeScan Record
        """
        try:
            # Verifiziere dass QR-Code existiert
            qr_code = db.query(QRCode).filter(QRCode.id == qr_code_id).first()
            if not qr_code:
                logger.error(f"QRCode {qr_code_id} not found")
                return None

            scan = QRCodeScan(
                qr_code_id=qr_code_id,
                latitude=latitude,
                longitude=longitude,
                accuracy=accuracy,
                ip_address=ip_address,
                country=country,
                city=city,
                user_agent=user_agent,
                device_type=device_type,
                browser_name=browser_name,
                referrer=referrer,
                is_returning_visitor=is_returning_visitor,
                created_at=datetime.utcnow()
            )

            db.add(scan)
            db.commit()
            db.refresh(scan)

            logger.info(f"Scan recorded: QRCode={qr_code_id}, Device={device_type}, Browser={browser_name}")
            return scan

        except Exception as e:
            logger.error(f"Error creating scan record: {str(e)}")
            db.rollback()
            return None

    @staticmethod
    def get_scan_stats(db: Session, qr_code_id: int) -> dict:
        """
        Hole Scan-Statistiken für einen QR-Code

        Returns:
            Dict mit:
            - total_scans: Gesamtzahl Scans
            - scans_by_country: {country: count}
            - scans_by_device: {device_type: count}
            - scans_by_browser: {browser_name: count}
            - returning_visitors: Anzahl wiederholter Besucher
            - latest_scans: Die 10 neuesten Scans
        """
        try:
            scans = db.query(QRCodeScan).filter(QRCodeScan.qr_code_id == qr_code_id).all()

            if not scans:
                return {
                    "total_scans": 0,
                    "scans_by_country": {},
                    "scans_by_device": {},
                    "scans_by_browser": {},
                    "returning_visitors": 0,
                    "latest_scans": []
                }

            # Aggregiere Statistiken
            scans_by_country = {}
            scans_by_device = {}
            scans_by_browser = {}
            returning = 0

            for scan in scans:
                # Country
                country = scan.country or "unknown"
                scans_by_country[country] = scans_by_country.get(country, 0) + 1

                # Device Type
                device = scan.device_type or "unknown"
                scans_by_device[device] = scans_by_device.get(device, 0) + 1

                # Browser
                browser = scan.browser_name or "unknown"
                scans_by_browser[browser] = scans_by_browser.get(browser, 0) + 1

                # Returning Visitor
                if scan.is_returning_visitor:
                    returning += 1

            # Die neuesten 10 Scans
            latest_scans = [
                {
                    "id": scan.id,
                    "device_type": scan.device_type,
                    "browser_name": scan.browser_name,
                    "country": scan.country or "unknown",
                    "latitude": scan.latitude,
                    "longitude": scan.longitude,
                    "created_at": scan.created_at.isoformat() if scan.created_at else None
                }
                for scan in sorted(scans, key=lambda s: s.created_at or datetime.min, reverse=True)[:10]
            ]

            return {
                "total_scans": len(scans),
                "scans_by_country": scans_by_country,
                "scans_by_device": scans_by_device,
                "scans_by_browser": scans_by_browser,
                "returning_visitors": returning,
                "latest_scans": latest_scans
            }

        except Exception as e:
            logger.error(f"Error getting scan stats: {str(e)}")
            return {
                "total_scans": 0,
                "scans_by_country": {},
                "scans_by_device": {},
                "scans_by_browser": {},
                "returning_visitors": 0,
                "latest_scans": []
            }


# Singleton-Instanz
tracking_service = TrackingService()
