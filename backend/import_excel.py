"""
Excel'deki Gate Transaction verisini SQLite'a aktarır.

İki tablo oluşturur:
1. gate_transactions_raw  -> Excel'deki TÜM sütunlar, olduğu gibi (yedek/genişleme için)
2. gate_transactions      -> Sadece şu an kullandığımız temiz sütunlar (LLM bunu sorgulayacak)
"""

import pandas as pd
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database" / "containers.db"
EXCEL_PATH = BASE_DIR / "Veriler.xlsx"  # Excel dosyasını bu klasöre koyacaksın


def main():
    print(f"Excel okunuyor: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH)
    print(f"{len(df)} satır, {len(df.columns)} sütun bulundu.")

    (BASE_DIR / "database").mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    # -----------------------------------------------------
    # 1. HAM TABLO: Excel'deki her şeyi olduğu gibi yükle
    # -----------------------------------------------------
    df.to_sql("gate_transactions_raw", conn, if_exists="replace", index=False)
    print("✅ gate_transactions_raw tablosu oluşturuldu (tüm sütunlar).")

    # -----------------------------------------------------
    # 2. TEMİZ TABLO: sadece ihtiyacımız olan sütunlar
    # -----------------------------------------------------
    clean_df = df[["UnitId", "TimeEnteredYard", "TimeExitedYard", "TransactionStatus"]].copy()
    clean_df.columns = ["container_no", "time_entered_yard", "time_exited_yard", "transaction_status"]
    # Konteyner numarası boş olan satırları at (varsa)
    clean_df = clean_df.dropna(subset=["container_no"])

    clean_df.to_sql("gate_transactions", conn, if_exists="replace", index=False)

    cursor = conn.cursor()
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_clean_container_no
        ON gate_transactions(container_no)
    """)
    conn.commit()

    print(f"✅ gate_transactions tablosu oluşturuldu ({len(clean_df)} satır).")

    # Kontrol amaçlı ilk birkaç satırı göster
    print("\n--- Örnek kayıtlar ---")
    cursor.execute("SELECT * FROM gate_transactions LIMIT 5")
    for row in cursor.fetchall():
        print(row)

    conn.close()


if __name__ == "__main__":
    main()