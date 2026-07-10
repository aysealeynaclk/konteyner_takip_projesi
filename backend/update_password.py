"""
Var olan bir kullanıcının şifresini günceller.
Kullanımı: aşağıdaki USERNAME ve NEW_PASSWORD değerlerini değiştirip çalıştır.
"""

import sqlite3
import bcrypt
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database" / "containers.db"

# Buradaki bilgileri kendi ihtiyacına göre değiştir
USERNAME = "admin"
NEW_PASSWORD = "01"


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    password_hash = bcrypt.hashpw(NEW_PASSWORD.encode("utf-8"), bcrypt.gensalt())

    cursor.execute("""
        UPDATE users SET password_hash = ? WHERE username = ?
    """, (password_hash.decode("utf-8"), USERNAME))

    if cursor.rowcount == 0:
        print(f"❌ '{USERNAME}' adında bir kullanıcı bulunamadı.")
    else:
        print(f"✅ '{USERNAME}' kullanıcısının şifresi güncellendi.")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()