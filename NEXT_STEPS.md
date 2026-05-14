# Telegram Integration - Nächste Schritte

## Status (Version 1.0.173)

✅ **Abgeschlossen:**
- Telegram Chat ID Registration Endpoint implementiert
- Telegram Webhook Handler für /start-Befehl
- Setup Script für automatische Chat ID Registrierung
- Datenbank-Initialisierung Script (init_db.py)
- Dokumentation und Troubleshooting Guides

❌ **Noch zu tun:**
- Server neustarten (um neue Endpoints verfügbar zu machen)
- Deine Telegram Chat ID registrieren
- Test-Nachricht senden

---

## Was wurde geändert?

### Neue Endpoints
- `POST /api/telegram/register` - Manuelle Chat ID Registrierung
- `POST /webhooks/telegram` - Automatische Registrierung via Telegram Bot

### Verbesserte Telegram Integration
- Chat ID wird jetzt aus der Datenbank gelesen statt nur aus .env
- Automatische Fallback auf Config, falls Benutzer nicht registriert
- Besseres Error Handling und Logging

---

## Was du jetzt tun musst

### 1️⃣ Server Neustarten

**SSH (Terminal):**
```bash
ssh kfz@192.168.178.47
cd /opt/kfz-kontakt
git pull
sudo systemctl restart kfz-kontakt
```

**Oder (falls SSH nicht funktioniert):**
- Nutze einen Remote-Management-Tool für deinen Server
- Oder nutze die Web-Oberfläche deines Hosting-Providers

### 2️⃣ Telegram Chat ID Finden und Registrieren

**Einfachste Methode:**
```bash
python3 setup_telegram.py
```

Das Script wird dich Schritt für Schritt durchleiten.

**Oder manuell:**

1. Finde deine Chat ID:
   - Öffne Telegram
   - Suche "@IDBot"
   - Starte den Bot
   - Kopiere deine Chat ID (z.B. 123456789)

2. Registriere die Chat ID via API:
   ```bash
   curl -X POST https://kfz-kontakt.michaely.de/api/telegram/register \
     -H "Content-Type: application/json" \
     -d '{"chat_id": "123456789"}'
   ```

### 3️⃣ Test

1. Öffne einen QR-Code: https://kfz-kontakt.michaely.de/qr/YOUR_UNIQUE_ID
2. Wähle eine Kategorie (z.B. "Schaden")
3. Schreib eine Test-Nachricht
4. Klick "Nachricht senden"
5. Überprüfe Telegram - du solltest die Nachricht erhalten!

---

## Was funktioniert jetzt?

✅ **Telegram-Benachrichtigungen**
- Automatische Benachrichtigungen bei neuen Nachrichten
- Kategorie wird automatisch angezeigt

✅ **SMS via Twilio**
- Wenn konfiguriert

✅ **WhatsApp via Twilio**
- Wenn konfiguriert (Sandbox oder Business Account)

---

## Files zu beachten

### Auf dem Server
- `/opt/kfz-kontakt/backend/routes/scanner.py` - Neue Endpoints
- `/opt/kfz-kontakt/backend/services/telegram_service.py` - Verbesserte Service
- `/opt/kfz-kontakt/init_db.py` - Datenbank-Initialisierung (falls nötig)

### Lokal
- `setup_telegram.py` - Automatisches Setup Script
- `TELEGRAM_SETUP.md` - Ausführliche Anleitung
- `init_db.py` - Datenbank-Initialisierung Script

---

## Checklist

- [ ] Server neu gestartet und neue Version geladen (`git pull`)
- [ ] Deine Telegram Chat ID gefunden (z.B. mit @IDBot)
- [ ] Chat ID registriert via `setup_telegram.py` oder API
- [ ] Test-Nachricht gesendet und in Telegram empfangen
- [ ] Kategorie wird korrekt angezeigt
- [ ] SMS/WhatsApp funktionieren (falls konfiguriert)

---

## Support

### Wenn Telegram nicht funktioniert:

1. Überprüfe, dass der Service neu gestartet wurde:
   ```bash
   systemctl status kfz-kontakt
   ```

2. Überprüfe die Logs:
   ```bash
   journalctl -u kfz-kontakt -f
   ```

3. Überprüfe, dass die Chat ID registriert ist:
   ```bash
   curl https://kfz-kontakt.michaely.de/api/version
   ```

4. Stelle sicher, dass der Telegram Bot Token korrekt ist (.env)

5. Überprüfe, dass die users-Tabelle existiert (sollte vom Service erstellt werden)

---

## Weitere Features (geplant)

- [ ] Telegram Bot Commands Handler (/stop, /help, etc.)
- [ ] Benutzer-Validierung (nur registrierte Admins können Nachrichten empfangen)
- [ ] WhatsApp Business Account Integration
- [ ] SMS Verification für Telefonnummern
- [ ] Message Archivierung und Suche
