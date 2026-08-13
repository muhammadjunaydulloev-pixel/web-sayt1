# -*- coding: utf-8 -*-
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, JSONResponse

from deps import templates, require_admin
from database.db import query_all, query_one, execute
from services import payment_service, certificate_service, lesson_service, auth_service, chat_service
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


# ---------- Users ----------

@router.get("/users")
def admin_users(request: Request, q: str = ""):
    admin = require_admin(request)
    users = auth_service.list_all_users(q)
    users_with_progress = [
        {"user": u, "summary": lesson_service.get_progress_summary(u["id"])} for u in users
    ]
    return templates.TemplateResponse("admin/users.html", {
        "request": request, "admin": admin, "users_with_progress": users_with_progress,
        "total_lessons": TOTAL_LESSONS, "q": q,
    })


@router.get("/users/{user_id}")
def admin_user_detail(request: Request, user_id: int):
    admin = require_admin(request)
    user = auth_service.get_user_by_id(user_id)
    if user is None or user["is_admin"]:
        return RedirectResponse("/admin/users", status_code=303)
    summary = lesson_service.get_progress_summary(user_id)
    lesson_detail = lesson_service.get_lesson_progress_detail(user_id)
    certificate = certificate_service.get_existing_certificate(user_id)
    payments = payment_service.list_payments_for_user(user_id)
    return templates.TemplateResponse("admin/user_detail.html", {
        "request": request, "admin": admin, "user": user, "summary": summary,
        "lesson_detail": lesson_detail, "certificate": certificate, "payments": payments,
    })


@router.post("/users/{user_id}/toggle-paid")
def admin_user_toggle_paid(request: Request, user_id: int):
    require_admin(request)
    user = auth_service.get_user_by_id(user_id)
    if user and not user["is_admin"]:
        execute("UPDATE users SET paid = ? WHERE id = ?", (0 if user["paid"] else 1, user_id))
    return RedirectResponse(f"/admin/users/{user_id}", status_code=303)


# ---------- Admin ↔ user chat ----------

@router.get("/chat")
def admin_chat_page(request: Request, user: int = 0):
    admin = require_admin(request)
    conversations = chat_service.list_conversations()
    selected_id = user or (conversations[0]["user_id"] if conversations else None)
    if selected_id:
        chat_service.mark_read(selected_id, reader="admin")
    selected_user = auth_service.get_user_by_id(selected_id) if selected_id else None
    return templates.TemplateResponse("admin/chat.html", {
        "request": request, "admin": admin, "conversations": conversations,
        "selected_id": selected_id, "selected_user": selected_user,
    })


@router.get("/chat/{user_id}/messages")
def admin_api_chat_messages(request: Request, user_id: int, after_id: int = 0):
    require_admin(request)
    chat_service.mark_read(user_id, reader="admin")
    rows = chat_service.get_admin_messages(user_id, after_id)
    return JSONResponse({
        "messages": [
            {"id": r["id"], "sender": r["sender"], "message": r["message"], "created_at": r["created_at"]}
            for r in rows
        ]
    })


@router.post("/chat/{user_id}/send")
def admin_chat_send(request: Request, user_id: int, message: str = Form(...)):
    require_admin(request)
    chat_service.send_admin_message(user_id, "admin", message)
    return JSONResponse({"ok": True})
