import sqlite3

DB_NAME = "voicegen.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            is_premium INTEGER DEFAULT 0,
            daily_usage INTEGER DEFAULT 0,
            monthly_usage INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()