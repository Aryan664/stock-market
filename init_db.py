import sqlite3

conn = sqlite3.connect("database.db")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL,
    cash REAL NOT NULL
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS portfolio (
    username TEXT,
    symbol TEXT,
    shares INTEGER,
    PRIMARY KEY (username, symbol)
)
""")

conn.commit()
conn.close()

print("Database initialized.")
