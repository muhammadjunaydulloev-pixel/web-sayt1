# -*- coding: utf-8 -*-
import json
import random
import sqlite3
import threading

from config import DB_PATH, WORDS_JSON_PATH
from database.models import CREATE_TABLES_SQL

_local = threading.local()
_write_lock = threading.Lock()


def get_conn():
    """One connection per thread (FastAPI runs sync path-ops in a threadpool)."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _local.conn = conn
    return conn


def execute(sql, params=()):
    with _write_lock:
        conn = get_conn()
        cur = conn.execute(sql, params)
        conn.commit()
        return cur


def query_one(sql, params=()):
    conn = get_conn()
    cur = conn.execute(sql, params)
    return cur.fetchone()


def query_all(sql, params=()):
    conn = get_conn()
    cur = conn.execute(sql, params)
    return cur.fetchall()


def init_db():
    conn = get_conn()
    conn.executescript(CREATE_TABLES_SQL)
    conn.commit()
    _migrate()
    _seed_words()


def _migrate():
    """Add columns that didn't exist in earlier versions of the schema,
    so an existing app.db from before this update keeps working."""
    conn = get_conn()
    cols = [row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()]
    if "avatar" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN avatar TEXT")
        conn.commit()
    if "game_code" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN game_code TEXT")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_game_code ON users(game_code)")
        conn.commit()
    _backfill_game_codes()


def _backfill_game_codes():
    """Every user needs a unique 6-digit game ID for the Мусобиқа feature.
    Assigns one to any account created before this feature existed."""
    conn = get_conn()
    missing = conn.execute("SELECT id FROM users WHERE game_code IS NULL OR game_code = ''").fetchall()
    if not missing:
        return
    existing = {row["game_code"] for row in conn.execute(
        "SELECT game_code FROM users WHERE game_code IS NOT NULL"
    ).fetchall()}
    with _write_lock:
        for row in missing:
            code = _new_unique_code(existing)
            existing.add(code)
            conn.execute("UPDATE users SET game_code = ? WHERE id = ?", (code, row["id"]))
        conn.commit()


def _new_unique_code(existing: set) -> str:
    while True:
        code = str(random.randint(100000, 999999))
        if code not in existing:
            return code


def _seed_words():
    row = query_one("SELECT COUNT(*) AS c FROM words")
    if row and row["c"] > 0:
        return
    with open(WORDS_JSON_PATH, "r", encoding="utf-8") as f:
        words = json.load(f)
    conn = get_conn()
    with _write_lock:
        conn.executemany(
            "INSERT INTO words (id, lesson, lesson_title, ru, tj) VALUES (?, ?, ?, ?, ?)",
            [(w["id"], w["lesson"], w["lesson_title"], w["ru"], w["tj"]) for w in words],
        )
        conn.commit()
