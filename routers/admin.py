# -*- coding: utf-8 -*-
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse

from deps import templates, require_admin
from database.db import query_all, query_one, execute
from services import payment_service, certificate_service, lesson_service
from config import TOTAL_LESSONS, TOTAL_WORDS

router = APIRouter(prefix="/admin")


@router.get("")
def admin_dashboard(request: Request):
    admin = require_admin(request)

    stats = query_one(
        """
        SELECT
          (SELECT COUNT(*) FROM users WHERE is_admin = 0) AS total_users,
          (SELECT COUNT(*) FROM users WHERE is_admin = 0 AND paid = 1) AS paid_users,
          (SELECT COALESCE(SUM(correct_count),0) FROM lesson_progress) AS total_correct,
          (SELECT COALESCE(SUM(wrong_count),0) FROM lesson_progress) AS total_wrong,
          (SELECT COUNT(*) FROM certificates) AS total_certificates,
          (SELECT COUNT(*) FROM payments WHERE status = 'pending') AS pending_payments
        """
    )
    recent_users = query_all(
        "SELECT * FROM users WHERE is_admin = 0 ORDER BY id DESC LIMIT 20"
    )
    users_with_progress = []
    for u in recent_users:
        summary = lesson_service.get_progress_summary(u["id"])
        users_with_progress.append({"user": u, "summary": summary})

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request, "admin": admin, "stats": stats,
        "users_with_progress": users_with_progress,
        "total_lessons": TOTAL_LESSONS, "total_words": TOTAL_WORDS,
    })


@router.get("/payments")
def admin_payments(request: Request):
    admin = require_admin(request)
    pending = payment_service.list_pending_payments()
    return templates.TemplateResponse("admin/payments.html", {
        "request": request, "admin": admin, "pending": pending,
    })


@router.post("/payments/{payment_id}/approve")
def admin_approve_payment(request: Request, payment_id: int):
    require_admin(request)
    payment = payment_service.get_payment(payment_id)
    if payment:
        payment_service.approve_payment(payment_id, payment["user_id"])
    return RedirectResponse("/admin/payments", status_code=303)


@router.post("/payments/{payment_id}/reject")
def admin_reject_payment(request: Request, payment_id: int):
    require_admin(request)
    payment_service.reject_payment(payment_id)
    return RedirectResponse("/admin/payments", status_code=303)


@router.get("/dictionary")
def admin_dictionary(request: Request):
    admin = require_admin(request)
    counts = query_all(
        "SELECT lesson, lesson_title, COUNT(*) AS c FROM words GROUP BY lesson ORDER BY lesson"
    )
    return templates.TemplateResponse("admin/dictionary.html", {
        "request": request, "admin": admin, "counts": counts,
    })


@router.post("/dictionary/add")
def admin_dictionary_add(request: Request, lesson: int = Form(...),
                          lesson_title: str = Form(...), ru: str = Form(...), tj: str = Form(...)):
    require_admin(request)
    row = query_one("SELECT MAX(id) AS m FROM words")
    new_id = (row["m"] or 0) + 1
    execute(
        "INSERT INTO words (id, lesson, lesson_title, ru, tj) VALUES (?, ?, ?, ?, ?)",
        (new_id, lesson, lesson_title.strip(), ru.strip(), tj.strip()),
    )
    return RedirectResponse("/admin/dictionary", status_code=303)


@router.get("/certificates")
def admin_certificates(request: Request):
    admin = require_admin(request)
    certs = query_all(
        """
        SELECT certificates.*, users.phone
        FROM certificates JOIN users ON users.id = certificates.user_id
        ORDER BY certificates.id DESC LIMIT 50
        """
    )
    return templates.TemplateResponse("admin/certificates.html", {
        "request": request, "admin": admin, "certs": certs,
    })
