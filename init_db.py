import sqlite3
import os

DB_PATH = os.environ.get("DATABASE_PATH", "/tmp/trading.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # USERS TABLE
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # PORTFOLIO TABLE
    c.execute("""
        CREATE TABLE IF NOT EXISTS portfolios (
            user_id INTEGER PRIMARY KEY,
            cash REAL NOT NULL DEFAULT 100000,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # HOLDINGS TABLE
    c.execute("""
        CREATE TABLE IF NOT EXISTS holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            shares INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()
