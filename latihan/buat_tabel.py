import sqlite3
import os

print("Working directory:", os.getcwd())

conn = sqlite3.connect("latihan.db")
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS mahasiswa (
        id    INTEGER PRIMARY KEY AUTOINCREMENT,
        nama  TEXT NOT NULL,
        nim   TEXT NOT NULL UNIQUE,
        prodi TEXT NOT NULL
    )
""")

conn.commit()

print("Database location:", os.path.abspath("latihan.db"))

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:", cursor.fetchall())

conn.close()