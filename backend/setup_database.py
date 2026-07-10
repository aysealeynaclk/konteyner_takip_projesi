"""
Bu script:
1. SQLite veritabanını oluşturur (yoksa)
2. gate_transactions tablosunu oluşturur (yoksa)
3. Test amaçlı örnek konteyner giriş/çıkış verileri ekler

Gerçek Gate Transaction verisi kaynağı belli olduğunda,
sadece bu dosyadaki "test verisi ekleme" kısmı, gerçek veriyi
okuyup INSERT eden bir koda dönüştürülecek. Şema (tablo yapısı) değişmeyecek.
"""

import sqlite3
from datetime import datetime, timedelta
import random

DB_PATH = "database/containers.db"

def create_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gate_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            container_no TEXT NOT NULL,
            transaction_type TEXT CHECK(transaction_type IN ('IN', 'OUT')) NOT NULL,
            gate_time DATETIME NOT NULL,
            gate_no TEXT,
            truck_plate TEXT,
            driver_name TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_container_no
        ON gate_transactions(container_no)
    """)
    conn.commit()
    print("✅ Tablo hazır: gate_transactions")


def insert_sample_data(conn):
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM gate_transactions")
    count = cursor.fetchone()[0]
    if count > 0:
        print(f"ℹ️  Tabloda zaten {count} kayıt var, örnek veri eklenmedi.")
        return

    sample_containers = [
        "TSTU1101101", "MSKU2203456", "CMAU3304789",
        "HLXU4405678", "OOLU5506789", "COSU6607890"
    ]

    gates = ["A1", "A2", "A3", "B1", "B2"]
    plates = ["34ABC123", "35DEF456", "06GHI789", "16JKL012"]
    drivers = ["Ahmet Yılmaz", "Mehmet Kaya", "Ali Demir", "Veli Şahin"]

    rows = []
    base_time = datetime(2026, 7, 1, 8, 0, 0)

    for container in sample_containers:
        entry_time = base_time + timedelta(
            days=random.randint(0, 5),
            hours=random.randint(0, 10)
        )
        rows.append((
            container, "IN", entry_time.strftime("%Y-%m-%d %H:%M:%S"),
            random.choice(gates), random.choice(plates), random.choice(drivers)
        ))

        if random.random() > 0.3:
            exit_time = entry_time + timedelta(hours=random.randint(5, 72))
            rows.append((
                container, "OUT", exit_time.strftime("%Y-%m-%d %H:%M:%S"),
                random.choice(gates), random.choice(plates), random.choice(drivers)
            ))

    cursor.executemany("""
        INSERT INTO gate_transactions
        (container_no, transaction_type, gate_time, gate_no, truck_plate, driver_name)
        VALUES (?, ?, ?, ?, ?, ?)
    """, rows)

    conn.commit()
    print(f"✅ {len(rows)} örnek kayıt eklendi.")


def main():
    import os
    os.makedirs("database", exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    create_table(conn)
    insert_sample_data(conn)

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM gate_transactions ORDER BY container_no, gate_time")
    print("\n--- Veritabanındaki Kayıtlar ---")
    for row in cursor.fetchall():
        print(row)

    conn.close()


if __name__ == "__main__":
    main()