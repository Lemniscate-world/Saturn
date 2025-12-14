import sqlite3


def connect(db_path="saturn.db"):
    return sqlite3.connect(db_path)


def init_db(conn):
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS memory_items (
        id TEXT PRIMARY KEY,
        source TEXT NOT NULL,
        note_path TEXT NOT NULL,
        block_ref TEXT,

        interval REAL NOT NULL,
        ease REAL NOT NULL,
        confidence REAL NOT NULL,
        repetitions INTEGER NOT NULL,

        last_review DATE,
        next_review DATE NOT NULL,
        created_at DATE NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS review_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        memory_id TEXT NOT NULL,
        review_date DATE NOT NULL,
        feedback TEXT NOT NULL,

        interval_after REAL,
        ease_after REAL,
        confidence_after REAL,

        FOREIGN KEY (memory_id) REFERENCES memory_items(id)
    )
    """)

    conn.commit()
