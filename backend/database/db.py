import os
import sqlite3
import json
from contextlib import contextmanager
from typing import Generator, Any, Dict, List, Optional

def get_db_info():
    """Retrieve database URL and postgres boolean dynamically."""
    db_url = os.getenv("DATABASE_URL")
    is_postgres = bool(db_url and (db_url.startswith("postgresql://") or db_url.startswith("postgres://")))
    if is_postgres and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return db_url, is_postgres

DATABASE_URL, IS_POSTGRES = get_db_info()

if os.environ.get("VERCEL") or not os.access(os.path.dirname(os.path.dirname(__file__)), os.W_OK):
    DB_DIR = "/tmp/auriic_data"
else:
    DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

DB_PATH = os.path.join(DB_DIR, "ats_auriic.db")

_initialized = False

def _find_migration_file(filename: str) -> Optional[str]:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "migrations", filename),
        os.path.join(os.path.dirname(base_dir), "database", "migrations", filename),
        os.path.join(os.path.dirname(os.path.dirname(base_dir)), "backend", "database", "migrations", filename),
        f"/var/task/backend/database/migrations/{filename}",
        f"backend/database/migrations/{filename}",
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.isfile(c):
            return c
    return None

def _create_raw_connection():
    db_url, is_postgres = get_db_info()
    if is_postgres:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        return psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    else:
        os.makedirs(DB_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    """Ensure data directory and database schema are initialized."""
    global _initialized
    if _initialized:
        return

    db_url, is_postgres = get_db_info()
    if is_postgres:
        try:
            conn = _create_raw_connection()
            try:
                cursor = conn.cursor()
                schema_file = _find_migration_file("001_supabase_schema.sql")
                if schema_file:
                    with open(schema_file, "r", encoding="utf-8") as f:
                        schema_sql = f.read()
                    cursor.execute(schema_sql)
                    conn.commit()
            finally:
                conn.close()
        except Exception as e:
            print(f"Supabase PostgreSQL init notice (safe to continue): {e}")
    else:
        os.makedirs(DB_DIR, exist_ok=True)
        conn = _create_raw_connection()
        try:
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
            except Exception:
                pass
            conn.execute("PRAGMA foreign_keys=ON;")
            schema_file = _find_migration_file("001_initial_schema.sql")
            if schema_file:
                with open(schema_file, "r", encoding="utf-8") as f:
                    schema_sql = f.read()
                conn.executescript(schema_sql)
                conn.commit()
        except Exception as e:
            print(f"SQLite init notice: {e}")
        finally:
            conn.close()

    _initialized = True

@contextmanager
def get_connection():
    """Provide a transactional database connection for either PostgreSQL or SQLite."""
    global _initialized
    if not _initialized:
        try:
            init_db()
        except Exception as e:
            print(f"Lazy init_db error: {e}")

    conn = _create_raw_connection()
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
    _, is_postgres = get_db_info()
    if is_postgres:
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

    _, is_postgres = get_db_info()
    with get_connection() as conn:
        cursor = conn.cursor()
        if is_postgres:
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
