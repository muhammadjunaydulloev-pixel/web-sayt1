# -*- coding: utf-8 -*-
import json
import random
from datetime import datetime, timezone

from database.db import execute, query_one, query_all
from config import WORDS_PER_TEST_ROUND, CHOICES_COUNT
from services import lesson_service


def _now():
    return datetime.now(timezone.utc).isoformat()


def get_active_session(user_id: int, lesson: int):
    return query_one(
        "SELECT * FROM test_sessions WHERE user_id = ? AND lesson = ? AND status = 'active' "
        "ORDER BY id DESC LIMIT 1",
        (user_id, lesson),
    )


def get_session(session_id: int):
    return query_one("SELECT * FROM test_sessions WHERE id = ?", (session_id,))


def _get_word(word_id: int):
    return query_one("SELECT * FROM words WHERE id = ?", (word_id,))


def start_new_test(user_id: int, lesson: int):
    words = lesson_service.get_lesson_words(lesson)
    if not words:
        return None

    # Abandon any stale active session for this lesson first.
    execute(
        "UPDATE test_sessions SET status = 'abandoned' WHERE user_id = ? AND lesson = ? AND status = 'active'",
        (user_id, lesson),
    )

    sample = list(words)
    random.shuffle(sample)
    sample = sample[:WORDS_PER_TEST_ROUND]
    word_ids = [w["id"] for w in sample]

    cur = execute(
        """
        INSERT INTO test_sessions (user_id, lesson, word_ids, current_index,
                                    correct_count, wrong_count, status, started_at, answered)
        VALUES (?, ?, ?, 0, 0, 0, 'active', ?, 0)
        """,
        (user_id, lesson, json.dumps(word_ids), _now()),
    )
    session_id = cur.lastrowid
    _prepare_question(session_id)
    return get_session(session_id)


def _prepare_question(session_id: int):
    session = get_session(session_id)
    word_ids = json.loads(session["word_ids"])
    idx = session["current_index"]
    correct_word_id = word_ids[idx]

    distractors = query_all(
        "SELECT id, tj FROM words WHERE lesson = ? AND id != ? ORDER BY RANDOM() LIMIT ?",
        (session["lesson"], correct_word_id, CHOICES_COUNT - 1),
    )

    if len(distractors) < CHOICES_COUNT - 1:
        missing = (CHOICES_COUNT - 1) - len(distractors)
        existing_ids = [d["id"] for d in distractors] + [correct_word_id]
        placeholders = ",".join("?" * len(existing_ids))
        extra = query_all(
            f"SELECT id, tj FROM words WHERE id NOT IN ({placeholders}) ORDER BY RANDOM() LIMIT ?",
            (*existing_ids, missing),
        )
        distractors = list(distractors) + list(extra)

    choice_ids = [correct_word_id] + [d["id"] for d in distractors]
    random.shuffle(choice_ids)

    execute(
        "UPDATE test_sessions SET current_choices = ?, current_correct_id = ?, answered = 0 WHERE id = ?",
        (json.dumps(choice_ids), correct_word_id, session_id),
    )


def get_current_question(session_id: int):
    session = get_session(session_id)
    if session is None:
        return None, [], None
    word_ids = json.loads(session["word_ids"])
    idx = session["current_index"]
    if idx >= len(word_ids):
        return None, [], session

    ru_word = _get_word(word_ids[idx])
    choice_ids = json.loads(session["current_choices"]) if session["current_choices"] else []
    choices = [_get_word(cid) for cid in choice_ids]
    return ru_word, choices, session


def submit_answer(session_id: int, chosen_word_id: int):
    session = get_session(session_id)
    if session is None or session["status"] != "active":
        return {"status": "invalid"}

    if session["answered"]:
        return {"status": "duplicate"}

    word_ids = json.loads(session["word_ids"])
    idx = session["current_index"]
    correct_id = session["current_correct_id"]
    is_correct = int(chosen_word_id) == int(correct_id)
    correct_word = _get_word(correct_id)

    cur = execute(
        "UPDATE test_sessions SET answered = 1 WHERE id = ? AND answered = 0", (session_id,)
    )
    if cur.rowcount == 0:
        return {"status": "duplicate"}

    new_correct = session["correct_count"] + (1 if is_correct else 0)
    new_wrong = session["wrong_count"] + (0 if is_correct else 1)
    execute(
        "UPDATE test_sessions SET correct_count = ?, wrong_count = ? WHERE id = ?",
        (new_correct, new_wrong, session_id),
    )

    wp = query_one(
        "SELECT * FROM user_word_progress WHERE user_id = ? AND word_id = ?",
        (session["user_id"], correct_id),
    )
    if wp is None:
        execute(
            "INSERT INTO user_word_progress (user_id, word_id, correct_count, wrong_count, learned) "
            "VALUES (?, ?, ?, ?, ?)",
            (session["user_id"], correct_id, 1 if is_correct else 0, 0 if is_correct else 1,
             1 if is_correct else 0),
        )
    else:
        c = wp["correct_count"] + (1 if is_correct else 0)
        w = wp["wrong_count"] + (0 if is_correct else 1)
        learned = 1 if (is_correct or wp["learned"]) else wp["learned"]
        execute(
            "UPDATE user_word_progress SET correct_count = ?, wrong_count = ?, learned = ? "
            "WHERE user_id = ? AND word_id = ?",
            (c, w, learned, session["user_id"], correct_id),
        )

    next_index = idx + 1
    finished = next_index >= len(word_ids)

    if finished:
        execute(
            "UPDATE test_sessions SET current_index = ?, status = 'completed' WHERE id = ?",
            (next_index, session_id),
        )
    else:
        execute("UPDATE test_sessions SET current_index = ? WHERE id = ?", (next_index, session_id))

    result = {
        "status": "correct" if is_correct else "wrong",
        "correct_tj": correct_word["tj"],
        "correct_ru": correct_word["ru"],
        "finished": finished,
    }

    if finished:
        final_session = get_session(session_id)
        result["final_correct"] = final_session["correct_count"]
        result["final_wrong"] = final_session["wrong_count"]
        result["lesson"] = session["lesson"]
        lesson_service.mark_lesson_completed(
            session["user_id"], session["lesson"],
            final_session["correct_count"], final_session["wrong_count"],
        )
    else:
        _prepare_question(session_id)

    return result
