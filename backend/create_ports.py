import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / 'database' / 'containers.db'

# Corex'in gerçek limanı olan 55 ülke — hepsi has_port=1.
# Şehir/koordinat sadece bilinen 7 liman için dolu; diğerlerinde henüz
# kesin liman şehri/koordinatı olmadığı için boş bırakıldı.
# (ülke, liman var mı (1/0), liman şehri, lat, lng)
COUNTRIES = [
    ("Kanada", 1, None, None, None),
    ("Amerika Birleşik Devletleri", 1, None, None, None),
    ("Meksika", 1, None, None, None),
    ("Guatemala", 1, None, None, None),
    ("El Salvador", 1, None, None, None),
    ("Honduras", 1, None, None, None),
    ("Kosta Rika", 1, None, None, None),
    ("Panama", 1, None, None, None),
    ("Kolombiya", 1, "Cartagena", 10.39, -75.51),
    ("Ekvador", 1, None, None, None),
    ("Peru", 1, "Callao", -12.05, -77.13),
    ("Brezilya", 1, None, None, None),
    ("Şili", 1, None, None, None),
    ("Arjantin", 1, None, None, None),
    ("Uruguay", 1, None, None, None),
    ("Norveç", 1, None, None, None),
    ("Finlandiya", 1, None, None, None),
    ("İsveç", 1, "Göteborg", 57.71, 11.97),
    ("Litvanya", 1, None, None, None),
    ("Hollanda", 1, None, None, None),
    ("Belçika", 1, None, None, None),
    ("Danimarka", 1, None, None, None),
    ("İngiltere", 1, None, None, None),
    ("İrlanda", 1, None, None, None),
    ("Fransa", 1, None, None, None),
    ("İsviçre", 1, None, None, None),
    ("İspanya", 1, None, None, None),
    ("Portekiz", 1, "Lizbon", 38.72, -9.14),
    ("Kosova", 1, None, None, None),
    ("Kuzey Makedonya", 1, None, None, None),
    ("Sırbistan", 1, None, None, None),
    ("İtalya", 1, None, None, None),
    ("Malta", 1, None, None, None),
    ("Yunanistan", 1, None, None, None),
    ("Arnavutluk", 1, "Durrës", 41.31, 19.45),
    ("Fas", 1, None, None, None),
    ("Gana", 1, None, None, None),
    ("Fildişi Sahili", 1, None, None, None),
    ("Zambiya", 1, None, None, None),
    ("Angola", 1, None, None, None),
    ("Namibya", 1, None, None, None),
    ("Mozambik", 1, None, None, None),
    ("Zimbabve", 1, None, None, None),
    ("Malavi", 1, None, None, None),
    ("Tanzanya", 1, None, None, None),
    ("Kazakistan", 1, "Aktau", 43.65, 51.20),
    ("Özbekistan", 1, None, None, None),
    ("Türkiye", 1, "Kocaeli", 40.85, 29.88),
    ("Çin", 1, None, None, None),
    ("Bangladeş", 1, None, None, None),
    ("Hindistan", 1, None, None, None),
    ("Vietnam", 1, None, None, None),
    ("Tayland", 1, None, None, None),
    ("Singapur", 1, None, None, None),
    ("Endonezya", 1, None, None, None),
]


def create_ports_table(conn):
    cur = conn.cursor()
    cur.execute('DROP TABLE IF EXISTS ports')
    cur.execute('''
        CREATE TABLE ports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country TEXT NOT NULL UNIQUE,
            has_port INTEGER NOT NULL DEFAULT 0,
            name TEXT,
            lat REAL,
            lng REAL
        )
    ''')
    conn.commit()


def seed_ports(conn):
    cur = conn.cursor()
    cur.executemany(
        'INSERT INTO ports (country, has_port, name, lat, lng) VALUES (?, ?, ?, ?, ?)',
        COUNTRIES,
    )
    conn.commit()
    print(f'Seeded ports table with {len(COUNTRIES)} countries.')


def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    create_ports_table(conn)
    seed_ports(conn)
    conn.close()


if __name__ == '__main__':
    main()
