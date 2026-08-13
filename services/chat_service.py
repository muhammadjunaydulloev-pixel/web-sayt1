# -*- coding: utf-8 -*-
"""Two chat surfaces:
  - group chat: one shared room every logged-in user (and the admin) can post to.
  - admin chat: a private 1:1 support thread between a single user and the admin.
Both are simple poll-based (no websockets) so they work reliably on any host.
"""
from datetime import datetime, timezone

from database.db import execute, query_one, query_all

MAX_MESSAGE_LEN = 2000


def _now():
    return datetime.now(timezone.utc).isoformat()


def _clean(message: str) -> str:
    return (message or "").strip()[:MAX_MESSAGE_LEN]


# ---------- Group chat ----------

def send_group_message(user_id: int, message: str):
    message = _clean(message)
    if not message:
        return None
    cur = execute(
        "INSERT INTO group_messages (user_id, message, created_at) VALUES (?, ?, ?)",
        (user_id, message, _now()),
    )
    return cur.lastrowid


def get_group_messages(after_id: int = 0, limit: int = 200):
    return query_all(
        """
        SELECT group_messages.*, users.full_name, users.avatar, users.is_admin
        FROM group_messages JOIN users ON users.id = group_messages.user_id
        WHERE group_messages.id > ?
        ORDER BY group_messages.id ASC
        LIMIT ?
        """,
        (after_id, limit),
    )


# ---------- Admin (private) chat ----------

def send_admin_message(user_id: int, sender: str, message: str):
    message = _clean(message)
    if not message:
        return None
    cur = execute(
        "INSERT INTO admin_messages (user_id, sender, message, is_read, created_at) "
        "VALUES (?, ?, ?, 0, ?)",
        (user_id, sender, message, _now()),
    )
    return cur.lastrowid


def get_admin_messages(user_id: int, after_id: int = 0, limit: int = 500):
    return query_all(
        "SELECT * FROM admin_messages WHERE user_id = ? AND id > ? ORDER BY id ASC LIMIT ?",
        (user_id, after_id, limit),
    )


def mark_read(user_id: int, reader: str):
    """reader='admin' clears the badge on messages the user sent;
    reader='user' clears the badge on messages the admin sent."""
    other_sender = "user" if reader == "admin" else "admin"
    execute(
        "UPDATE admin_messages SET is_read = 1 WHERE user_id = ? AND sender = ? AND is_read = 0",
        (user_id, other_sender),
    )


def get_unread_count_for_user(user_id: int) -> int:
    row = query_one(
        "SELECT COUNT(*) AS c FROM admin_messages WHERE user_id = ? AND sender = 'admin' AND is_read = 0",
        (user_id,),
    )
    return row["c"] if row else 0


def list_conversations():
    """One row per user who has any admin-chat history, newest activity first,
    with the unread-from-user count for the admin's inbox badge."""
    return query_all(
        """
        SELECT
          users.id AS user_id, users.full_name, users.phone, users.avatar,
          (SELECT message FROM admin_messages am2
             WHERE am2.user_id = users.id ORDER BY am2.id DESC LIMIT 1) AS last_message,
          (SELECT created_at FROM admin_messages am3
             WHERE am3.user_id = users.id ORDER BY am3.id DESC LIMIT 1) AS last_at,
          (SELECT COUNT(*) FROM admin_messages am4
             WHERE am4.user_id = users.id AND am4.sender = 'user' AND am4.is_read = 0) AS unread
        FROM users
        WHERE users.is_admin = 0
          AND EXISTS (SELECT 1 FROM admin_messages am WHERE am.user_id = users.id)
        ORDER BY last_at DESC
        """
    )


def total_unread_for_admin() -> int:
    row = query_one(
        "SELECT COUNT(*) AS c FROM admin_messages WHERE sender = 'user' AND is_read = 0"
    )
    return row["c"] if row else 0
