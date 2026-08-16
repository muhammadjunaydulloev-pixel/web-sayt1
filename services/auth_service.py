# -*- coding: utf-8 -*-
import hashlib
import hmac
import os
import random
from datetime import datetime, timezone

from database.db import execute, query_one, query_all


def _now():
    return datetime.now(timezone.utc).isoformat()


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return salt.hex() + "$" + dk.hex()


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split("$")
    except ValueError:
        return False
    salt = bytes.fromhex(salt_hex)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return hmac.compare_digest(dk.hex(), dk_hex)


def get_user_by_phone(phone: str):
    return query_one("SELECT * FROM users WHERE phone = ?", (phone,))


def get_user_by_id(user_id: int):
    return query_one("SELECT * FROM users WHERE id = ?", (user_id,))


def _new_game_code() -> str:
    """A unique, memorable 6-digit ID every user gets for the Мусобиқа
    (competition) feature — friends invite each other by typing it in."""
    while True:
        code = str(random.randint(100000, 999999))
        if not query_one("SELECT id FROM users WHERE game_code = ?", (code,)):
            return code


def create_user(full_name: str, phone: str, password: str, is_admin: bool = False):
    execute(
        "INSERT INTO users (full_name, phone, password_hash, is_admin, paid, joined_at, game_code) "
        "VALUES (?, ?, ?, ?, 0, ?, ?)",
        (full_name.strip(), phone.strip(), hash_password(password), 1 if is_admin else 0, _now(),
         _new_game_code()),
    )
    return get_user_by_phone(phone.strip())


def get_user_by_game_code(code: str):
    return query_one("SELECT * FROM users WHERE game_code = ?", (code.strip(),))


def authenticate(phone: str, password: str):
    user = get_user_by_phone(phone.strip())
    if user is None:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


def list_all_users(search: str = ""):
    """All non-admin users, newest first. Optional search by name or phone."""
    search = (search or "").strip()
    if search:
        like = f"%{search}%"
        return query_all(
            "SELECT * FROM users WHERE is_admin = 0 AND (full_name LIKE ? OR phone LIKE ?) "
            "ORDER BY id DESC",
            (like, like),
        )
    return query_all("SELECT * FROM users WHERE is_admin = 0 ORDER BY id DESC")


def set_avatar(user_id: int, avatar: str):
    execute("UPDATE users SET avatar = ? WHERE id = ?", (avatar, user_id))
