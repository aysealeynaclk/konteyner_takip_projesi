"""
Kullanıcılar tablosunu oluşturur ve başlangıç kullanıcılarını ekler.
Yeni kullanıcı eklemek istediğinde bu dosyadaki NEW_USERS listesine
ekleyip tekrar çalıştırman yeterli.
"""

import sqlite3
import bcrypt
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database" / "containers.db"

# Buraya kullanıcı ekleme kısımları yetki adminde = true

NEW_USERS = [
    {"username": "admin", "password": "01", "is_admin": True},
    {"username": "ahmet", "password": "A1976", "is_admin": False},
]


def create_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


def add_users(conn):
    cursor = conn.cursor()
    for user in NEW_USERS:
        password_hash = bcrypt.hashpw(user["password"].encode("utf-8"), bcrypt.gensalt())
        try:
            cursor.execute("""
                INSERT INTO users (username, password_hash, is_admin)
                VALUES (?, ?, ?)
            """, (user["username"], password_hash.decode("utf-8"), int(user["is_admin"])))
            print(f"✅ Kullanıcı eklendi: {user['username']}")
        except sqlite3.IntegrityError:
            print(f"ℹ️  '{user['username']}' zaten mevcut, atlandı.")
    conn.commit()


def main():
    conn = sqlite3.connect(DB_PATH)
    create_table(conn)
    add_users(conn)

    cursor = conn.cursor()
    cursor.execute("SELECT id, username, is_admin FROM users")
    print("\n--- Mevcut Kullanıcılar ---")
    for row in cursor.fetchall():
        print(row)

    conn.close()


if __name__ == "__main__":
    main()