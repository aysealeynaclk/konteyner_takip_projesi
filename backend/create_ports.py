import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / 'database' / 'containers.db'

# Corex'in gerçek limanı olan sadece 12 ülke — has_port=1.
# Bu listede olmayan hiçbir ülke ports tablosunda yer almaz; harita bu yüzden
# o ülkelere tıklandığında otomatik olarak "liman bulunmuyor" gösterir.
# Bazı ülkelerin birden fazla liman/terminali olduğu için o ülkeler birden
# fazla satırla (her liman için bir satır) temsil ediliyor.
# (ülke, liman var mı (1/0), liman/terminal adı, lat, lng)
COUNTRIES = [
    ("Türkiye", 1, "Gebze", 40.80, 29.43),
    ("Türkiye", 1, "Körfez", 40.77, 29.75),
    ("Türkiye", 1, "Ankara", 39.93, 32.86),
    ("Norveç", 1, "Oslo", 59.91, 10.75),
    ("İsveç", 1, "Gävle", 60.67, 17.14),
    ("İsveç", 1, "Stockholm Nord", 58.93, 17.90),
    ("Portekiz", 1, "Liscont", None, None),
    ("Portekiz", 1, "Elvas", None, None),
    ("Portekiz", 1, "Tersado", None, None),
    ("Portekiz", 1, "Setúbal", 38.52, -8.89),
    ("Portekiz", 1, "Aveiro", 40.64, -8.65),
    ("Portekiz", 1, "Leixões", 41.18, -8.70),
    ("Portekiz", 1, "Sotagus", None, None),
    ("Portekiz", 1, "Figueira Da Foz", 40.15, -8.86),
    ("İspanya", 1, "Huelva", 37.26, -6.95),
    ("İspanya", 1, "Ferrol", 43.49, -8.24),
    ("Ekvador", 1, "Puerto Bolívar", -3.26, -79.95),
    ("Peru", 1, "Paita", -5.09, -81.11),
    ("Guatemala", 1, "YILPORT Quetzal", 13.92, -90.79),
    ("El Salvador", 1, "Acajutla", 13.59, -89.83),
    ("El Salvador", 1, "La Unión", 13.34, -87.84),
    ("Malta", 1, "Marsaxlokk", 35.84, 14.54),
    ("İtalya", 1, "Taranto", 40.47, 17.24),
    ("Gana", 1, "Takoradi", 4.90, -1.76),
]


def create_ports_table(conn):
    cur = conn.cursor()
    cur.execute('DROP TABLE IF EXISTS ports')
    cur.execute('''
        CREATE TABLE ports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country TEXT NOT NULL,
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
    print(f'Seeded ports table with {len(COUNTRIES)} rows.')


def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    create_ports_table(conn)
    seed_ports(conn)
    conn.close()


if __name__ == '__main__':
    main()
