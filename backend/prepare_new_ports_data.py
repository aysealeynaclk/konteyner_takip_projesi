"""
COREX_Marsaxlokk_Data.csv, COREX_Takoradi_Data.csv, COREX_Taranto_Data.csv,
COREX_Oslo_Data.xlsx, COREX_Gavle_Data.xlsx, COREX_Stockholm_Nord_Data.xlsx —
hepsi Ankara verisiyle aynı formatta (ayrı DateEnteredYard sütunu,
TimeExitedYard'da sadece saat var). Bu script her dosya için tarih+saat
birleştirmesini yapıp (gece yarısı sarkması dahil) import_excel.py'nin
okuyabileceği bir Excel dosyasına yazar. Kaynak CSV veya Excel olabilir.
"""

import pandas as pd
import datetime as dt
from pathlib import Path

DATASETS_DIR = Path(__file__).resolve().parent / "datasets"

FILES = [
    ("COREX_Marsaxlokk_Data.csv", "marsaxlokk_prepared.xlsx"),
    ("COREX_Takoradi_Data.csv", "takoradi_prepared.xlsx"),
    ("COREX_Taranto_Data.csv", "taranto_prepared.xlsx"),
    ("COREX_Oslo_Data.xlsx", "oslo_prepared.xlsx"),
    ("COREX_Gavle_Data.xlsx", "gavle_prepared.xlsx"),
    ("COREX_Stockholm_Nord_Data.xlsx", "stockholm_nord_prepared.xlsx"),
    ("COREX_Acajutla_Data.xlsx", "acajutla_prepared.xlsx"),
    ("COREX_La_Union_Data.xlsx", "la_union_prepared.xlsx"),
    ("COREX_Paita_Peru_Data.xlsx", "paita_prepared.xlsx"),
    ("COREX_Puerto_Bolivar_Ecuador_Data.xlsx", "puerto_bolivar_prepared.xlsx"),
    ("COREX_Puerto_Quetzal_Data.xlsx", "puerto_quetzal_prepared.xlsx"),
    ("COREX_Liscont_Portugal_Data.xlsx", "liscont_prepared.xlsx"),
    ("COREX_Figueira_Da_Foz_Portugal_Data.xlsx", "figueira_da_foz_prepared.xlsx"),
    ("COREX_Sotagus_Portugal_Data.xlsx", "sotagus_prepared.xlsx"),
    ("COREX_Leixoes_Portugal_Data.xlsx", "leixoes_prepared.xlsx"),
    ("COREX_Aveiro_Portugal_Data.xlsx", "aveiro_prepared.xlsx"),
    ("COREX_Setubal_Portugal_Data.xlsx", "setubal_prepared.xlsx"),
    ("COREX_Tersado_Portugal_Data.xlsx", "tersado_prepared.xlsx"),
    ("COREX_Huelva_Spain_Data.xlsx", "huelva_prepared.xlsx"),
    ("COREX_Ferrol_Spain_Data.xlsx", "ferrol_prepared.xlsx"),
    ("COREX_Elvas_Portugal_Data.xlsx", "elvas_prepared.xlsx"),
]


def parse_time(s):
    if pd.isna(s) or str(s).strip() == "":
        return None
    return dt.datetime.strptime(str(s).strip(), "%H:%M:%S").time()


def parse_date(s):
    s = str(s).strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Bilinmeyen tarih formatı: {s}")


def prepare_one(src_name, out_name):
    src_path = DATASETS_DIR / src_name
    out_path = DATASETS_DIR / out_name

    df = pd.read_csv(src_path) if src_path.suffix.lower() == ".csv" else pd.read_excel(src_path)
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

    mismatches = 0
    for _, row in df.iterrows():
        if row["TimeExitedYard"] is not None and not pd.isna(row.get("TruckVisitMinutesInYard")):
            computed = (row["TimeExitedYard"] - row["TimeEnteredYard"]).total_seconds() / 60
            if abs(computed - row["TruckVisitMinutesInYard"]) > 1:
                mismatches += 1
    print(f"[{src_name}] Süre uyuşmazlığı: {mismatches} / {len(df)}")

    df["Damage"] = df["Damage"].fillna(0).astype(int)

    df.to_excel(out_path, index=False)
    print(f"✅ {out_path} yazıldı ({len(df)} satır)")


def main():
    for src_name, out_name in FILES:
        prepare_one(src_name, out_name)


if __name__ == "__main__":
    main()
