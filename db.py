import sqlite3
from pathlib import Path

DB_PATH = Path("app.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        user_name TEXT NOT NULL,
        username TEXT,
        phone TEXT NOT NULL,
        service TEXT NOT NULL,
        desired_date TEXT,
        desired_time TEXT,
        comment TEXT NOT NULL,
        photo_path TEXT,
        status TEXT NOT NULL DEFAULT 'new',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER NOT NULL,
        sender_id INTEGER NOT NULL,
        sender_role TEXT NOT NULL,
        text TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(application_id) REFERENCES applications(id)
    )
    """)

    conn.commit()
    conn.close()