# Telegram Chat ID Setup für KFZ Kontakt

Version: 1.0.172+

## Das Problem
Die Telegram-Benachrichtigungen funktionieren nicht, weil die Admin-Chat ID nicht registriert ist.

## Die Lösung
Du musst deine Telegram Chat ID registrieren, damit der Bot weiß, wohin die Nachrichten gesendet werden sollen.

---

## Option 1: Automatisches Setup (Empfohlen)

### Schritt 1: Voraussetzungen
- Python 3 installiert
- Zugriff auf den Telegram Bot Token (aus der .env Datei auf dem Server)

### Schritt 2: Setup Script ausführen

**Lokal (auf deinem Computer):**
```bash
python3 setup_telegram.py
```

Das Script wird dich auffordern:
1. Den Telegram Bot Token einzugeben (oder aus .env zu laden)
2. Eine Nachricht an deinen Telegram Bot zu schreiben
3. Die Chat ID automatisch zu finden
4. Die Chat ID auf dem Server zu registrieren

---

## Option 2: Manuelle Registrierung via API

### Schritt 1: Telegram Chat ID herausfinden

**Methode A: Mit @IDBot im Telegram**
1. Öffne Telegram
2. Suche "@IDBot"
3. Starte den Bot mit `/start`
4. Der Bot zeigt dir deine Chat ID

**Methode B: Mit Telegram Bot API**
1. Schreibe eine Nachricht an deinen KFZ Kontakt Bot
2. Öffne folgende URL im Browser (ersetze TOKEN mit deinem Bot Token):
   ```
   https://api.telegram.org/botTOKEN/getUpdates
   ```
3. Suche in der JSON-Response nach `"chat":{"id":123456789}`
4. Die Zahl ist deine Chat ID

### Schritt 2: API Call zum Registrieren

Führe einen HTTP-POST-Request durch:

```bash
curl -X POST https://kfz-kontakt.michaely.de/api/telegram/register \
  -H "Content-Type: application/json" \
  -d '{"chat_id": "123456789", "username": "dein_telegram_username"}'
```

Ersetze:
- `123456789` mit deiner echten Chat ID
- `dein_telegram_username` mit deinem Telegram Username (optional)

**PowerShell:**
```powershell
$body = @{
    chat_id = "123456789"
    username = "dein_username"
} | ConvertTo-Json

Invoke-WebRequest -Uri "https://kfz-kontakt.michaely.de/api/telegram/register" `
    -Method POST `
    -Headers @{"Content-Type"="application/json"} `
    -Body $body
```

Erfolgreiche Antwort:
```json
{
  "status": "success",
  "message": "Telegram Chat ID registriert: 123456789",
  "user_id": 1
}
```

---

## Option 3: Server-seitiges Setup

Falls du SSH-Zugriff zum Server hast:

### Schritt 1: Service neu starten

```bash
ssh kfz@192.168.178.47

# Neue Version pullen
cd /opt/kfz-kontakt
git pull

# Service neu starten
sudo systemctl restart kfz-kontakt

# Status prüfen
systemctl status kfz-kontakt
```

### Schritt 2: Datenbank-Initialisierung (falls nötig)

Falls die users-Tabelle nicht existiert:

```bash
# Von der Server
python3 init_db.py 123456789
```

Ersetze `123456789` mit deiner Telegram Chat ID.

---

## Test

Nach der Registrierung:

1. Öffne einen QR-Code der App
2. Wähle eine Kategorie
3. Schreibe eine Test-Nachricht
4. Klick "Nachricht senden"
5. Überprüfe deine Telegram-Nachrichten

Du solltest eine Benachrichtigung mit der Nachricht und Kategorie erhalten:
```
🚗 Neue Nachricht über QR-Code: Auto 1

Von: Max Mustermann
Kategorie: ⚠️ Schaden
Nachricht: Der rechte Spiegel ist beschädigt...
```

---

## Troubleshooting

### Problem: "Chat ID nicht gefunden"
- **Lösung:** Schreib eine Nachricht an deinen Bot BEVOR du das Setup Script ausführst
- **Oder:** Verwende @IDBot um deine Chat ID zu finden

### Problem: "Chat ID ist ungültig"
- **Lösung:** Überprüfe, dass die Chat ID nur Ziffern sind (z.B. "123456789", nicht "+123456789")

### Problem: "Server antwortet nicht"
- **Lösung:** Überprüfe, dass der Server läuft: https://kfz-kontakt.michaely.de/
- **Oder:** SSH auf den Server und prüfe: `systemctl status kfz-kontakt`

### Problem: "Immer noch keine Telegram-Nachrichten"
1. Stelle sicher, dass die Chat ID richtig registriert ist:
   ```
   curl https://kfz-kontakt.michaely.de/api/telegram/register \
     -H "Content-Type: application/json" \
     -d '{"chat_id": "deine_id"}'
   ```

2. Prüfe die Server-Logs:
   ```bash
   ssh kfz@192.168.178.47
   systemctl status kfz-kontakt
   systemctl logs kfz-kontakt -f
   ```

---

## Sicherheit

⚠️ **Wichtig:**
- Die Chat ID wird in der SQLite-Datenbank gespeichert
- Der Telegram Bot Token sollte NICHT in Git committet werden
- Nur Admin kann sich registrieren (User-Validierung sollte hinzugefügt werden für Produktion)

---

## Weitere Funktionen

Nach erfolgreicher Telegram-Registrierung:
- ✅ Telegram-Benachrichtigungen bei neuen Nachrichten
- ✅ Kategorie wird automatisch angezeigt
- ✅ SMS via Twilio (falls konfiguriert)
- ✅ WhatsApp via Twilio (falls konfiguriert)
