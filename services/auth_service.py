# -*- coding: utf-8 -*-
import hashlib
import hmac
import os
from datetime import datetime, timezone

from database.db import execute, query_one


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


def create_user(full_name: str, phone: str, password: str, is_admin: bool = False):
    execute(
        "INSERT INTO users (full_name, phone, password_hash, is_admin, paid, joined_at) "
        "VALUES (?, ?, ?, ?, 0, ?)",
        (full_name.strip(), phone.strip(), hash_password(password), 1 if is_admin else 0, _now()),
    )
    return get_user_by_phone(phone.strip())


def authenticate(phone: str, password: str):
    user = get_user_by_phone(phone.strip())
    if user is None:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user
