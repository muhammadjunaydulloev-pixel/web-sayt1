# -*- coding: utf-8 -*-
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from services.auth_service import get_user_by_id
from services import chat_service
from config import BASE_DIR
import os

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


def _current_user_from_session(request: Request):
    user_id = request.session.get("user_id")
    return get_user_by_id(user_id) if user_id else None


def nav_chat_unread(request: Request) -> int:
    """Unread admin replies for the logged-in (non-admin) user — for the nav badge."""
    user = _current_user_from_session(request)
    if not user or user["is_admin"]:
        return 0
    return chat_service.get_unread_count_for_user(user["id"])


def nav_admin_chat_unread(request: Request) -> int:
    """Unread user messages across all conversations — for the admin nav badge."""
    user = _current_user_from_session(request)
    if not user or not user["is_admin"]:
        return 0
    return chat_service.total_unread_for_admin()


templates.env.globals["nav_chat_unread"] = nav_chat_unread
templates.env.globals["nav_admin_chat_unread"] = nav_admin_chat_unread
templates.env.globals["nav_user"] = _current_user_from_session


def get_current_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return get_user_by_id(user_id)


class RedirectException(Exception):
    def __init__(self, url: str):
        self.url = url


def require_login(request: Request):
    user = get_current_user(request)
    if user is None:
        raise RedirectException("/login")
    return user


def require_admin(request: Request):
    user = require_login(request)
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Танҳо барои админ")
    return user
