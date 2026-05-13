# 🚀 KFZ-Kontakt Deployment Guide

Dokumentation für die Bereitstellung auf Linux (LXC Container / Debian 12).

## Schnell-Start (LXC Container)

### 1. System vorbereiten

```bash
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv git curl
```

### 2. App installieren

```bash
cd /opt
git clone https://github.com/totocotonio/kfz-kontakt.git
cd kfz-kontakt/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Konfigurieren

```bash
cp .env.example .env
nano .env
```

**Erforderliche Variablen:**
- `TELEGRAM_BOT_TOKEN` - Von @BotFather auf Telegram
- `TELEGRAM_CHAT_ID` - Deine Telegram Chat ID
- `DATABASE_URL` - Bleibt `sqlite:///./kfz_kontakt.db`

### 4. Telegram Bot Setup

1. Öffne Telegram → Suche `@BotFather`
2. `/newbot` → Name + Username eingeben
3. Token kopieren → In `.env` eintragen
4. Bot zu deiner Gruppe hinzufügen
5. In Gruppe `/start` tippen → Chat ID kopieren

### 5. Testen

```bash
python3 main.py
```

Server läuft auf `http://localhost:8000`

---

## Production Setup mit Systemd Service

### 1. Service erstellen

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
Environment="PATH=/opt/kfz-kontakt/backend/venv/bin"
ExecStart=/opt/kfz-kontakt/backend/venv/bin/python3 main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 2. Service aktivieren

```bash
sudo systemctl daemon-reload
sudo systemctl enable kfz-kontakt
sudo systemctl start kfz-kontakt
sudo systemctl status kfz-kontakt
```

### 3. Logs anschauen

```bash
sudo journalctl -u kfz-kontakt -f
```

---

## Nginx Reverse Proxy

### Nginx installieren

```bash
apt install -y nginx
```

### Konfiguration

```bash
nano /etc/nginx/sites-available/kfz-kontakt
```

```nginx
upstream kfz_kontakt {
    server localhost:8000;
}

server {
    listen 80;
    listen [::]:80;
    server_name kfz-kontakt.deine-domain.de;

    client_max_body_size 10M;

    location / {
        proxy_pass http://kfz_kontakt;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }

    location /static {
        alias /opt/kfz-kontakt/frontend/dashboard;
        expires 30d;
    }
}
```

### Aktivieren

```bash
sudo ln -s /etc/nginx/sites-available/kfz-kontakt /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## SSL mit Let's Encrypt

### Certbot installieren

```bash
apt install -y certbot python3-certbot-nginx
```

### Zertifikat erstellen

```bash
sudo certbot --nginx -d kfz-kontakt.deine-domain.de
```

Auto-Renewal wird automatisch konfiguriert.

---

## Firewall (UFW)

```bash
apt install -y ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP
ufw allow 443/tcp  # HTTPS
ufw enable
```

---

## Datenbank Backup

### Tägliches Backup (Cron)

```bash
crontab -e
```

```bash
0 2 * * * cp /opt/kfz-kontakt/backend/kfz_kontakt.db /backup/kfz_kontakt_$(date +\%Y\%m\%d).db
```

### Manuelles Backup

```bash
cp /opt/kfz-kontakt/backend/kfz_kontakt.db kfz_kontakt_backup_$(date +%Y%m%d_%H%M%S).db
```

---

## Monitoring & Maintenance

### Server-Status prüfen

```bash
# Service Status
systemctl status kfz-kontakt

# Disk Space
df -h

# Memory
free -h

# Database Size
ls -lh /opt/kfz-kontakt/backend/kfz_kontakt.db
```

### Database bereinigen (optional)

```bash
cd /opt/kfz-kontakt/backend
source venv/bin/activate
python3 << 'EOF'
from database import SessionLocal, engine
from models import Base, Message
from sqlalchemy import delete
from datetime import datetime, timedelta

db = SessionLocal()

# Alte Nachrichten löschen (älter als 90 Tage)
old_date = datetime.utcnow() - timedelta(days=90)
db.execute(delete(Message).where(Message.created_at < old_date))
db.commit()
db.close()

print("✅ Alte Nachrichten gelöscht")
EOF
```

---

## Troubleshooting

### "Port 8000 already in use"

```bash
# Finde Prozess
sudo lsof -i :8000

# Beende ihn
sudo kill -9 <PID>
```

### "Telegram notification failed"

Prüfe:
1. Bot Token ist korrekt
2. Chat ID ist korrekt
3. Bot ist in der Gruppe/Chat hinzugefügt
4. Bot hat Send-Berechtigung

```bash
# Teste Telegram API
curl -X POST https://api.telegram.org/bot<TOKEN>/sendMessage \
  -d chat_id=<CHAT_ID> \
  -d text="Test Nachricht"
```

### "Database locked"

```bash
# Service neu starten
sudo systemctl restart kfz-kontakt

# Oder: SQLite Prozess prüfen
sudo lsof /opt/kfz-kontakt/backend/kfz_kontakt.db
```

### "Permission denied on /opt/kfz-kontakt"

```bash
sudo chown -R www-data:www-data /opt/kfz-kontakt
sudo chmod -R 755 /opt/kfz-kontakt
```

---

## Updates

### Code aktualisieren

```bash
cd /opt/kfz-kontakt
git pull origin main

# Dependencies prüfen
cd backend
source venv/bin/activate
pip install -r requirements.txt

# Service neu starten
sudo systemctl restart kfz-kontakt
```

---

## Sicherheit Checklist

- [ ] TELEGRAM_BOT_TOKEN & TELEGRAM_CHAT_ID sind in .env (nicht im Code!)
- [ ] `.env` ist im `.gitignore`
- [ ] Database ist nicht öffentlich zugänglich
- [ ] Firewall nur Port 80/443 öffnen (nicht 8000)
- [ ] SSL Zertifikat aktiv (HTTPS)
- [ ] Regular Backups laufen
- [ ] Updates regelmäßig einspielen
- [ ] Logs regelmäßig prüfen

---

## Performance Tuning

### Gunicorn statt uvicorn (für Production)

```bash
pip install gunicorn
```

Systemd Service anpassen:

```ini
ExecStart=/opt/kfz-kontakt/backend/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 main:app
```

### Nginx Caching

```nginx
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m;

location / {
    proxy_cache api_cache;
    proxy_cache_valid 200 10m;
}
```

---

## Support & Debugging

Logs anschauen:

```bash
# Systemd logs
sudo journalctl -u kfz-kontakt -n 50 -f

# Nginx logs
sudo tail -f /var/log/nginx/error.log

# Manuell starten für Debugging
cd /opt/kfz-kontakt/backend
source venv/bin/activate
python3 main.py
```

---

Version: 1.0  
Zuletzt aktualisiert: 2026-05-12
