# 🎫 MP-Feuer Ticketsystem

Support-Ticketsystem für die Feuerwehr Landkreis Saarlouis. Nutzer können Tickets einreichen, der Admin bearbeitet und beantwortet sie – mit vollständiger E-Mail-Benachrichtigung, Kommentarverlauf, Anhängen und Admin-Aufgabenverwaltung.

**Status:** ✅ Production Ready (v3.9.24)  
**Live:** https://ticket.mpfeuer.michaely.de  
**© 2026 Torsten Michaely** – Alle Rechte vorbehalten.

---

## Features

### User-Portal
✅ **Registrierung & Login** – mit E-Mail-Verifizierung und optionaler 2-Faktor-Authentifizierung  
✅ **Ticket erstellen** – mit Priorität, Kategorie, Dateianhängen und CC-Empfängern  
✅ **Kommentieren & Antworten** – inkl. Zitierfunktion (Textauswahl oder Button)  
✅ **Druckansicht** – saubere Druckvorlage für jedes Ticket  
✅ **Status-Übersicht** – 📬 Eingereicht · 🔄 Beim Support · ↩️ Rückmeldung ausstehend · 📩 Neue Nachricht! · ✅ Erledigt  
✅ **Profil & Avatar** – Profilbild hochladen, Benachrichtigungseinstellungen  
✅ **Passwort zurücksetzen** – per E-Mail-Link  

### Admin-Panel
✅ **Ticket-Verwaltung** – Status, Priorität, Tags, interne Notizen, Zeitverlauf  
✅ **Antworten + Status in einem Schritt** – direkt beim Antworten Status setzen  
✅ **Zitierfunktion** – aus Kommentaren und Ticketbeschreibung zitieren  
✅ **Antwortvorlagen** – vordefinierte Textbausteine für häufige Antworten  
✅ **Aufgabenverwaltung** – AdminTasks mit Fälligkeitsdatum, Priorität, Ticket-Rücklink  
✅ **Globale Suche** – durchsucht Tickets, Nutzer und Kommentare  
✅ **Statistiken & Charts** – Monatsvolumen, Wochentag-Verteilung, Ø Antwortzeit  
✅ **Druckansicht** – vollständige Admin-Druckansicht inkl. Kommentarverlauf  
✅ **Nutzerverwaltung** – mit Avatar-Anzeige, Rollen, Aktivitätsstatus  
✅ **Störungsmeldungen** – Infobanner für alle Nutzer  
✅ **Changelog** – integrierte Versionshistorie  

### E-Mail
✅ **Benachrichtigungen** – bei neuen Tickets, Antworten, Statusänderungen  
✅ **CC-Empfänger** – weitere Adressen beim Erstellen eines Tickets angeben  
✅ **Circuit Breaker** – automatische Pause nach SMTP-Fehlern (verhindert IP-Sperren)  
✅ **Erinnerungen, SLA-Warnungen, Wochenberichte, Tagesübersicht**  

---

## Tech-Stack

| Komponente | Technologie |
|---|---|
| Backend | Python 3, FastAPI, uvicorn |
| Datenbank | SQLite via SQLAlchemy ORM |
| Templates | Jinja2 |
| Auth | JWT Cookies, bcrypt, 2FA per E-Mail |
| E-Mail | smtplib SMTP_SSL + Circuit Breaker |
| Charts | Chart.js 4.4.0 |
| Deployment | LXC Container auf Proxmox |
| Webserver | uvicorn (direkt, kein Nginx) |

---

## Server-Konfiguration

```
Server:    LXC Container auf Proxmox
IP:        192.168.178.181 (lokal)
URL:       https://ticket.mpfeuer.michaely.de
Python:    /opt/venv/bin/python3
App:       /opt/ticketsystem/main.py
Service:   systemctl status ticketsystem
DB:        /opt/ticketsystem/tickets.db
Uploads:   /opt/ticketsystem/uploads/
```

### Systemd Service

```ini
[Unit]
Description=MP-Feuer-Ticketsystem
After=network.target

[Service]
WorkingDirectory=/opt/ticketsystem
EnvironmentFile=/opt/ticketsystem/.env
ExecStart=/opt/venv/bin/python3 main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### .env Konfiguration

```env
SMTP_USER=ticket.mpfeuer@michaely.de
SMTP_PASS=...
SMTP_HOST=server36.webgo24.de
SMTP_PORT=465
FROM_EMAIL=ticket.mpfeuer@michaely.de
ADMIN_EMAIL=ticket.mpfeuer@michaely.de
APP_URL=https://ticket.mpfeuer.michaely.de
SECRET_KEY=...
```

---

## Installation (Neuaufbau)

```bash
# 1. Verzeichnis vorbereiten
mkdir /opt/ticketsystem
cd /opt/ticketsystem

# 2. Python-Umgebung
python3 -m venv /opt/venv
/opt/venv/bin/pip install fastapi uvicorn sqlalchemy jinja2 python-jose[cryptography] \
  passlib[bcrypt] python-multipart pillow slowapi paramiko

# 3. .env anlegen
cp .env.example .env
# Werte eintragen

# 4. Service einrichten
cp ticketsystem.service /etc/systemd/system/
systemctl enable ticketsystem
systemctl start ticketsystem
```

---

## Datenbank-Migrationen

Neue Spalten werden direkt per SQLite hinzugefügt:

```bash
sqlite3 /opt/ticketsystem/tickets.db \
  "ALTER TABLE tickets ADD COLUMN cc_emails TEXT;"
```

---

## Backup

Proxmox-Backup läuft täglich um 02:30 Uhr auf NAS (`192.168.178.62/Proxmoxbackup`).  
Aufbewahrung: `keep-daily=10, keep-last=10, keep-monthly=3`

---

## Lizenz

Privat entwickelt – alle Rechte vorbehalten.
