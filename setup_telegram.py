#!/usr/bin/env python3
"""
Setup Script zum Finden und Registrieren der Telegram Chat ID
"""

import requests
import sys
import json
from pathlib import Path

def get_telegram_chat_id(bot_token):
    """Hole ungelesene Telegram Bot Updates, um die Chat ID zu finden"""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            print(f"❌ Fehler beim Abrufen von Telegram Updates: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

        data = response.json()

        if not data.get("ok"):
            print(f"❌ Telegram API Fehler: {data.get('description', 'Unbekannter Fehler')}")
            return None

        updates = data.get("result", [])

        if not updates:
            print("⚠️  Keine Telegram Updates gefunden")
            print("   Bitte schreibe eine Nachricht an deinen Bot und starte diesen Script erneut")
            return None

        # Suche nach /start oder anderen Nachrichten
        for update in reversed(updates):  # Von neuesten zu ältest
            if "message" in update:
                message = update["message"]
                chat = message.get("chat", {})
                chat_id = chat.get("id")
                username = chat.get("username", "")
                text = message.get("text", "")

                if chat_id:
                    print(f"\n✅ Telegram Chat ID gefunden!")
                    print(f"   Chat ID: {chat_id}")
                    if username:
                        print(f"   Username: @{username}")
                    print(f"   Letzte Nachricht: {text[:50]}")
                    return chat_id

        print("⚠️  Keine Chat ID in den Updates gefunden")
        return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Netzwerkfehler: {e}")
        return None
    except Exception as e:
        print(f"❌ Fehler beim Abrufen der Chat ID: {e}")
        return None

def register_chat_id(server_url, chat_id, username=None):
    """Registriere die Chat ID auf dem Server"""
    try:
        url = f"{server_url}/api/telegram/register"
        payload = {
            "chat_id": str(chat_id),
            "username": username or ""
        }

        response = requests.post(url, json=payload, timeout=10)

        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Telegram Chat ID erfolgreich registriert!")
            print(f"   Server Response: {result.get('message', 'OK')}")
            return True
        else:
            print(f"❌ Registrierung fehlgeschlagen: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Netzwerkfehler: {e}")
        return False
    except Exception as e:
        print(f"❌ Fehler bei der Registrierung: {e}")
        return False

def main():
    print("=" * 60)
    print("KFZ Kontakt - Telegram Chat ID Setup")
    print("=" * 60)

    # 1. Bot Token einlesen
    print("\n[1] Telegram Bot Token")

    env_file = Path(".env")
    bot_token = None

    if env_file.exists():
        try:
            with open(env_file, "r") as f:
                for line in f:
                    if line.startswith("TELEGRAM_BOT_TOKEN="):
                        bot_token = line.split("=", 1)[1].strip()
                        print(f"   ✓ Bot Token aus .env geladen")
                        break
        except Exception as e:
            print(f"   ⚠️  Fehler beim Lesen der .env Datei: {e}")

    if not bot_token:
        print("   Bot Token nicht gefunden in .env")
        bot_token = input("   Bitte gib deinen Telegram Bot Token ein: ").strip()

        if not bot_token:
            print("❌ Kein Bot Token angegeben")
            sys.exit(1)

    # 2. Chat ID abrufen
    print("\n[2] Suche nach Telegram Chat ID...")
    print("   💡 Hinweis: Schreibe eine Nachricht an deinen Telegram Bot,")
    print("      damit dieser Script deine Chat ID finden kann")

    chat_id = get_telegram_chat_id(bot_token)

    if not chat_id:
        print("\n❌ Chat ID konnte nicht automatisch gefunden werden")
        print("\n📱 Alternative: Finde deine Chat ID manuell:")
        print("   1. Schreibe eine beliebige Nachricht an deinen Bot")
        print("   2. Rufe auf: https://api.telegram.org/bot<TOKEN>/getUpdates")
        print("   3. Suche im JSON nach 'chat' -> 'id'")
        print("   4. Gib die Chat ID hier ein:")

        chat_id_str = input("   Chat ID: ").strip()

        if not chat_id_str:
            print("❌ Keine Chat ID eingegeben")
            sys.exit(1)

        try:
            chat_id = int(chat_id_str)
        except ValueError:
            print("❌ Ungültige Chat ID (muss eine Zahl sein)")
            sys.exit(1)

    # 3. Server-URL
    print("\n[3] Server-URL")
    server_url = input("   Server-URL [https://kfz-kontakt.michaely.de]: ").strip()

    if not server_url:
        server_url = "https://kfz-kontakt.michaely.de"

    if not server_url.startswith("http"):
        server_url = f"https://{server_url}"

    print(f"   ✓ Server: {server_url}")

    # 4. Registrierung
    print("\n[4] Registriere Chat ID auf dem Server...")

    if register_chat_id(server_url, chat_id):
        print("\n" + "=" * 60)
        print("✅ Setup erfolgreich abgeschlossen!")
        print("=" * 60)
        print("\nDu solltest jetzt Telegram-Benachrichtigungen erhalten, wenn:")
        print("- Jemand eine Nachricht über den QR-Code sendet")
        print("- Die Kategorie automatisch in der Nachricht angezeigt wird")
        print("\nZum Testen:")
        print("1. Öffne einen QR-Code der App")
        print("2. Sende eine Test-Nachricht")
        print("3. Prüfe deine Telegram-Nachrichten")

    else:
        print("\n" + "=" * 60)
        print("❌ Setup fehlgeschlagen!")
        print("=" * 60)
        print("\nTroubleshooting:")
        print("- Überprüfe deine Internet-Verbindung")
        print("- Stelle sicher, dass der Server läuft: https://kfz-kontakt.michaely.de/")
        print("- Überprüfe den Bot Token")
        sys.exit(1)

if __name__ == "__main__":
    main()
