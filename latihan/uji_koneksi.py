import sqlite3 

conn = sqlite3.connect("latihan.db")
print("Database siap digunakan")
conn.close()