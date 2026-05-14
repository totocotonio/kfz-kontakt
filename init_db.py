#!/usr/bin/env python3
"""
Initialisiert die Datenbank und erstellt einen Admin-User mit Telegram Chat ID.
Auf dem Server ausführen: python3 init_db.py <telegram_chat_id>
"""

import sys
import sqlite3
from datetime import datetime

if len(sys.argv) < 2:
    print("Fehler: Telegram Chat ID erforderlich")
    print("Benutzung: python3 init_db.py <telegram_chat_id>")
    print("\nBeispiel: python3 init_db.py 123456789")
    sys.exit(1)

telegram_chat_id = sys.argv[1]
db_path = '/opt/kfz-kontakt/kfz_kontakt.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"Verbindung zur Datenbank: {db_path}")

    # 1. Create users table
    print("\n[1] Erstelle users-Tabelle...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(255),
            telegram_chat_id VARCHAR(255) UNIQUE,
            telegram_username VARCHAR(255),
            phone_number VARCHAR(20),
            whatsapp_number VARCHAR(20),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    print("✓ users-Tabelle erstellt/existiert")

    # 2. Create categories table
    print("\n[2] Erstelle categories-Tabelle...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) UNIQUE,
            description TEXT,
            icon VARCHAR(50)
        )
    ''')
    conn.commit()
    print("✓ categories-Tabelle erstellt/existiert")

    # 3. Create qr_codes table
    print("\n[3] Erstelle qr_codes-Tabelle...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS qr_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            unique_id VARCHAR(50) UNIQUE,
            label VARCHAR(255),
            title VARCHAR(255),
            design VARCHAR(50) DEFAULT 'default',
            background_color VARCHAR(7) DEFAULT '#f5f5f5',
            logo VARCHAR(500),
            license_plate VARCHAR(50),
            vehicle_image_path VARCHAR(500),
            icon_type VARCHAR(50) DEFAULT 'phone',
            icon_position VARCHAR(50) DEFAULT 'bottom',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    print("✓ qr_codes-Tabelle erstellt/existiert")

    # 4. Create messages table
    print("\n[4] Erstelle messages-Tabelle...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qr_code_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            category_id INTEGER,
            sender_name VARCHAR(255),
            sender_contact VARCHAR(255),
            message TEXT,
            read INTEGER DEFAULT 0,
            responded INTEGER DEFAULT 0,
            contact_method VARCHAR(20) DEFAULT 'telegram',
            sms_sid VARCHAR(50),
            sms_status VARCHAR(20) DEFAULT 'pending',
            whatsapp_sid VARCHAR(50),
            whatsapp_status VARCHAR(20) DEFAULT 'pending',
            status_updated_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (qr_code_id) REFERENCES qr_codes(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    ''')
    conn.commit()
    print("✓ messages-Tabelle erstellt/existiert")

    # 5. Create default categories
    print("\n[5] Füge Default-Kategorien ein...")
    default_categories = [
        ('🅿️ Parkplatz', 'Parkplatz-bezogene Nachricht'),
        ('💡 Beleuchtung', 'Beleuchtungs-Problem'),
        ('🪟 Fenster', 'Fenster-Problem'),
        ('⚠️ Schaden', 'Fahrzeug-Schaden'),
        ('📝 Sonstiges', 'Sonstige Nachricht'),
    ]

    for name, desc in default_categories:
        cursor.execute(
            'INSERT OR IGNORE INTO categories (name, description) VALUES (?, ?)',
            (name, desc)
        )
    conn.commit()
    print("✓ Kategorien hinzugefügt")

    # 6. Create or update admin user with Telegram Chat ID
    print(f"\n[6] Erstelle/aktualisiere Admin-User mit Telegram Chat ID: {telegram_chat_id}")
    cursor.execute(
        '''INSERT OR REPLACE INTO users (name, telegram_chat_id, created_at)
           VALUES (?, ?, CURRENT_TIMESTAMP)''',
        ('Admin', telegram_chat_id)
    )
    conn.commit()

    # Get user ID
    cursor.execute('SELECT id FROM users WHERE telegram_chat_id = ?', (telegram_chat_id,))
    user_result = cursor.fetchone()
    admin_user_id = user_result[0] if user_result else None
    print(f"✓ Admin-User erstellt/aktualisiert (ID: {admin_user_id})")

    # 7. Verify database state
    print("\n[7] Überprüfe Datenbank-Status...")
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM categories")
    cat_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM qr_codes")
    qr_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM messages")
    msg_count = cursor.fetchone()[0]

    print(f"  Users: {user_count}")
    print(f"  Categories: {cat_count}")
    print(f"  QR Codes: {qr_count}")
    print(f"  Messages: {msg_count}")

    # 8. Check telegram chat ID
    cursor.execute("SELECT * FROM users WHERE telegram_chat_id = ?", (telegram_chat_id,))
    admin_check = cursor.fetchone()
    if admin_check:
        print(f"\n✅ Admin-User erfolgreich erstellt!")
        print(f"   Telegram Chat ID: {admin_check[2]}")
    else:
        print(f"\n❌ Fehler: Admin-User konnte nicht erstellt werden!")

    conn.close()
    print("\n✅ Datenbankinitialisierung abgeschlossen!")

except sqlite3.Error as e:
    print(f"❌ Datenbankfehler: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Fehler: {e}")
    sys.exit(1)
