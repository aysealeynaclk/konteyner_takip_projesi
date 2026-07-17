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
# display_name: giriş yaptıktan sonra ekranda gösterilecek düzgün yazılmış isim
# (kullanıcı adı hangi harf büyüklüğü/Türkçe karakterle girilirse girilsin
# giriş kabul edilir, ama ekranda her zaman bu isim gösterilir).

NEW_USERS = [
    {"username": "admin", "password": "01", "is_admin": True, "display_name": "Admin"},
    {"username": "ahmet", "password": "A1976", "is_admin": False, "display_name": "Ahmet"},
    {"username": "mehmet", "password": "53", "is_admin": False, "display_name": "Mehmet"},
    {"username": "ayse", "password": "61", "is_admin": False, "display_name": "Ayşe"},
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
    cursor.execute("PRAGMA table_info(users)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    if "display_name" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN display_name TEXT")
    conn.commit()


def add_users(conn):
    cursor = conn.cursor()
    for user in NEW_USERS:
        password_hash = bcrypt.hashpw(user["password"].encode("utf-8"), bcrypt.gensalt())
        try:
            cursor.execute("""
                INSERT INTO users (username, password_hash, is_admin, display_name)
                VALUES (?, ?, ?, ?)
            """, (user["username"], password_hash.decode("utf-8"), int(user["is_admin"]), user["display_name"]))
            print(f"✅ Kullanıcı eklendi: {user['username']}")
        except sqlite3.IntegrityError:
            cursor.execute(
                "UPDATE users SET display_name = ? WHERE username = ?",
                (user["display_name"], user["username"]),
            )
            print(f"ℹ️  '{user['username']}' zaten mevcut, display_name güncellendi.")
    conn.commit()


def main():
    conn = sqlite3.connect(DB_PATH)
    create_table(conn)
    add_users(conn)

    cursor = conn.cursor()
    cursor.execute("SELECT id, username, is_admin, display_name FROM users")
    print("\n--- Mevcut Kullanıcılar ---")
    for row in cursor.fetchall():
        print(row)

    conn.close()


if __name__ == "__main__":
    main()
