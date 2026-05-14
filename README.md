# 🚗 KFZ Kontakt - QR-Code Nachrichtensystem

Sichere und anonyme Kommunikation zwischen Fahrzeughaltern und anderen Verkehrsteilnehmern über QR-Codes. Mit Fahrzeugfotos, Kennzeichen und persönlichen Icons.

**Status:** ✅ Production Ready (v1.0.121) - Auto-Deploy aktiv

## Features

✅ **QR-Code Generator** - Erstelle einzigartige QR-Codes mit 3 Designs (Standard/Minimal/Professionell)  
✅ **Fahrzeugfotos & Kennzeichen** - Zeige dein Fahrzeugbild + Kennzeichen auf der Landing Page  
✅ **Icon-Auswahl** - ☎️ Telefon / 💬 WhatsApp / 📧 Email / ❌ Keine - mit 4 Positionen  
✅ **Hintergrundfarbe** - Wähle die Farbe des QR-Code Stickers  
✅ **Landing Page** - Besucher sehen Fahrzeugbild bevor sie Nachricht schreiben  
✅ **Nachrichtenformular** - Scanner können anonym Nachrichten hinterlassen  
✅ **Kategorien** - Nachrichten mit Kategorien (Parkplatz, Beleuchtung, Fenster, Schaden, Sonstiges)  
✅ **Telegram-Benachrichtigungen** - Sofortige Benachrichtigungen bei neuen Nachrichten  
✅ **Admin-Dashboard** - Verwalte QR-Codes, Fahrzeugbilder, Nachrichten und WhatsApp-Nummer  
✅ **Datenschutz** - Keine persönlichen Daten werden angezeigt  
✅ **Mobile-optimiert** - Funktioniert auf allen Geräten  

## QR-Code Designs

### Standard (400×500px)
- Hellgrauer Hintergrund mit blauem Rahmen
- Label-Text unten
- Perfekt für Frontscheibe
- Mit optional Icon am unteren Rand

### Minimal (340×340px)
- Kompakt - ideal für kleine Plätze
- Dünner grauer Rahmen
- Nur QR-Code + Optional Icon
- Gut für Scheiben mit wenig Platz

### Professionell (450×550px)
- Großer weißer Rahmen auf dunklem Hintergrund
- Großer Titel oben
- Premium-Look für Gewerbe/Business
- Optional Icon unten

### Icon-Optionen
- **☎️ Telefon** - Grünes Rechteck mit Bildschirm (oder PNG-Datei wenn vorhanden)
- **💬 WhatsApp** - Dunkelgrüner Kreis mit Sprechblase
- **📧 Email** - Blaues Rechteck mit Umschlag
- **❌ Keine** - Kein Icon anzeigen

### Icon-Positionen
- **⬇️ Unten** - Zentriert am unteren Rand
- **↘️ Unten-Rechts** - In der rechten unteren Ecke
- **➡️ Rechts** - Auf der rechten Seite, vertikal zentriert
- **↗️ Oben-Rechts** - In der rechten oberen Ecke

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
- **URL:** `http://localhost:8000/dashboard/` (oder mit Domain)
- **Login:** Passwort erforderlich (aus .env: DASHBOARD_PASSWORD)

#### Tabs:

**📬 Nachrichten**
- Alle eingehenden Nachrichten anzeigen
- Als gelesen/beantwortet markieren
- Kategorien und Sender sehen
- Mit Zeitstempel

**📱 QR-Codes**
- WhatsApp-Nummer eingeben (optional)
- Neue QR-Codes erstellen mit:
  - Beschreibung (Label)
  - Text auf Sticker
  - Design (Standard/Minimal/Professionell)
  - Hintergrundfarbe
  - Icon-Typ + Position
  - Kennzeichen
  - Fahrzeugbild Upload
- QR-Codes runterladen (als PNG)
- QR-Codes bearbeiten
- QR-Codes löschen

**📊 Statistiken**
- Gesamt Nachrichten
- Ungelesene Nachrichten
- Beantwortete Nachrichten

### Scanner-Seite
- **URL:** `http://localhost:8000/qr/{unique_id}`
- Scanner füllt Formular aus
- Nachricht wird verschlüsselt weitergeleitet
- Du erhältst Telegram-Benachrichtigung

### QR-Code Sticker mit Fahrzeugbild

1. **Dashboard öffnen** → "Neuer QR-Code" klicken
2. **Beschreibung** eingeben (z.B. "Mein Auto")
3. **Text auf Sticker** wählen (z.B. "FAHRZEUG KONTAKT")
4. **Design wählen** (Standard/Minimal/Professionell)
5. **Hintergrundfarbe** einstellen
6. **Icon wählen** (☎️ Telefon / 💬 WhatsApp / 📧 Email / ❌ Keine)
7. **Icon Position** wählen (Unten / Unten-Rechts / Rechts / Oben-Rechts)
8. **Kennzeichen eingeben** (z.B. "AB-CD 1234")
9. **Fahrzeugbild hochladen** (PNG/JPG/WebP, max 5MB)
10. **Erstellen** → Sticker runterladen
11. Auf Frontscheibe drucken und einkleben

**Workflow beim QR-Code Scan:**
- Scanner scannt QR-Code → Sieht Fahrzeugbild + Kennzeichen
- "Nachricht senden" klicken → Kategorie wählen → Kontaktform
- Nachricht wird an dich gesendet + Telegram-Benachrichtigung

## API Endpoints

### Scanner (Öffentlich)
- `GET /api/qr/{unique_id}/info` - QR-Code Infos + Kategorien
- `POST /api/qr/{unique_id}/message` - Nachricht submitten

### QR-Code Management
- `POST /api/qrcode/generate` - Neuen QR-Code erstellen (mit label, title, design, background_color, icon_type, icon_position, license_plate)
- `GET /api/qrcode/{qr_id}/image` - QR-Code Sticker als PNG (Download)
- `GET /api/qrcodes/list` - Alle QR-Codes auflisten
- `GET /api/qrcode/{qr_id}` - Einzelnen QR-Code Details abrufen
- `PATCH /api/qrcode/{qr_id}` - QR-Code aktualisieren (label, title, design, background_color, icon_type, icon_position, license_plate)
- `POST /api/qrcode/{qr_id}/upload-image` - Fahrzeugbild hochladen (Multipart Form Data)
- `DELETE /api/qrcode/{qr_id}` - QR-Code löschen (inkl. Fahrzeugbild)

### Dashboard
- `GET /api/dashboard/messages` - Alle Nachrichten
- `GET /api/dashboard/messages/{id}` - Einzelne Nachricht
- `PATCH /api/dashboard/messages/{id}` - Nachricht aktualisieren (read, responded)
- `GET /api/dashboard/stats` - Statistiken (total_messages, unread, responded)
- `GET /api/dashboard/whatsapp` - WhatsApp-Nummer abrufen
- `PATCH /api/dashboard/whatsapp` - WhatsApp-Nummer aktualisieren

### Scanner Pages
- `GET /qr/{unique_id}` - Landing Page (automatisch gewählt basierend auf Fahrzeugbild)
  - Mit Fahrzeugbild → `/qr/vehicle-landing.html` (Fahrzeugbild + Kennzeichen)
  - Ohne Fahrzeugbild → `/select-category.html` (Kategorie-Auswahl)
- `GET /qr/{unique_id}?category={id}` - Kontaktformular
- `GET /select-category.html` - Kategorie-Auswahl
- `POST /api/qr/{unique_id}/message` - Nachricht absenden

## Fahrzeugbild Spezifikationen

### Unterstützte Formate
- **PNG** - Mit Transparenz (wird zu JPG konvertiert)
- **JPEG/JPG** - Standard-Format
- **WebP** - Modernes Format

### Anforderungen
- **Maximale Größe:** 5 MB
- **Empfohlene Größe:** 200-500 KB
- **Seitenverhältnis:** 4:3 (z.B. 800×600, 1024×768)
- **Speicherort:** `/uploads/{unique_id}/vehicle.jpg` (wird automatisch verwaltet)

### Verarbeitung
- Alle Bilder werden zu JPG mit Qualität 90 konvertiert
- Transparente Bereiche (PNG/WebP) werden mit Weiß gefüllt
- Bilder werden bei Löschung des QR-Codes automatisch gelöscht

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

## Changelog - Neue Features (v1.0.120+)

### v1.0.120
✅ **Fahrzeugbild + Kennzeichen Landing Page**
- `vehicle-landing.html`: Neue Landing Page mit Fahrzeugbild anzeige
- `file_service.py`: Service für Image Upload/Delete/Validate
- Automatische JPG-Konvertierung und Validierung
- Fallback auf Kategorie-Auswahl wenn kein Bild vorhanden

✅ **Icon-Auswahl Fix**
- Icons ändern sich jetzt korrekt (nicht immer Telefon)
- ☎️ Telefon / 💬 WhatsApp / 📧 Email / ❌ Keine
- Icon-Positionen: Bottom / Bottom-Right / Right / Top-Right

### v1.0.119
✅ **Icon Positioning Feature**
- Wählbare Icon-Positionen (4 Optionen)
- _get_icon_position() Helper-Funktion
- Anpassbar für alle 3 Designs

### v1.0.115
✅ **Icon Type Selection**
- Verschiedene Icon-Typen wählbar
- Gezeichnete Icons als Fallback
- _draw_icon() Function für Rendering

## Lizenz

Privat entwickelt.

## Support

Bei Fragen/Problemen → Issue erstellen oder Kontakt aufnehmen.
