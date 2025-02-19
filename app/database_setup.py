import sqlite3

USERS_DB = "users.db"
WIKI_DB = "wiki.db"

def init_user_db():
    """
    Creates the 'users' table in users.db if it does not exist.
    """
    with sqlite3.connect(USERS_DB) as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()

def init_wiki_db():
    """
    Creates the 'wiki' table in wiki.db if it does not exist,
    and adds a 'last_edited_by' column if missing.
    """
    with sqlite3.connect(WIKI_DB) as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS wiki (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                folder TEXT DEFAULT '',
                updated_at TEXT NOT NULL
            )
        """)
        # Attempt to add 'last_edited_by' column if it doesn't exist.
        try:
            cur.execute("ALTER TABLE wiki ADD COLUMN last_edited_by TEXT")
        except:
            pass

        conn.commit()
