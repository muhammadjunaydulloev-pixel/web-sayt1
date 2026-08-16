# -*- coding: utf-8 -*-
"""Мусобиқа — live 2-4 player vocabulary duel.

Flow: a user enters a friend's 6-digit game_code -> we create (or reuse) a
'lobby' room and a pending invite. If accepted, the friend joins the room.
Anyone in the room can share its 6-digit room code so up to 4 people total
sit in the lobby. The host starts the match once 2-4 players are in; each
round shows one Russian word and 4 Tajik choices, everyone races to answer,
points reward correctness + speed, and after the last round we show a podium.

No websockets/background workers are used — the whole match is driven by a
lazy "tick" that runs whenever a client polls the room state or answers a
round, and simply checks whether enough time has passed / everyone has
answered to advance the phase. This matches the rest of the app's simple
polling style (see chat_service) and needs no extra infrastructure.
"""
import json
import random
from datetime import datetime, timedelta, timezone

from database.db import execute, query_one, query_all
from config import FREE_LESSON

ROUND_SECONDS = 12          # time to answer each round
REVEAL_SECONDS = 4          # pause showing the correct answer + points
STARTING_SECONDS = 3        # "3..2..1" countdown before round 1
TOTAL_ROUNDS = 10
MAX_PLAYERS = 4
MIN_PLAYERS = 2
CHOICES_COUNT = 4

BASE_POINTS = 100
MAX_SPEED_BONUS = 60


def _now():
    return datetime.now(timezone.utc)


def _now_iso():
    return _now().isoformat()


def _parse(ts: str):
    return datetime.fromisoformat(ts)


# ---------- room codes ----------

def _new_room_code() -> str:
    while True:
        code = str(random.randint(100000, 999999))
        if not query_one("SELECT id FROM game_rooms WHERE code = ?", (code,)):
            return code


# ---------- basic lookups ----------

def get_room(room_id: int):
    return query_one("SELECT * FROM game_rooms WHERE id = ?", (room_id,))


def get_room_by_code(code: str):
    return query_one("SELECT * FROM game_rooms WHERE code = ?", (code.strip(),))


def get_players(room_id: int):
    return query_all(
        """
        SELECT gp.*, u.full_name, u.avatar
        FROM game_players gp JOIN users u ON u.id = gp.user_id
        WHERE gp.room_id = ?
        ORDER BY gp.joined_at ASC
        """,
        (room_id,),
    )


def get_active_players(room_id: int):
    return [p for p in get_players(room_id) if p["left_at"] is None]


def get_player(room_id: int, user_id: int):
    return query_one(
        "SELECT * FROM game_players WHERE room_id = ? AND user_id = ?", (room_id, user_id)
    )


def is_member(room_id: int, user_id: int) -> bool:
    p = get_player(room_id, user_id)
    return bool(p and p["left_at"] is None)


def get_active_room_for_user(user_id: int):
    """The room this user is currently sitting in (lobby or live), if any."""
    return query_one(
        """
        SELECT gr.* FROM game_rooms gr
        JOIN game_players gp ON gp.room_id = gr.id
        WHERE gp.user_id = ? AND gp.left_at IS NULL AND gr.status IN ('lobby', 'playing')
        ORDER BY gr.id DESC LIMIT 1
        """,
        (user_id,),
    )


# ---------- invites ----------

def list_incoming_invites(user_id: int):
    rows = query_all(
        """
        SELECT gi.*, gr.code AS room_code, gr.status AS room_status,
               u.full_name AS from_name, u.avatar AS from_avatar
        FROM game_invites gi
        JOIN game_rooms gr ON gr.id = gi.room_id
        JOIN users u ON u.id = gi.from_user_id
        WHERE gi.to_user_id = ? AND gi.status = 'pending'
        ORDER BY gi.id DESC
        """,
        (user_id,),
    )
    # Hide invites to rooms that are already full or no longer accepting players.
    result = []
    for r in rows:
        active = len(get_active_players(r["room_id"])) if r["room_status"] == "lobby" else MAX_PLAYERS
        if r["room_status"] == "lobby" and active < MAX_PLAYERS:
            result.append(r)
        else:
            execute("UPDATE game_invites SET status = 'cancelled', responded_at = ? WHERE id = ?",
                    (_now_iso(), r["id"]))
    return result


def list_outgoing_invites(user_id: int):
    return query_all(
        """
        SELECT gi.*, gr.code AS room_code, u.full_name AS to_name, u.avatar AS to_avatar
        FROM game_invites gi
        JOIN game_rooms gr ON gr.id = gi.room_id
        JOIN users u ON u.id = gi.to_user_id
        WHERE gi.from_user_id = ? AND gi.status = 'pending'
        ORDER BY gi.id DESC
        """,
        (user_id,),
    )


def count_incoming_invites(user_id: int) -> int:
    return len(list_incoming_invites(user_id))


class GameError(Exception):
    pass


def create_invite(from_user, code: str):
    """A user types a friend's 6-digit game_code to invite them. Reuses the
    inviter's existing open lobby if they have one, otherwise starts a new
    room with the inviter as host."""
    code = (code or "").strip()
    if len(code) != 6 or not code.isdigit():
        raise GameError("Рамз бояд аз 6 рақам иборат бошад.")

    to_user = query_one("SELECT * FROM users WHERE game_code = ?", (code,))
    if not to_user:
        raise GameError("Бо ин айди корбар ёфт нашуд.")
    if to_user["id"] == from_user["id"]:
        raise GameError("Шумо наметавонед худатонро даъват кунед.")

    room = get_active_room_for_user(from_user["id"])
    if room and room["status"] != "lobby":
        raise GameError("Ҳуҷраи шумо аллакай бозиро сар кардааст.")
    if room and len(get_active_players(room["id"])) >= MAX_PLAYERS:
        raise GameError("Ҳуҷраи шумо пур аст (то 4 нафар).")

    if not room:
        room = _create_room(from_user["id"])

    if is_member(room["id"], to_user["id"]):
        raise GameError("Ин корбар аллакай дар ҳуҷраи шумост.")

    already = query_one(
        "SELECT id FROM game_invites WHERE room_id = ? AND to_user_id = ? AND status = 'pending'",
        (room["id"], to_user["id"]),
    )
    if not already:
        execute(
            "INSERT INTO game_invites (room_id, from_user_id, to_user_id, status, created_at) "
            "VALUES (?, ?, ?, 'pending', ?)",
            (room["id"], from_user["id"], to_user["id"], _now_iso()),
        )
    return get_room(room["id"])


def _create_room(host_id: int):
    code = _new_room_code()
    cur = execute(
        """
        INSERT INTO game_rooms (code, host_id, status, phase, max_players, total_rounds,
                                 round_seconds, used_word_ids, created_at)
        VALUES (?, ?, 'lobby', 'lobby', ?, ?, ?, '[]', ?)
        """,
        (code, host_id, MAX_PLAYERS, TOTAL_ROUNDS, ROUND_SECONDS, _now_iso()),
    )
    room_id = cur.lastrowid
    execute(
        "INSERT INTO game_players (room_id, user_id, joined_at) VALUES (?, ?, ?)",
        (room_id, host_id, _now_iso()),
    )
    return get_room(room_id)


def respond_invite(invite_id: int, user_id: int, accept: bool):
    invite = query_one("SELECT * FROM game_invites WHERE id = ?", (invite_id,))
    if not invite or invite["to_user_id"] != user_id or invite["status"] != "pending":
        raise GameError("Ин даъватнома дигар мавҷуд нест.")

    if not accept:
        execute("UPDATE game_invites SET status = 'declined', responded_at = ? WHERE id = ?",
                (_now_iso(), invite_id))
        return None

    room = get_room(invite["room_id"])
    if not room or room["status"] != "lobby":
        execute("UPDATE game_invites SET status = 'cancelled', responded_at = ? WHERE id = ?",
                (_now_iso(), invite_id))
        raise GameError("Ин бозӣ аллакай сар шудааст ё бекор шудааст.")
    if len(get_active_players(room["id"])) >= MAX_PLAYERS:
        execute("UPDATE game_invites SET status = 'cancelled', responded_at = ? WHERE id = ?",
                (_now_iso(), invite_id))
        raise GameError("Ҳуҷра пур аст (то 4 нафар).")

    join_room(user_id, room["code"])
    execute("UPDATE game_invites SET status = 'accepted', responded_at = ? WHERE id = ?",
            (_now_iso(), invite_id))
    return room


def cancel_invite(invite_id: int, user_id: int):
    invite = query_one("SELECT * FROM game_invites WHERE id = ?", (invite_id,))
    if invite and invite["from_user_id"] == user_id and invite["status"] == "pending":
        execute("UPDATE game_invites SET status = 'cancelled', responded_at = ? WHERE id = ?",
                (_now_iso(), invite_id))


# ---------- join / leave ----------

def join_room(user_id: int, code: str):
    room = get_room_by_code(code)
    if not room:
        raise GameError("Бо ин рамз ҳуҷра ёфт нашуд.")
    if is_member(room["id"], user_id):
        return room
    if room["status"] != "lobby":
        raise GameError("Ин бозӣ аллакай сар шудааст.")
    if len(get_active_players(room["id"])) >= room["max_players"]:
        raise GameError("Ҳуҷра пур аст (то 4 нафар).")

    existing = get_player(room["id"], user_id)
    if existing and existing["left_at"] is not None:
        execute("UPDATE game_players SET left_at = NULL, joined_at = ? WHERE room_id = ? AND user_id = ?",
                (_now_iso(), room["id"], user_id))
    else:
        execute(
            "INSERT INTO game_players (room_id, user_id, joined_at) VALUES (?, ?, ?)",
            (room["id"], user_id, _now_iso()),
        )
    return room


def leave_room(user_id: int, room_id: int):
    room = get_room(room_id)
    if not room or not is_member(room_id, user_id):
        return
    if room["status"] == "lobby":
        execute("DELETE FROM game_players WHERE room_id = ? AND user_id = ?", (room_id, user_id))
        remaining = get_active_players(room_id)
        if not remaining:
            execute("DELETE FROM game_rooms WHERE id = ?", (room_id,))
            execute("UPDATE game_invites SET status = 'cancelled', responded_at = ? "
                    "WHERE room_id = ? AND status = 'pending'", (_now_iso(), room_id))
        elif room["host_id"] == user_id:
            new_host = min(remaining, key=lambda p: p["joined_at"])
            execute("UPDATE game_rooms SET host_id = ? WHERE id = ?", (new_host["user_id"], room_id))
    else:
        execute("UPDATE game_players SET left_at = ? WHERE room_id = ? AND user_id = ?",
                (_now_iso(), room_id, user_id))
        if room["status"] == "playing" and not get_active_players(room_id):
            execute("UPDATE game_rooms SET status = 'finished', phase = 'finished', finished_at = ? "
                    "WHERE id = ?", (_now_iso(), room_id))


# ---------- word pool ----------

def _word_pool_for_room(room_id: int):
    """Only use words every player currently has access to, so the game
    never leaks paid-lesson vocabulary to someone who hasn't unlocked it."""
    players = get_active_players(room_id)
    all_paid = bool(players) and all(
        query_one("SELECT paid FROM users WHERE id = ?", (p["user_id"],))["paid"] for p in players
    )
    if all_paid:
        return query_all("SELECT id, ru, tj FROM words")
    return query_all("SELECT id, ru, tj FROM words WHERE lesson = ?", (FREE_LESSON,))


def _get_word(word_id: int):
    return query_one("SELECT * FROM words WHERE id = ?", (word_id,))


# ---------- game lifecycle ----------

def start_game(room_id: int, user_id: int):
    room = get_room(room_id)
    if not room or room["host_id"] != user_id:
        raise GameError("Танҳо соҳиби ҳуҷра метавонад бозиро сар кунад.")
    if room["status"] != "lobby":
        raise GameError("Бозӣ аллакай сар шудааст.")
    players = get_active_players(room_id)
    if len(players) < MIN_PLAYERS:
        raise GameError("Барои сар кардан ҳадди ақал 2 бозингар лозим аст.")

    pool = _word_pool_for_room(room_id)
    total_rounds = min(TOTAL_ROUNDS, max(MIN_PLAYERS, len(pool)))
    execute(
        "UPDATE game_rooms SET status = 'playing', phase = 'starting', phase_ends_at = ?, "
        "total_rounds = ? WHERE id = ?",
        ((_now() + timedelta(seconds=STARTING_SECONDS)).isoformat(), total_rounds, room_id),
    )
    return get_room(room_id)


def _generate_round(room):
    used = json.loads(room["used_word_ids"])
    pool = [w for w in _word_pool_for_room(room["id"]) if w["id"] not in used]
    if not pool:
        used = []
        pool = list(_word_pool_for_room(room["id"]))
    correct = random.choice(pool)

    all_words = query_all("SELECT id, tj FROM words WHERE id != ? ORDER BY RANDOM() LIMIT ?",
                           (correct["id"], CHOICES_COUNT - 1))
    choice_ids = [correct["id"]] + [w["id"] for w in all_words]
    random.shuffle(choice_ids)

    used.append(correct["id"])
    next_round = room["round_number"] + 1
    execute(
        "UPDATE game_rooms SET round_number = ?, phase = 'question', phase_ends_at = ?, "
        "current_word_id = ?, current_choices = ?, used_word_ids = ?, last_reveal = NULL WHERE id = ?",
        (
            next_round,
            (_now() + timedelta(seconds=room["round_seconds"])).isoformat(),
            correct["id"],
            json.dumps(choice_ids),
            json.dumps(used),
            room["id"],
        ),
    )


def _finalize_round(room):
    word_id = room["current_word_id"]
    correct_word = _get_word(word_id)
    active = get_active_players(room["id"])
    answers = {
        a["user_id"]: a for a in query_all(
            "SELECT * FROM game_answers WHERE room_id = ? AND round_number = ?",
            (room["id"], room["round_number"]),
        )
    }

    results = []
    for p in active:
        a = answers.get(p["user_id"])
        results.append({
            "user_id": p["user_id"],
            "full_name": p["full_name"],
            "avatar": p["avatar"],
            "correct": bool(a and a["is_correct"]),
            "points": a["points"] if a else 0,
            "choice_word_id": a["choice_word_id"] if a else None,
            "answered": a is not None,
        })

    is_last = room["round_number"] >= room["total_rounds"]
    execute(
        "UPDATE game_rooms SET phase = ?, phase_ends_at = ?, last_reveal = ?, "
        "status = ?, finished_at = ? WHERE id = ?",
        (
            "finished" if is_last else "reveal",
            None if is_last else (_now() + timedelta(seconds=REVEAL_SECONDS)).isoformat(),
            json.dumps({
                "round_number": room["round_number"],
                "ru": correct_word["ru"],
                "correct_tj": correct_word["tj"],
                "results": results,
            }),
            "finished" if is_last else "playing",
            _now_iso() if is_last else None,
            room["id"],
        ),
    )


def _tick(room):
    """Advance the room's phase if enough time has passed / everyone answered.
    Called on every state fetch and every answer submission — no background
    worker needed."""
    if room["status"] != "playing":
        return room

    now = _now()
    if room["phase"] == "starting":
        if room["phase_ends_at"] and now >= _parse(room["phase_ends_at"]):
            _generate_round(room)
            room = get_room(room["id"])

    elif room["phase"] == "question":
        active = get_active_players(room["id"])
        answered = query_all(
            "SELECT DISTINCT user_id FROM game_answers WHERE room_id = ? AND round_number = ?",
            (room["id"], room["round_number"]),
        )
        deadline = room["phase_ends_at"] and now >= _parse(room["phase_ends_at"])
        all_answered = active and len(answered) >= len(active)
        if deadline or all_answered:
            _finalize_round(room)
            room = get_room(room["id"])

    elif room["phase"] == "reveal":
        if room["phase_ends_at"] and now >= _parse(room["phase_ends_at"]):
            _generate_round(room)
            room = get_room(room["id"])

    return room


def submit_answer(room_id: int, user_id: int, choice_word_id: int):
    room = get_room(room_id)
    if not room:
        raise GameError("Ҳуҷра ёфт нашуд.")
    room = _tick(room)
    if room["status"] != "playing" or room["phase"] != "question":
        raise GameError("Ҳоло вақти ҷавоб додан нест.")
    if not is_member(room_id, user_id):
        raise GameError("Шумо дар ин ҳуҷра нестед.")

    existing = query_one(
        "SELECT 1 FROM game_answers WHERE room_id = ? AND round_number = ? AND user_id = ?",
        (room_id, room["round_number"], user_id),
    )
    if existing:
        return _build_state(room, user_id)

    is_correct = int(choice_word_id) == int(room["current_word_id"])
    points = 0
    if is_correct:
        deadline = _parse(room["phase_ends_at"])
        remaining = max(0.0, (deadline - _now()).total_seconds())
        fraction = min(1.0, remaining / room["round_seconds"]) if room["round_seconds"] else 0
        points = BASE_POINTS + round(MAX_SPEED_BONUS * fraction)

    execute(
        "INSERT INTO game_answers (room_id, round_number, user_id, choice_word_id, is_correct, "
        "points, answered_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (room_id, room["round_number"], user_id, choice_word_id, 1 if is_correct else 0, points, _now_iso()),
    )
    execute(
        "UPDATE game_players SET score = score + ?, correct_count = correct_count + ? "
        "WHERE room_id = ? AND user_id = ?",
        (points, 1 if is_correct else 0, room_id, user_id),
    )

    room = _tick(get_room(room_id))
    return _build_state(room, user_id)


# ---------- state assembly (used by the polling endpoint) ----------

def _build_state(room, viewer_id: int):
    players = get_players(room["id"])
    leaderboard = sorted(
        [
            {
                "user_id": p["user_id"], "full_name": p["full_name"], "avatar": p["avatar"],
                "score": p["score"], "correct_count": p["correct_count"],
                "is_host": p["user_id"] == room["host_id"],
                "is_me": p["user_id"] == viewer_id,
                "left": p["left_at"] is not None,
            }
            for p in players
        ],
        key=lambda p: (-p["score"], -p["correct_count"]),
    )

    now = _now()
    seconds_left = None
    if room["phase_ends_at"]:
        seconds_left = max(0, (_parse(room["phase_ends_at"]) - now).total_seconds())

    state = {
        "room_code": room["code"],
        "status": room["status"],
        "phase": room["phase"],
        "round_number": room["round_number"],
        "total_rounds": room["total_rounds"],
        "round_seconds": room["round_seconds"],
        "reveal_seconds": REVEAL_SECONDS,
        "starting_seconds": STARTING_SECONDS,
        "seconds_left": seconds_left,
        "server_time": now.isoformat(),
        "phase_ends_at": room["phase_ends_at"],
        "host_id": room["host_id"],
        "max_players": room["max_players"],
        "min_players": MIN_PLAYERS,
        "viewer_id": viewer_id,
        "leaderboard": leaderboard,
        "question": None,
        "reveal": None,
        "my_answer": None,
    }

    if room["phase"] == "question" and room["current_word_id"]:
        ru_word = _get_word(room["current_word_id"])
        choice_ids = json.loads(room["current_choices"]) if room["current_choices"] else []
        choices = [{"id": c["id"], "tj": c["tj"]} for c in (_get_word(cid) for cid in choice_ids)]
        state["question"] = {"ru": ru_word["ru"]}
        state["choices"] = choices
        my_answer = query_one(
            "SELECT * FROM game_answers WHERE room_id = ? AND round_number = ? AND user_id = ?",
            (room["id"], room["round_number"], viewer_id),
        )
        if my_answer:
            state["my_answer"] = {"choice_word_id": my_answer["choice_word_id"],
                                   "is_correct": bool(my_answer["is_correct"])}

    if room["phase"] == "reveal" and room["last_reveal"]:
        state["reveal"] = json.loads(room["last_reveal"])

    return state


def get_room_state(code: str, viewer_id: int):
    room = get_room_by_code(code)
    if not room:
        raise GameError("Ҳуҷра ёфт нашуд.")
    if not is_member(room["id"], viewer_id):
        raise GameError("Шумо ба ин ҳуҷра ҳамроҳ нашудаед.")
    room = _tick(room)
    return _build_state(room, viewer_id)
