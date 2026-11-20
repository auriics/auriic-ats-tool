import os
import sqlite3
import json
from contextlib import contextmanager
from typing import Generator, Any, Dict, List, Optional

if os.environ.get("VERCEL") or not os.access(os.path.dirname(os.path.dirname(__file__)), os.W_OK):
    DB_DIR = "/tmp/auriic_data"
else:
    DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

DB_PATH = os.path.join(DB_DIR, "ats_auriic.db")
MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")

def init_db():
    """Ensure data directory and database schema are initialized."""
    os.makedirs(DB_DIR, exist_ok=True)
    with get_connection() as conn:
        try:
            # Enable WAL mode for high concurrency
            conn.execute("PRAGMA journal_mode=WAL;")
        except Exception:
            pass
        conn.execute("PRAGMA foreign_keys=ON;")
        migration_file = os.path.join(MIGRATIONS_DIR, "001_initial_schema.sql")
        with open(migration_file, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)

@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Provide a transactional database connection."""
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def query_one(sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None

def query_all(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def execute(sql: str, params: tuple = ()) -> int:
    """Execute SQL and return the last row ID or affected row count."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.lastrowid
