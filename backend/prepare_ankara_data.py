"""
COREX_Ankara_Data.csv'de giriş için ayrı bir tarih sütunu (DateEnteredYard) var,
ama çıkış için yok — TimeExitedYard'da sadece saat var. Bu script girişi
DateEnteredYard+TimeEnteredYard birleştirerek, çıkışı ise giriş tarihini baz
alıp (çıkış saati giriş saatinden küçükse gece yarısını geçmiş demektir, bir
gün eklenir) tam TIMESTAMP'e çevirir. Sonucu import_excel.py'nin
okuyabileceği bir Excel dosyasına yazar.
"""

import pandas as pd
import datetime as dt
from pathlib import Path

DATASETS_DIR = Path(__file__).resolve().parent / "datasets"
SRC_PATH = DATASETS_DIR / "COREX_Ankara_Data.csv"
OUT_PATH = DATASETS_DIR / "ankara_prepared.xlsx"


def parse_time(s):
    if pd.isna(s) or str(s).strip() == "":
        return None
    return dt.datetime.strptime(str(s).strip(), "%H:%M:%S").time()


def parse_date(s):
    return dt.datetime.strptime(str(s).strip(), "%m/%d/%Y").date()


def main():
    df = pd.read_csv(SRC_PATH)
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

    entered_ts = []
    exited_ts = []
    for _, row in df.iterrows():
        entry_date = parse_date(row["DateEnteredYard"])
        entry_time = parse_time(row["TimeEnteredYard"])
        entered_dt = dt.datetime.combine(entry_date, entry_time) if entry_time else None
        entered_ts.append(entered_dt)

        exit_time = parse_time(row.get("TimeExitedYard"))
        if exit_time is None or entered_dt is None:
            exited_ts.append(None)
            continue
        exit_date = entry_date
        if exit_time < entry_time:
            exit_date = entry_date + dt.timedelta(days=1)
        exited_ts.append(dt.datetime.combine(exit_date, exit_time))

    df["TimeEnteredYard"] = entered_ts
    df["TimeExitedYard"] = exited_ts
    df = df.drop(columns=["DateEnteredYard"])

    # Doğrulama: hesaplanan süre TruckVisitMinutesInYard ile eşleşiyor mu?
    mismatches = 0
    for _, row in df.iterrows():
        if row["TimeExitedYard"] is not None and not pd.isna(row.get("TruckVisitMinutesInYard")):
            computed = (row["TimeExitedYard"] - row["TimeEnteredYard"]).total_seconds() / 60
            if abs(computed - row["TruckVisitMinutesInYard"]) > 1:
                mismatches += 1
    print(f"Süre uyuşmazlığı olan satır sayısı: {mismatches} / {len(df)}")

    df["Damage"] = df["Damage"].fillna(0).astype(int)

    df.to_excel(OUT_PATH, index=False)
    print(f"✅ Hazırlanan dosya yazıldı: {OUT_PATH} ({len(df)} satır)")
    print(df[["UnitId", "TimeEnteredYard", "TimeExitedYard", "TruckVisitMinutesInYard", "TransactionStatus", "FacilityId"]].head(5))


if __name__ == "__main__":
    main()
