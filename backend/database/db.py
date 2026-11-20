import os
import sqlite3
import json
from contextlib import contextmanager
from typing import Generator, Any, Dict, List, Optional

DATABASE_URL = os.getenv("DATABASE_URL")

# Check if using PostgreSQL / Supabase
IS_POSTGRES = bool(DATABASE_URL and (DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://")))

if IS_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    # Handle Supabase pooler / postgres:// vs postgresql:// prefix
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if os.environ.get("VERCEL") or not os.access(os.path.dirname(os.path.dirname(__file__)), os.W_OK):
    DB_DIR = "/tmp/auriic_data"
else:
    DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

DB_PATH = os.path.join(DB_DIR, "ats_auriic.db")
MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")

def init_db():
    """Ensure data directory and database schema are initialized."""
    if IS_POSTGRES:
        with get_connection() as conn:
            cursor = conn.cursor()
            schema_file = os.path.join(MIGRATIONS_DIR, "001_supabase_schema.sql")
            with open(schema_file, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            cursor.execute(schema_sql)
            conn.commit()
    else:
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
def get_connection():
    """Provide a transactional database connection for either PostgreSQL or SQLite."""
    if IS_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
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

def _adapt_sql(sql: str) -> str:
    """Adapt SQL placeholders and types between SQLite and PostgreSQL."""
    if IS_POSTGRES:
        return sql.replace("?", "%s")
    return sql

def query_one(sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    sql = _adapt_sql(sql)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None

def query_all(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    sql = _adapt_sql(sql)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def execute(sql: str, params: tuple = ()) -> int:
    """Execute SQL and return last inserted ID or affected row count."""
    is_insert = sql.strip().upper().startswith("INSERT")
    sql = _adapt_sql(sql)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        if IS_POSTGRES:
            if is_insert and "RETURNING" not in sql.upper():
                sql = sql.rstrip("; ") + " RETURNING id;"
                cursor.execute(sql, params)
                res = cursor.fetchone()
                return res["id"] if res else 0
            else:
                cursor.execute(sql, params)
                return cursor.rowcount
        else:
            cursor.execute(sql, params)
            return cursor.lastrowid
