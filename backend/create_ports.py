import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / 'database' / 'containers.db'

SAMPLE_PORTS = [
    ("Aktau", "Kazakistan", 43.65, 51.20),
    ("Durrës", "Arnavutluk", 41.31, 19.45),
    ("Cartagena", "Kolombiya", 10.39, -75.51),
    ("Göteborg", "İsveç", 57.71, 11.97),
    ("Lizbon", "Portekiz", 38.72, -9.14),
    ("Kocaeli", "Türkiye", 40.85, 29.88),
    ("Callao", "Peru", -12.05, -77.13),
]


def create_ports_table(conn):
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS ports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            country TEXT NOT NULL,
            lat REAL,
            lng REAL
        )
    ''')
    conn.commit()


def seed_ports(conn):
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM ports')
    if cur.fetchone()[0] > 0:
        print('Ports table already has data, skipping seeding.')
        return
    cur.executemany('INSERT INTO ports (name, country, lat, lng) VALUES (?, ?, ?, ?)', SAMPLE_PORTS)
    conn.commit()
    print('Seeded ports table with sample data.')


def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    create_ports_table(conn)
    seed_ports(conn)
    conn.close()

if __name__ == '__main__':
    main()
