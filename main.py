# -*- coding: utf-8 -*-
import os
import uuid

from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from config import (
    SECRET_KEY, BASE_DIR, TOTAL_LESSONS, FREE_LESSON,
    PAYMENT_CARD_NUMBER, PAYMENT_CARD_NAME, COURSE_PRICE, RECEIPTS_DIR,
)
from database.db import init_db
from deps import templates, get_current_user, require_login, require_admin, RedirectException
from services import auth_service, lesson_service, test_service, certificate_service, payment_service
from routers import admin as admin_router

app = FastAPI(title="1300 Луғат — Русӣ-Тоҷикӣ")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, session_cookie="slovarho_session")
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
app.include_router(admin_router.router)


@app.exception_handler(RedirectException)
async def redirect_handler(request: Request, exc: RedirectException):
    return RedirectResponse(exc.url, status_code=303)


@app.on_event("startup")
def _startup():
    init_db()
    # Bootstrap a default admin so the site owner can log in immediately.
    if not auth_service.get_user_by_phone("admin"):
        auth_service.create_user("Админ", "admin", "admin123", is_admin=True)


def can_access_lesson(user, lesson: int) -> bool:
    if lesson == FREE_LESSON:
        return True
    return bool(user and user["paid"])


# ---------- Public / landing ----------

@app.get("/")
def home(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse("/lessons", status_code=303)
    lesson_titles = lesson_service.get_lesson_titles()
    return templates.TemplateResponse("landing.html", {
        "request": request,
        "lesson_titles": lesson_titles,
        "total_lessons": TOTAL_LESSONS,
        "price": COURSE_PRICE,
    })


# ---------- Auth ----------

@app.get("/register")
def register_page(request: Request):
    if get_current_user(request):
        return RedirectResponse("/lessons", status_code=303)
    return templates.TemplateResponse("register.html", {"request": request, "error": None})


@app.post("/register")
def register_submit(request: Request, full_name: str = Form(...), phone: str = Form(...),
                     password: str = Form(...), password2: str = Form(...)):
    full_name = full_name.strip()
    phone = phone.strip()
    error = None
    if len(full_name) < 2:
        error = "Лутфан номи пурраи худро нависед."
    elif len(phone) < 5:
        error = "Рақами телефон нодуруст аст."
    elif len(password) < 4:
        error = "Парол бояд ҳадди ақал 4 аломат бошад."
    elif password != password2:
        error = "Паролҳо мувофиқат намекунанд."
    elif auth_service.get_user_by_phone(phone):
        error = "Ин рақами телефон аллакай сабт шудааст."

    if error:
        return templates.TemplateResponse("register.html", {"request": request, "error": error},
                                            status_code=400)

    user = auth_service.create_user(full_name, phone, password)
    request.session["user_id"] = user["id"]
    return RedirectResponse("/lessons", status_code=303)


@app.get("/login")
def login_page(request: Request):
    if get_current_user(request):
        return RedirectResponse("/lessons", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login")
def login_submit(request: Request, phone: str = Form(...), password: str = Form(...)):
    user = auth_service.authenticate(phone, password)
    if not user:
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Рақами телефон ё парол нодуруст аст."},
            status_code=400,
        )
    request.session["user_id"] = user["id"]
    if user["is_admin"]:
        return RedirectResponse("/admin", status_code=303)
    return RedirectResponse("/lessons", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


# ---------- Lessons ----------

@app.get("/lessons")
def lessons_page(request: Request):
    user = require_login(request)
    lesson_titles = lesson_service.get_lesson_titles()
    progress_map = lesson_service.get_lesson_progress_map(user["id"])
    next_lesson = lesson_service.get_next_lesson(user["id"])
    summary = lesson_service.get_progress_summary(user["id"])

    lessons = []
    for lesson_num, title in lesson_titles:
        lessons.append({
            "number": lesson_num,
            "title": title,
            "completed": lesson_num in progress_map and progress_map[lesson_num]["completed"],
            "locked": not can_access_lesson(user, lesson_num),
            "is_next": lesson_num == next_lesson,
        })

    return templates.TemplateResponse("lessons.html", {
        "request": request, "user": user, "lessons": lessons, "summary": summary,
    })


@app.get("/lesson/{lesson_num}")
def lesson_detail(request: Request, lesson_num: int):
    user = require_login(request)
    if lesson_num < 1 or lesson_num > TOTAL_LESSONS:
        return RedirectResponse("/lessons", status_code=303)
    if not can_access_lesson(user, lesson_num):
        return RedirectResponse("/payment", status_code=303)

    words = lesson_service.get_lesson_words(lesson_num)
    lesson_titles = dict(lesson_service.get_lesson_titles())
    completed = lesson_service.is_lesson_completed(user["id"], lesson_num)

    return templates.TemplateResponse("lesson_detail.html", {
        "request": request, "user": user, "lesson_num": lesson_num,
        "lesson_title": lesson_titles.get(lesson_num, ""),
        "words": words, "completed": completed,
    })


@app.get("/lesson/{lesson_num}/test")
def lesson_test_page(request: Request, lesson_num: int):
    user = require_login(request)
    if lesson_num < 1 or lesson_num > TOTAL_LESSONS:
        return RedirectResponse("/lessons", status_code=303)
    if not can_access_lesson(user, lesson_num):
        return RedirectResponse("/payment", status_code=303)
    lesson_titles = dict(lesson_service.get_lesson_titles())
    return templates.TemplateResponse("test.html", {
        "request": request, "user": user, "lesson_num": lesson_num,
        "lesson_title": lesson_titles.get(lesson_num, ""),
    })


# ---------- Test flow (JSON API used by the lesson test page) ----------

def _question_payload(session_id):
    ru_word, choices, session = test_service.get_current_question(session_id)
    if ru_word is None:
        return None
    return {
        "session_id": session_id,
        "question_number": session["current_index"] + 1,
        "total_questions": len(__import__("json").loads(session["word_ids"])),
        "ru": ru_word["ru"],
        "choices": [{"id": c["id"], "tj": c["tj"]} for c in choices],
        "correct_count": session["correct_count"],
        "wrong_count": session["wrong_count"],
    }


@app.post("/api/test/start/{lesson_num}")
def api_test_start(request: Request, lesson_num: int):
    user = require_login(request)
    if not can_access_lesson(user, lesson_num):
        return JSONResponse({"error": "locked"}, status_code=403)
    session = test_service.start_new_test(user["id"], lesson_num)
    if session is None:
        return JSONResponse({"error": "no_words"}, status_code=404)
    return JSONResponse(_question_payload(session["id"]))


@app.post("/api/test/{session_id}/answer")
def api_test_answer(request: Request, session_id: int, choice_id: int = Form(...)):
    user = require_login(request)
    session = test_service.get_session(session_id)
    if session is None or session["user_id"] != user["id"]:
        return JSONResponse({"error": "not_found"}, status_code=404)

    result = test_service.submit_answer(session_id, choice_id)
    if result.get("status") in ("invalid", "duplicate"):
        return JSONResponse(result, status_code=409)

    if not result["finished"]:
        result["next_question"] = _question_payload(session_id)
    return JSONResponse(result)


# ---------- Profile / certificate ----------

@app.get("/profile")
def profile_page(request: Request):
    user = require_login(request)
    summary = lesson_service.get_progress_summary(user["id"])
    certificate = certificate_service.get_existing_certificate(user["id"])
    payment = payment_service.get_latest_payment(user["id"])
    return templates.TemplateResponse("profile.html", {
        "request": request, "user": user, "summary": summary,
        "certificate": certificate, "payment": payment,
    })


@app.get("/certificate/download")
def certificate_download(request: Request):
    user = require_login(request)
    summary = lesson_service.get_progress_summary(user["id"])
    if not summary["course_completed"]:
        return RedirectResponse("/profile", status_code=303)
    cert = certificate_service.generate_certificate(user["id"], user["full_name"])
    return FileResponse(cert["file_path"], media_type="application/pdf",
                         filename=f"sertifikat-{cert['certificate_id']}.pdf")


# ---------- Payment ----------

@app.get("/payment")
def payment_page(request: Request):
    user = require_login(request)
    pending = payment_service.has_pending_payment(user["id"])
    latest = payment_service.get_latest_payment(user["id"])
    return templates.TemplateResponse("payment.html", {
        "request": request, "user": user, "pending": pending, "latest": latest,
        "card_number": PAYMENT_CARD_NUMBER, "card_name": PAYMENT_CARD_NAME, "price": COURSE_PRICE,
    })


@app.post("/payment")
async def payment_submit(request: Request, receipt: UploadFile = File(...)):
    user = require_login(request)
    ext = os.path.splitext(receipt.filename or "")[1] or ".jpg"
    filename = f"{user['id']}_{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(RECEIPTS_DIR, filename)
    content = await receipt.read()
    with open(dest_path, "wb") as f:
        f.write(content)
    payment_service.create_payment_request(user["id"], os.path.join("uploads", "receipts", filename))
    return RedirectResponse("/payment", status_code=303)
