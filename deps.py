# -*- coding: utf-8 -*-
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from services.auth_service import get_user_by_id
from config import BASE_DIR
import os

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


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
