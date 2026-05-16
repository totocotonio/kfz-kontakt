#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Add new contact method fields to users table"""

from sqlalchemy import create_engine, text
import os

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./kfz_kontakt.db")

engine = create_engine(DATABASE_URL)

with engine.begin() as conn:
    # SQLite doesn't have easy ALTER COLUMN, so we check if columns exist first
    result = conn.execute(text("PRAGMA table_info(users)"))
    columns = {row[1] for row in result}

    if "enable_telegram" not in columns:
        print("Adding enable_telegram column...")
        conn.execute(text("ALTER TABLE users ADD COLUMN enable_telegram BOOLEAN DEFAULT 1"))

    if "enable_sms" not in columns:
        print("Adding enable_sms column...")
        conn.execute(text("ALTER TABLE users ADD COLUMN enable_sms BOOLEAN DEFAULT 0"))

    if "enable_whatsapp" not in columns:
        print("Adding enable_whatsapp column...")
        conn.execute(text("ALTER TABLE users ADD COLUMN enable_whatsapp BOOLEAN DEFAULT 0"))

    print("Migration complete!")
