# 🚗 KFZ Kontakt - QR-Code Nachrichtensystem

Sichere und anonyme Kommunikation zwischen Fahrzeughaltern und anderen Verkehrsteilnehmern über QR-Codes. Mit Fahrzeugfotos, Kennzeichen, persönlichen Icons und PWA-Unterstützung.

**Status:** ✅ Production Ready (v1.0.257) - Auto-Deploy aktiv
**© 2026 Torsten Michaely** – Alle Rechte vorbehalten. Mit professionellem Dashboard & auswählbaren Kontaktmethoden.

## Features

✅ **QR-Code Generator** - Erstelle einzigartige QR-Codes mit 3 Designs (Standard/Minimal/Professionell)  
✅ **Fahrzeugfotos & Kennzeichen** - Zeige dein Fahrzeugbild + Kennzeichen auf der Landing Page  
✅ **Icon-Auswahl** - ☎️ Telefon / 💬 WhatsApp / 📧 Email / ❌ Keine - mit 4 Positionen  
✅ **Hintergrundfarbe** - Wähle die Farbe des QR-Code Stickers  
✅ **Landing Page** - Besucher sehen Fahrzeugbild bevor sie Nachricht schreiben  
✅ **Nachrichtenformular** - Scanner können anonym Nachrichten hinterlassen  
✅ **Kategorien** - Nachrichten mit Kategorien (Parkplatz, Beleuchtung, Fenster, Schaden, Sonstiges)  
✅ **Telegram-Benachrichtigungen** - Sofortige Benachrichtigungen bei neuen Nachrichten  
✅ **Admin-Dashboard** - Premium-Design mit Nachrichten, QR-Codes, Einstellungen & Statistiken
✅ **Auswählbare Kontaktmethoden** - Eine Telefonnummer mit Toggle für Telegram, SMS, WhatsApp
✅ **Statistiken-Seite** - Übersicht: Gesamtnachrichten, Ungelesen, Beantwortet
✅ **Responsive Layout** - Kein Scrollen nötig, alle Inhalte auf einer Bildschirmseite
✅ **Message Tracking** - Lieferungsstatus für SMS und WhatsApp (pending/sent/delivered/failed)  
✅ **Datenschutz** - Keine persönlichen Daten werden öffentlich angezeigt  
✅ **Mobile-optimiert** - Funktioniert auf allen Geräten  
✅ **PWA (Progressive Web App)** - Installierbar auf Mobilgeräten, offline-fähig mit Service Worker
✅ **Legal Pages** - Datenschutzerklärung & Impressum (DSGVO/§5 TMG konform)
✅ **Copyright-Schutz** - Professionelle Code-Header in allen Dateien  

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
- **Notifications:** python-telegram-bot, Twilio
- **PWA:** Service Worker, Web App Manifest, Offline-Support
- **SMS/WhatsApp:** Twilio API (v8.10.0) mit Webhook Status-Updates

## PWA Features (Progressive Web App)

✅ **Installierbar** - "Zum Home-Bildschirm hinzufügen" auf Mobilgeräten  
✅ **Offline-Unterstützung** - Service Worker cacht wichtige Ressourcen  
✅ **App-Manifest** - `manifest.json` mit App-Metadaten, Icons und Konfiguration  
✅ **Auto-Update** - Service Worker prüft regelmäßig auf Updates  
✅ **Responsive** - Optimiert für alle Bildschirmgrößen (Mobile, Tablet, Desktop)  

### PWA Installation
1. **Auf Mobilgerät:** Browser → KFZ Kontakt öffnen → Menü → "Zum Home-Bildschirm hinzufügen"
2. **Auf Desktop:** Chrome/Edge → Adressleiste → "App installieren"
3. App erscheint dann wie eine native App (Vollbild, offline verfügbar)

### Offline-Funktionalität
- Alle HTML-Seiten und Assets werden gecacht
- Navigation funktioniert offline (mit cached Pages)
- API-Anfragen zeigen offline.html wenn Verbindung fehlt
- Nachrichten können erst gesendet werden, wenn Verbindung vorhanden ist

## Legal Pages

✅ **Datenschutzerklärung** - DSGVO-konform (`/datenschutz.html`)
- Verantwortlicher & Kontakt
- Datenverarbeitung & Speicherung
- WhatsApp & Telegram Integration
- Benutzerrechte (DSGVO Art. 15-22)

✅ **Impressum** - §5 TMG (`/impressum.html`)
- Anbieterangaben
- Haftungsausschluss
- Urheberrecht & Lizenzierung

✅ **Copyright-Schutz**
- HTML-Comments mit © 2026 Torsten Michaely in allen Dateien
- Meta-Tags für Copyright, Author, Application-Name
- Schema.org JSON-LD für Strukturierte Daten
- Dynamisches Footer-Jahr (wird automatisch aktualisiert)

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
   # Telegram
   TELEGRAM_BOT_TOKEN=dein_bot_token
   TELEGRAM_CHAT_ID=deine_chat_id
   
   # Twilio (Optional für SMS/WhatsApp)
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=your_auth_token
   TWILIO_PHONE_NUMBER=+49xxxxxxxxx
   TWILIO_WHATSAPP_NUMBER=+14xxxxxxxxx
   
   # Database & Server
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
- Lieferungsstatus für SMS/WhatsApp anzeigen (pending/sent/delivered/failed)

**⚙️ Einstellungen**
- Telefonnummer eingeben (für SMS und WhatsApp Empfang)
- Admin-Benachrichtigungen via Telegram konfigurieren

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
- `POST /api/qr/{unique_id}/contact/sms` - SMS via Twilio versenden (anonym)
- `POST /api/qr/{unique_id}/contact/whatsapp` - WhatsApp via Twilio versenden (anonym)

### QR-Code Management
- `POST /api/qrcode/generate` - Neuen QR-Code erstellen (mit label, title, design, background_color, icon_type, icon_position, license_plate)
- `GET /api/qrcode/{qr_id}/image` - QR-Code Sticker als PNG (Download)
- `GET /api/qrcodes/list` - Alle QR-Codes auflisten
- `GET /api/qrcode/{qr_id}` - Einzelnen QR-Code Details abrufen
- `PATCH /api/qrcode/{qr_id}` - QR-Code aktualisieren (label, title, design, background_color, icon_type, icon_position, license_plate)
- `POST /api/qrcode/{qr_id}/upload-image` - Fahrzeugbild hochladen (Multipart Form Data)
- `DELETE /api/qrcode/{qr_id}` - QR-Code löschen (inkl. Fahrzeugbild)

### Dashboard
- `GET /api/dashboard/messages` - Alle Nachrichten (mit SMS/WhatsApp Status)
- `GET /api/dashboard/messages/{id}` - Einzelne Nachricht (mit Twilio-Tracking)
- `PATCH /api/dashboard/messages/{id}` - Nachricht aktualisieren (read, responded)
- `GET /api/dashboard/stats` - Statistiken (total_messages, unread, responded)
- `GET /api/dashboard/phone` - Admin-Telefonnummer abrufen
- `PATCH /api/dashboard/phone` - Admin-Telefonnummer aktualisieren (für SMS/WhatsApp Empfang)

### Webhooks
- `POST /webhooks/twilio` - Twilio Status-Updates (SMS/WhatsApp Delivery Status)

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

## Twilio Setup (für SMS & WhatsApp)

### 1. Twilio-Konto erstellen
1. https://www.twilio.com/ öffnen → Sign up
2. Gratis mit $10 Trial-Guthaben
3. Telefonnummer bestätigen
4. Account aktivieren

### 2. Account-Credentials
1. **Console Dashboard** öffnen
2. **Account SID** kopieren (sieht so aus: `ACxxxxxxxxxxxxxxxx`)
3. **Auth Token** kopieren (sieht so aus: `your_auth_token`)
4. Diese Werte speichern

### 3. Telefonnummer kaufen
1. Im Dashboard → **Phone Numbers** → **Buy a Number**
2. **Country:** Deutschland (DE)
3. **Number Type:** SMS + Voice
4. Nächste verfügbare Nummer auswählen (~$1/Monat)
5. **Purchase** klicken
6. Nummer formatiert kopieren (z.B. `+49xxx`)

### 4. WhatsApp Sandbox aktivieren
1. Im Dashboard → **Messaging** → **Try it out** → **Send an SMS**
2. Im Menü → **WhatsApp** → **Sandbox**
3. **Join the Sandbox:** QR-Code scannen oder WhatsApp-Nummer + Text senden
4. **Sandbox Phone Number** kopieren

### 5. .env aktualisieren
```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+49xxxxxxxxx     # Gekaufte SMS-Nummer
TWILIO_WHATSAPP_NUMBER=+14xxxxxxxxx  # WhatsApp Sandbox Nummer
```

### 6. Webhook-URL konfigurieren (Production nur)
1. Im Dashboard → **Messaging** → **Settings** → **Webhook URL**
2. **Status Callbacks:** `https://deine-domain.de/webhooks/twilio`
3. **Method:** POST
4. Speichern

### Kosten
- **SMS:** $0.0083 pro Nachricht (gesendet an Admin)
- **WhatsApp:** $0.005 pro Nachricht
- **Phone Number:** ~$1/Monat
- **Beispiel:** 50 Nachrichten/Monat = ca. $1.50 Kosten

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

### v1.0.257 - Dashboard Redesign & Kontaktmethoden
✅ **Professionelles Admin-Dashboard**
- Card-basiertes Design mit Hover-Effekten
- Vergrößerte QR-Code Vorschaubilder (160px)
- Größere Action-Buttons für bessere Usability
- Responsive Grid-Layout für alle Tabs

✅ **Kontaktmethoden Konsolidierung**
- Eine einzige Telefonnummer für SMS und WhatsApp (statt zwei separaten)
- Auswählbare Kontaktmethoden: Telegram ☑️ / SMS ☑️ / WhatsApp ☑️
- Besucher können wählen, welche Methode sie nutzen
- Admin-Telefonnummer bleibt privat (nicht in URLs sichtbar)
- API-Endpoints konsolidiert: `/dashboard/contact` + `/dashboard/contact-methods`

✅ **Statistiken-Seite Redesign**
- Professionelle Card-Layouts mit Statistiken
- Gesamtnachrichten, Ungelesene, Beantwortete anzeigen
- Konsistent mit Dashboard-Design

✅ **Responsive Layout ohne Scrolling**
- Flexbox-basiertes Layout
- Alle Inhalte passen auf eine Bildschirmseite (kein Scrollen nötig)
- Header und Navigation sperren oben
- Hauptbereich scrollt bei Bedarf

✅ **Datenbank Auto-Migration**
- Neue Spalten (`enable_telegram`, `enable_sms`, `enable_whatsapp`) werden bei Start automatisch hinzugefügt
- `migrate.py` für manuelle Migrationen
- Keine manuellen SQL-Befehle nötig

### v1.0.161 - Twilio SMS/WhatsApp Integration
✅ **Anonyme SMS und WhatsApp über Twilio**
- `TwilioService` für SMS und WhatsApp Versand
- Message-Modell erweitert mit `contact_method`, `sms_sid`, `sms_status`, `whatsapp_sid`, `whatsapp_status`, `status_updated_at`
- API-Endpoints: `/api/qr/{unique_id}/contact/sms` und `/contact/whatsapp`
- Webhook-Handler: `POST /webhooks/twilio` für Delivery Status Updates
- RequestValidator für Twilio Webhook-Signatur-Validierung
- Dashboard: Lieferungsstatus anzeigen (pending/sent/delivered/failed)
- Kostengünstig: SMS $0.0083, WhatsApp $0.005 pro Nachricht
- Admin-Telefonnummer bleibt privat (wird nicht öffentlich angezeigt)

✅ **Erweiterte .env Konfiguration**
- TWILIO_ACCOUNT_SID
- TWILIO_AUTH_TOKEN
- TWILIO_PHONE_NUMBER
- TWILIO_WHATSAPP_NUMBER

✅ **Frontend Updates**
- SMS/WhatsApp Buttons nutzen jetzt API-Calls statt direkter Links
- Loading-States während Versand
- Status-Feedback nach Versand
- Telefonnummer wird nicht in URLs angezeigt

### v1.0.124 - PWA Professionalisierung
✅ **Progressive Web App (PWA)**
- Service Worker (`sw.js`) für Caching und Offline-Support
- Web App Manifest (`manifest.json`) mit Icons und App-Konfiguration
- Offline Fallback Page (`offline.html`)
- Auto-Update Mechanismus alle 60 Sekunden

✅ **Legal Pages**
- `datenschutz.html`: DSGVO-konforme Datenschutzerklärung
- `impressum.html`: §5 TMG Impressum mit Kontaktdaten
- Responsive Design mit Purple-Gradient-Theme

✅ **Copyright & Meta-Tags**
- Professionelle Copyright-Header in allen Python-Dateien (qr_service.py, file_service.py)
- Meta-Tags in allen HTML-Seiten (copyright, author, application-name, description, keywords, robots)
- Schema.org JSON-LD Structured Data für SEO
- Open Graph Tags für Social Media Sharing

✅ **CSS Root-Variablen**
- Zentrale CSS-Variablendefinition (:root) für konsistentes Design
- Farben: primary, secondary, success, danger, warning, info, whatsapp, telegram
- Fonts: font-sans, font-mono
- Shadows: shadow, shadow-lg

✅ **Asset-Optimierung**
- SVG Favicon (`/assets/favicon.svg`)
- Favicon-Links in allen HTML-Dateien
- Reduzierte Icon-Pfade (SVG statt PNG)

✅ **Service Worker Registration**
- Automatische Registration in allen Seiten
- Regelmäßige Update-Checks (60 Sekunden)
- Fehlerbehandlung & Logging

✅ **Footer-Update**
- Dynamisches Copyright-Jahr in Datenschutz & Impressum
- Links zu Legal Pages in Footer

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
