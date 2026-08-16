# -*- coding: utf-8 -*-
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, JSONResponse

from deps import templates, require_login
from services import game_service
from services.game_service import GameError

router = APIRouter()


@router.get("/game")
def game_hub(request: Request):
    user = require_login(request)
    incoming = game_service.list_incoming_invites(user["id"])
    outgoing = game_service.list_outgoing_invites(user["id"])
    active_room = game_service.get_active_room_for_user(user["id"])
    return templates.TemplateResponse("game_hub.html", {
        "request": request, "user": user,
        "incoming": incoming, "outgoing": outgoing,
        "active_room": active_room, "error": None,
    })


def _hub_error(request, user, message):
    incoming = game_service.list_incoming_invites(user["id"])
    outgoing = game_service.list_outgoing_invites(user["id"])
    active_room = game_service.get_active_room_for_user(user["id"])
    return templates.TemplateResponse("game_hub.html", {
        "request": request, "user": user,
        "incoming": incoming, "outgoing": outgoing,
        "active_room": active_room, "error": message,
    }, status_code=400)


@router.post("/game/invite")
def send_invite(request: Request, code: str = Form(...)):
    user = require_login(request)
    try:
        room = game_service.create_invite(user, code)
    except GameError as e:
        return _hub_error(request, user, str(e))
    return RedirectResponse(f"/game/room/{room['code']}", status_code=303)


@router.post("/game/invite/{invite_id}/accept")
def accept_invite(request: Request, invite_id: int):
    user = require_login(request)
    try:
        room = game_service.respond_invite(invite_id, user["id"], accept=True)
    except GameError as e:
        return _hub_error(request, user, str(e))
    return RedirectResponse(f"/game/room/{room['code']}", status_code=303)


@router.post("/game/invite/{invite_id}/decline")
def decline_invite(request: Request, invite_id: int):
    user = require_login(request)
    try:
        game_service.respond_invite(invite_id, user["id"], accept=False)
    except GameError:
        pass
    return RedirectResponse("/game", status_code=303)


@router.post("/game/invite/{invite_id}/cancel")
def cancel_invite(request: Request, invite_id: int):
    user = require_login(request)
    game_service.cancel_invite(invite_id, user["id"])
    return RedirectResponse("/game", status_code=303)


@router.post("/game/join")
def join_by_code(request: Request, code: str = Form(...)):
    user = require_login(request)
    try:
        room = game_service.join_room(user["id"], code)
    except GameError as e:
        return _hub_error(request, user, str(e))
    return RedirectResponse(f"/game/room/{room['code']}", status_code=303)


@router.get("/game/room/{code}")
def room_page(request: Request, code: str):
    user = require_login(request)
    room = game_service.get_room_by_code(code)
    if not room:
        return RedirectResponse("/game", status_code=303)
    member = game_service.is_member(room["id"], user["id"])
    can_join = (not member and room["status"] == "lobby"
                and len(game_service.get_active_players(room["id"])) < room["max_players"])
    return templates.TemplateResponse("game_room.html", {
        "request": request, "user": user, "room_code": room["code"],
        "is_member": member, "can_join": can_join,
    })


@router.post("/game/room/{code}/join")
def room_join(request: Request, code: str):
    user = require_login(request)
    try:
        game_service.join_room(user["id"], code)
    except GameError:
        pass
    return RedirectResponse(f"/game/room/{code}", status_code=303)


@router.post("/game/room/{code}/leave")
def room_leave(request: Request, code: str):
    user = require_login(request)
    room = game_service.get_room_by_code(code)
    if room:
        game_service.leave_room(user["id"], room["id"])
    return RedirectResponse("/game", status_code=303)


@router.post("/game/room/{code}/start")
def room_start(request: Request, code: str):
    user = require_login(request)
    room = game_service.get_room_by_code(code)
    if room:
        try:
            game_service.start_game(room["id"], user["id"])
        except GameError:
            pass
    return RedirectResponse(f"/game/room/{code}", status_code=303)


# ---------- JSON polling API ----------

@router.get("/api/game/room/{code}/state")
def api_room_state(request: Request, code: str):
    user = require_login(request)
    try:
        state = game_service.get_room_state(code, user["id"])
    except GameError as e:
        return JSONResponse({"error": str(e)}, status_code=404)
    return JSONResponse(state)


@router.post("/api/game/room/{code}/answer")
def api_room_answer(request: Request, code: str, choice_id: int = Form(...)):
    user = require_login(request)
    room = game_service.get_room_by_code(code)
    if not room:
        return JSONResponse({"error": "not_found"}, status_code=404)
    try:
        state = game_service.submit_answer(room["id"], user["id"], choice_id)
    except GameError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    return JSONResponse(state)
