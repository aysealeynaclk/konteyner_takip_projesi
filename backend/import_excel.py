"""
Excel'deki Gate Transaction verisini SQLite'a aktarır.

İki tablo oluşturur/günceller:
1. gate_transactions_raw  -> Excel'deki TÜM sütunlar, olduğu gibi (yedek/genişleme için)
2. gate_transactions      -> Sadece şu an kullandığımız temiz sütunlar (LLM bunu sorgulayacak)

Birden fazla liman desteklenir: her satırın FacilityId'si de temiz tabloya
"facility_id" olarak taşınır. Script çalıştığında sadece o Excel'deki
FacilityId'lere ait eski satırlar silinip yeniden eklenir; diğer limanların
verisi bozulmaz. Yani aynı Excel'i tekrar yüklemek güvenlidir (satır
çoğalmaz), farklı bir limanın Excel'ini yüklemek ise mevcut limanları silmez.

Not: temiz tabloda ayrıca "source" sütunu var ('excel' / 'admin'). Silme
işlemi sadece source='excel' olan satırları hedefler, admin panelinden
elle eklenen kayıtlar (source='admin') bu script tekrar çalıştırılsa bile
asla silinmez.
"""

import pandas as pd
import sqlite3
import sys
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATASETS_DIR = BASE_DIR / "datasets"
DB_PATH = BASE_DIR / "database" / "containers.db"
EXCEL_PATH = DATASETS_DIR / "Veriler.xlsx"  # Varsayılan dosya; farklı bir liman için
# python import_excel.py datasets/baska_liman.xlsx şeklinde yol verebilirsin.

# YARD tipi loc_name'lerin sonundaki blok+bay/row(+kat) kısmını yakalar.
# Örn: "Y-YCT-C24273" -> blok C, bay/row 2427, kat 3 (kat opsiyonel).
_YARD_SUFFIX_PATTERN = re.compile(r'^([A-Z])(\d{4})(\d)?$')


def _col_or_none(df, name):
    return df[name] if name in df.columns else pd.Series([None] * len(df), index=df.index)


def _derive_loc_slot_tier(loc_type, loc_name, raw_slot, raw_tier):
    """Mümkünse ham tablodaki gerçek LocSlot/LocTier'ı kullanır (örn. YCT).
    Bu veri yoksa (örn. Gebze) ve tip YARD ise loc_name'den blok+bay/row'u
    parse eder. Gebze'nin kodlarında kat bilgisi hiç yer almadığı için o
    durumda kat (tier) None kalır — uydurulmaz."""
    if pd.notna(raw_slot) or pd.notna(raw_tier):
        return raw_slot, raw_tier
    if loc_type != "YARD" or not isinstance(loc_name, str):
        return None, None
    suffix = loc_name.split("-")[-1]
    match = _YARD_SUFFIX_PATTERN.match(suffix)
    if not match:
        return None, None
    block, bay_row, tier_digit = match.groups()
    if tier_digit:
        return f"{block}{bay_row}.{tier_digit}", float(tier_digit)
    return f"{block}{bay_row}", None


def main():
    excel_path = Path(sys.argv[1]) if len(sys.argv) > 1 else EXCEL_PATH
    print(f"Excel okunuyor: {excel_path}")
    df = pd.read_excel(excel_path)
    print(f"{len(df)} satır, {len(df.columns)} sütun bulundu.")

    facility_ids = sorted(df["FacilityId"].dropna().unique().tolist())
    print(f"Excel'deki liman(lar): {facility_ids}")

    (BASE_DIR / "database").mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # -----------------------------------------------------
    # 1. HAM TABLO: bu limanlara ait eski satırları silip yeniden ekle
    # -----------------------------------------------------
    raw_exists = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='gate_transactions_raw'"
    ).fetchone()
    if raw_exists:
        cursor.executemany(
            "DELETE FROM gate_transactions_raw WHERE FacilityId = ?",
            [(f,) for f in facility_ids],
        )
        conn.commit()
        # Yeni Excel'in sütun sayısı/isimleri eski tablodan farklı olabilir
        # (örn. elle hazırlanmış, daha az sütunlu bir dosya). Eksik sütunlar
        # NULL olarak eklenir, ham tablodaki fazladan sütunlar korunur.
        raw_cols = [row[1] for row in cursor.execute("PRAGMA table_info(gate_transactions_raw)")]
        for col in df.columns:
            if col not in raw_cols:
                cursor.execute(f'ALTER TABLE gate_transactions_raw ADD COLUMN "{col}" TEXT')
                raw_cols.append(col)
        conn.commit()
        df_raw = df.reindex(columns=raw_cols)
    else:
        df_raw = df
    df_raw.to_sql("gate_transactions_raw", conn, if_exists="append", index=False)
    print("✅ gate_transactions_raw güncellendi (tüm sütunlar).")

    # -----------------------------------------------------
    # 2. TEMİZ TABLO: sadece ihtiyacımız olan sütunlar + facility_id
    # -----------------------------------------------------
    clean_df = df[[
        "UnitId", "TimeEnteredYard", "TimeExitedYard", "TransactionStatus",
        "LocName", "TruckVisitMinutesInYard", "TransactionType", "Damage", "FreightKind",
        "FacilityId",
    ]].copy()
    clean_df.columns = [
        "container_no", "time_entered_yard", "time_exited_yard", "transaction_status",
        "loc_name", "truck_visit_minutes_in_yard", "transaction_type", "damage", "freight_kind",
        "facility_id",
    ]

    # loc_type doğrudan ham veriden gelir; loc_slot/loc_tier mümkünse ham
    # veriden (örn. YCT), yoksa loc_name'den parse edilerek türetilir (örn. Gebze).
    loc_type_col = _col_or_none(df, "LocType")
    raw_slot_col = _col_or_none(df, "LocSlot")
    raw_tier_col = _col_or_none(df, "LocTier")
    derived = [
        _derive_loc_slot_tier(lt, ln, rs, rt)
        for lt, ln, rs, rt in zip(loc_type_col, df["LocName"], raw_slot_col, raw_tier_col)
    ]
    clean_df["loc_type"] = loc_type_col.values
    clean_df["loc_slot"] = [d[0] for d in derived]
    clean_df["loc_tier"] = [d[1] for d in derived]

    # Konteyner numarası boş olan satırları at (varsa)
    clean_df = clean_df.dropna(subset=["container_no"])

    # Tabloyu elle, id (PRIMARY KEY) sütunuyla oluşturuyoruz ki admin panelinden
    # eklenen/kapatılan/iptal edilen kayıtlar tekil olarak referans alınabilsin.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gate_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            container_no TEXT,
            time_entered_yard TIMESTAMP,
            time_exited_yard TIMESTAMP,
            transaction_status TEXT,
            loc_name TEXT,
            truck_visit_minutes_in_yard REAL,
            transaction_type TEXT,
            damage INTEGER,
            freight_kind TEXT,
            facility_id TEXT,
            source TEXT NOT NULL DEFAULT 'excel',
            loc_type TEXT,
            loc_slot TEXT,
            loc_tier REAL
        )
    """)
    # Eski sürümden yükseltilen DB'lerde bazı sütunlar olmayabilir.
    existing_cols = [row[1] for row in cursor.execute("PRAGMA table_info(gate_transactions)")]
    if "facility_id" not in existing_cols:
        cursor.execute("ALTER TABLE gate_transactions ADD COLUMN facility_id TEXT")
    if "source" not in existing_cols:
        cursor.execute("ALTER TABLE gate_transactions ADD COLUMN source TEXT NOT NULL DEFAULT 'excel'")
    if "loc_type" not in existing_cols:
        cursor.execute("ALTER TABLE gate_transactions ADD COLUMN loc_type TEXT")
    if "loc_slot" not in existing_cols:
        cursor.execute("ALTER TABLE gate_transactions ADD COLUMN loc_slot TEXT")
    if "loc_tier" not in existing_cols:
        cursor.execute("ALTER TABLE gate_transactions ADD COLUMN loc_tier REAL")

    # Sadece bu Excel'den daha önce yüklenmiş satırları sil (source='excel'),
    # admin panelinden eklenen kayıtlara (source='admin') asla dokunma.
    cursor.executemany(
        "DELETE FROM gate_transactions WHERE facility_id = ? AND source = 'excel'",
        [(f,) for f in facility_ids],
    )
    conn.commit()
    clean_df.to_sql("gate_transactions", conn, if_exists="append", index=False)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_clean_container_no
        ON gate_transactions(container_no)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_clean_facility_id
        ON gate_transactions(facility_id)
    """)
    conn.commit()

    print(f"✅ gate_transactions güncellendi ({len(clean_df)} satır eklendi/güncellendi, liman(lar): {facility_ids}).")

    # Kontrol amaçlı ilk birkaç satırı göster
    print("\n--- Örnek kayıtlar ---")
    cursor.execute("SELECT * FROM gate_transactions LIMIT 5")
    for row in cursor.fetchall():
        print(row)

    conn.close()


if __name__ == "__main__":
    main()