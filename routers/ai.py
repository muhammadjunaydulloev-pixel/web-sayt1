# -*- coding: utf-8 -*-
"""JSON API used by the AI Assistant widget (see static/js/ai-assistant.js).
Keeps the API key server-side only — the frontend never talks to the AI
provider directly."""
from typing import List, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from deps import require_login
from services import ai_service

router = APIRouter(prefix="/api/ai")

MAX_MESSAGE_LEN = 2000


class ContextWord(BaseModel):
    ru: Optional[str] = None
    tj: Optional[str] = None


class HistoryTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    context_word: Optional[ContextWord] = None
    history: Optional[List[HistoryTurn]] = None


@router.post("/chat")
def ai_chat(request: Request, payload: ChatRequest):
    require_login(request)

    message = (payload.message or "").strip()[:MAX_MESSAGE_LEN]
    if not message:
        return JSONResponse({"error": "empty"}, status_code=400)

    context_word = payload.context_word.model_dump() if payload.context_word else None
    history = [h.model_dump() for h in payload.history] if payload.history else None

    reply, error = ai_service.get_ai_reply(message, context_word, history)
    if error:
        return JSONResponse({"error": error}, status_code=502)
    return JSONResponse({"reply": reply})
