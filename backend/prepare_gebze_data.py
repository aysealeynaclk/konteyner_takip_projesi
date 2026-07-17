"""
gebze_veri seti.csv'deki TimeEnteredYard/TimeExitedYard sütunlarında sadece
saat var, tarih yok. Bu script her satıra rastgele bir giriş tarihi atayıp
tam TIMESTAMP üretir; TruckVisitMinutesInYard ile tutarlı kalması için çıkış
saati, giriş saatinden küçükse (gece yarısını geçmiş demektir) çıkışa bir
gün ekler. Sonucu import_excel.py'nin okuyabileceği bir Excel dosyasına yazar.
"""

import pandas as pd
import numpy as np
import datetime as dt
from pathlib import Path

DATASETS_DIR = Path(__file__).resolve().parent / "datasets"
SRC_PATH = DATASETS_DIR / "gebze_veri seti.csv"
OUT_PATH = DATASETS_DIR / "gebze_prepared.xlsx"

RNG_SEED = 42
DATE_RANGE_START = dt.date(2026, 6, 1)
DATE_RANGE_END = dt.date(2026, 7, 16)  # bugün


def parse_time(s):
    if pd.isna(s) or str(s).strip() == "":
        return None
    return dt.datetime.strptime(str(s).strip(), "%H:%M:%S").time()


def main():
    df = pd.read_csv(SRC_PATH)
    # Excel'den kalan isimsiz/boş sütunları at
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

    rng = np.random.default_rng(RNG_SEED)
    span_days = (DATE_RANGE_END - DATE_RANGE_START).days
    random_offsets = rng.integers(0, span_days + 1, size=len(df))

    entered_ts = []
    exited_ts = []
    for i, row in df.iterrows():
        entry_date = DATE_RANGE_START + dt.timedelta(days=int(random_offsets[i]))
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

    # Doğrulama: COMPLETE kayıtlarda hesaplanan süre, verilen
    # TruckVisitMinutesInYard ile eşleşiyor mu kontrol et.
    mismatches = 0
    for i, row in df.iterrows():
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
