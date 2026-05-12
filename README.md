# 🚗 KFZ Kontakt - QR-Code Nachrichtensystem

Sichere und anonyme Kommunikation zwischen Fahrzeughaltern und anderen Verkehrsteilnehmern über QR-Codes.

## Features

✅ **QR-Code Generator** - Erstelle einzigartige QR-Codes mit verschiedenen Designs  
✅ **Nachrichtenformular** - Scanner können anonym Nachrichten hinterlassen  
✅ **Kategorien** - Nachrichten mit Kategorien (Parkplatz, Beleuchtung, etc.)  
✅ **Telegram-Benachrichtigungen** - Sofortige Benachrichtigungen bei neuen Nachrichten  
✅ **Admin-Dashboard** - Verwende und verwalte deine Nachrichten  
✅ **Datenschutz** - Keine persönlichen Daten werden angezeigt  
✅ **Mobile-optimiert** - Funktioniert auf allen Geräten  

## Tech-Stack

- **Backend:** FastAPI, SQLAlchemy, SQLite
- **Frontend:** HTML5, CSS3, Vanilla JavaScript
- **QR-Code:** qrcode-python, Pillow
- **Notifications:** python-telegram-bot

## Installation

### Voraussetzungen
- Python 3.8+
- pip
- Telegram Bot Token (von @BotFather)

### Setup

1. **Repository klonen / Verzeichnis vorbereiten**
   ```bash
   cd backend
   ```

2. **Dependencies installieren**
   ```bash
   pip install -r requirements.txt
   ```

3. **.env Datei erstellen**
   ```bash
   cp .env.example .env
   ```

4. **.env konfigurieren**
   ```
   TELEGRAM_BOT_TOKEN=dein_bot_token
   TELEGRAM_CHAT_ID=deine_chat_id
   DATABASE_URL=sqlite:///./kfz_kontakt.db
   HOST=0.0.0.0
   PORT=8000
   ```

5. **Server starten**
   ```bash
   python main.py
   ```

Server läuft unter `http://localhost:8000`

## Nutzung

### Admin-Dashboard
- **URL:** `http://localhost:8000/dashboard/index.html` (oder mit Domain)
- **Funktionen:**
  - Nachrichten verwalten
  - QR-Codes generieren
  - Statistiken anschauen
  - Entwürfe hochladen/runterladen

### Scanner-Seite
- **URL:** `http://localhost:8000/qr/{unique_id}`
- Scanner füllt Formular aus
- Nachricht wird verschlüsselt weitergeleitet
- Du erhältst Telegram-Benachrichtigung

### QR-Code Sticker
1. Im Dashboard "Neuer QR-Code" klicken
2. Beschreibung eingeben (z.B. "Mein Auto")
3. Design wählen (Standard/Minimal/Professionell)
4. Sticker runterladen
5. Auf Frontscheibe drucken und einkleben

## API Endpoints

### Scanner (Öffentlich)
- `GET /api/qr/{unique_id}/info` - QR-Code Infos + Kategorien
- `POST /api/qr/{unique_id}/message` - Nachricht submitten

### QR-Code Management
- `POST /api/qrcode/generate` - Neuen QR-Code erstellen
- `GET /api/qrcode/{qr_id}/image` - QR-Code als PNG
- `GET /api/qrcodes/list` - Alle QR-Codes auflisten

### Dashboard
- `GET /api/dashboard/messages` - Alle Nachrichten
- `GET /api/dashboard/messages/{id}` - Einzelne Nachricht
- `PATCH /api/dashboard/messages/{id}` - Nachricht aktualisieren
- `GET /api/dashboard/stats` - Statistiken
- `GET /api/dashboard/categories` - Kategorien

## Telegram Setup

1. Öffne Telegram → Suche **@BotFather**
2. `/start` → `/newbot`
3. Namen eingeben (z.B. "KFZ-Kontakt Bot")
4. Benutzername eingeben (z.B. "kfz_kontakt_bot")
5. **Token kopieren** (sieht so aus: `123456:ABCdefGHIjklmnoPQRstuvWXYZ`)
6. Bot zu deiner privaten Gruppe/Chat hinzufügen
7. In der Gruppe `/start` tippen → Chat-ID kopieren
8. Token und Chat-ID in `.env` eintragen

## Deployment auf Linux (LXC Container)

### 1. Container vorbereiten
```bash
apt update
apt install -y python3 python3-pip python3-venv
```

### 2. App hochfahren
```bash
git clone <repo> /opt/kfz-kontakt
cd /opt/kfz-kontakt/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# .env konfigurieren mit deinen Daten
```

### 3. Mit Systemd als Service
```bash
sudo nano /etc/systemd/system/kfz-kontakt.service
```

```ini
[Unit]
Description=KFZ Kontakt QR Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/kfz-kontakt/backend
ExecStart=/opt/kfz-kontakt/backend/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable kfz-kontakt
systemctl start kfz-kontakt
systemctl status kfz-kontakt
```

### 4. Mit Nginx Reverse Proxy
```nginx
server {
    listen 80;
    server_name kfz-kontakt.deine-domain.de;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static {
        alias /opt/kfz-kontakt/frontend/dashboard;
    }
}
```

## Lizenz

Privat entwickelt.

## Support

Bei Fragen/Problemen → Issue erstellen oder Kontakt aufnehmen.
