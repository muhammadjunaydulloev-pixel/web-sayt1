# -*- coding: utf-8 -*-
from datetime import datetime, timezone

from database.db import execute, query_one, query_all
from config import TOTAL_LESSONS, TOTAL_WORDS


def _now():
    return datetime.now(timezone.utc).isoformat()


def get_lesson_titles():
    rows = query_all("SELECT DISTINCT lesson, lesson_title FROM words ORDER BY lesson ASC")
    return [(r["lesson"], r["lesson_title"]) for r in rows]


def get_lesson_words(lesson: int):
    return query_all("SELECT * FROM words WHERE lesson = ? ORDER BY id ASC", (lesson,))


def is_lesson_completed(user_id: int, lesson: int) -> bool:
    row = query_one(
        "SELECT completed FROM lesson_progress WHERE user_id = ? AND lesson = ?",
        (user_id, lesson),
    )
    return bool(row and row["completed"])


def get_completed_lessons(user_id: int):
    rows = query_all(
        "SELECT lesson FROM lesson_progress WHERE user_id = ? AND completed = 1",
        (user_id,),
    )
    return {r["lesson"] for r in rows}


def get_lesson_progress_map(user_id: int):
    rows = query_all(
        "SELECT lesson, completed, correct_count, wrong_count FROM lesson_progress WHERE user_id = ?",
        (user_id,),
    )
    return {r["lesson"]: dict(r) for r in rows}


def get_next_lesson(user_id: int):
    completed = get_completed_lessons(user_id)
    for lesson in range(1, TOTAL_LESSONS + 1):
        if lesson not in completed:
            return lesson
    return None


def mark_lesson_completed(user_id: int, lesson: int, correct: int, wrong: int):
    execute(
        """
        INSERT INTO lesson_progress (user_id, lesson, completed, correct_count, wrong_count, completed_at)
        VALUES (?, ?, 1, ?, ?, ?)
        ON CONFLICT(user_id, lesson) DO UPDATE SET
            completed = 1,
            correct_count = excluded.correct_count,
            wrong_count = excluded.wrong_count,
            completed_at = excluded.completed_at
        """,
        (user_id, lesson, correct, wrong, _now()),
    )


def get_lesson_progress_detail(user_id: int):
    """Per-lesson breakdown (title, completed, correct/wrong) for a single user —
    used on the admin user-detail page."""
    titles = get_lesson_titles()
    progress_map = get_lesson_progress_map(user_id)
    detail = []
    for lesson_num, title in titles:
        p = progress_map.get(lesson_num)
        detail.append({
            "number": lesson_num,
            "title": title,
            "completed": bool(p and p["completed"]),
            "correct": p["correct_count"] if p else 0,
            "wrong": p["wrong_count"] if p else 0,
        })
    return detail


def get_progress_summary(user_id: int):
    completed_lessons = len(get_completed_lessons(user_id))

    row = query_one(
        """
        SELECT COALESCE(SUM(correct_count), 0) AS correct,
               COALESCE(SUM(wrong_count), 0) AS wrong
        FROM lesson_progress WHERE user_id = ?
        """,
        (user_id,),
    )
    correct = row["correct"]
    wrong = row["wrong"]

    learned_row = query_one(
        "SELECT COUNT(*) AS c FROM user_word_progress WHERE user_id = ? AND learned = 1",
        (user_id,),
    )
    words_learned = learned_row["c"]

    total_answers = correct + wrong
    percent = round((correct / total_answers) * 100, 1) if total_answers else 0.0

    return {
        "lessons_completed": completed_lessons,
        "total_lessons": TOTAL_LESSONS,
        "words_learned": words_learned,
        "total_words": TOTAL_WORDS,
        "correct": correct,
        "wrong": wrong,
        "percent": percent,
        "course_completed": completed_lessons >= TOTAL_LESSONS,
    }
