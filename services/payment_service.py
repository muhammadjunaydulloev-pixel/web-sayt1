# -*- coding: utf-8 -*-
from datetime import datetime, timezone

from database.db import execute, query_one, query_all


def _now():
    return datetime.now(timezone.utc).isoformat()


def is_paid(user_id: int) -> bool:
    row = query_one("SELECT paid FROM users WHERE id = ?", (user_id,))
    return bool(row and row["paid"])


def has_pending_payment(user_id: int) -> bool:
    row = query_one(
        "SELECT id FROM payments WHERE user_id = ? AND status = 'pending'", (user_id,)
    )
    return row is not None


def get_latest_payment(user_id: int):
    return query_one(
        "SELECT * FROM payments WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)
    )


def create_payment_request(user_id: int, file_path: str) -> int:
    cur = execute(
        "INSERT INTO payments (user_id, file_path, status, created_at) VALUES (?, ?, 'pending', ?)",
        (user_id, file_path, _now()),
    )
    return cur.lastrowid


def list_payments_for_user(user_id: int):
    return query_all(
        "SELECT * FROM payments WHERE user_id = ? ORDER BY id DESC", (user_id,)
    )


def get_payment(payment_id: int):
    return query_one("SELECT * FROM payments WHERE id = ?", (payment_id,))


def list_pending_payments():
    return query_all(
        """
        SELECT payments.*, users.full_name, users.phone
        FROM payments JOIN users ON users.id = payments.user_id
        WHERE payments.status = 'pending'
        ORDER BY payments.id ASC
        """
    )


def approve_payment(payment_id: int, user_id: int):
    execute(
        "UPDATE payments SET status = 'approved', resolved_at = ? WHERE id = ?",
        (_now(), payment_id),
    )
    execute("UPDATE users SET paid = 1 WHERE id = ?", (user_id,))


def reject_payment(payment_id: int, note: str = ""):
    execute(
        "UPDATE payments SET status = 'rejected', resolved_at = ?, note = ? WHERE id = ?",
        (_now(), note, payment_id),
    )
