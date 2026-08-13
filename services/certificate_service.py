# -*- coding: utf-8 -*-
import os
from datetime import datetime, timezone

from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from database.db import execute, query_one
from config import CERTIFICATES_DIR, CERT_PREFIX, TOTAL_LESSONS, TOTAL_WORDS, BASE_DIR

_FONT_NAME = "CertFont"
_FONT_BOLD = "CertFont-Bold"
_FONT_REGISTERED = False


def _register_font():
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return
    regular = os.path.join(BASE_DIR, "fonts", "DejaVuSans.ttf")
    bold = os.path.join(BASE_DIR, "fonts", "DejaVuSans-Bold.ttf")
    try:
        if os.path.exists(regular):
            pdfmetrics.registerFont(TTFont(_FONT_NAME, regular))
        else:
            globals()["_FONT_NAME"] = "Helvetica"
        if os.path.exists(bold):
            pdfmetrics.registerFont(TTFont(_FONT_BOLD, bold))
        else:
            globals()["_FONT_BOLD"] = "Helvetica-Bold"
    except Exception:
        globals()["_FONT_NAME"] = "Helvetica"
        globals()["_FONT_BOLD"] = "Helvetica-Bold"
    _FONT_REGISTERED = True


def get_existing_certificate(user_id: int):
    return query_one("SELECT * FROM certificates WHERE user_id = ?", (user_id,))


def _next_certificate_id():
    year = datetime.now(timezone.utc).year
    row = query_one("SELECT COUNT(*) AS c FROM certificates")
    seq = row["c"] + 1
    return f"{CERT_PREFIX}-{year}-{seq:06d}"


def _draw_certificate(path: str, full_name: str, cert_id: str, date_str: str):
    _register_font()
    os.makedirs(os.path.dirname(path), exist_ok=True)

    page_size = landscape(A4)
    c = canvas.Canvas(path, pagesize=page_size)
    width, height = page_size

    c.setFillColor(HexColor("#FDFBF3"))
    c.rect(0, 0, width, height, fill=1, stroke=0)

    border_color = HexColor("#B8860B")
    c.setStrokeColor(border_color)
    c.setLineWidth(6)
    margin = 1.0 * cm
    c.rect(margin, margin, width - 2 * margin, height - 2 * margin, fill=0, stroke=1)
    c.setLineWidth(1.5)
    inner_margin = margin + 0.35 * cm
    c.rect(inner_margin, inner_margin, width - 2 * inner_margin, height - 2 * inner_margin,
           fill=0, stroke=1)

    center_x = width / 2

    c.setStrokeColor(border_color)
    c.setLineWidth(1.2)
    c.line(center_x - 3 * cm, height - 2.6 * cm, center_x - 0.6 * cm, height - 2.6 * cm)
    c.line(center_x + 0.6 * cm, height - 2.6 * cm, center_x + 3 * cm, height - 2.6 * cm)
    c.setFillColor(border_color)
    c.circle(center_x, height - 2.6 * cm, 0.15 * cm, fill=1, stroke=0)

    c.setFillColor(HexColor("#2C2C2C"))
    c.setFont(_FONT_BOLD, 30)
    c.drawCentredString(center_x, height - 4.2 * cm, "СЕРТИФИКАТ")

    c.setFont(_FONT_NAME, 13)
    c.setFillColor(HexColor("#555555"))
    c.drawCentredString(center_x, height - 5.1 * cm, "Бо ин сертификат тасдиқ карда мешавад, ки")

    c.setFont(_FONT_BOLD, 24)
    c.setFillColor(border_color)
    c.drawCentredString(center_x, height - 6.6 * cm, full_name)

    name_width = c.stringWidth(full_name, _FONT_BOLD, 24)
    c.setStrokeColor(border_color)
    c.setLineWidth(1)
    c.line(center_x - name_width / 2 - 0.5 * cm, height - 7.0 * cm,
           center_x + name_width / 2 + 0.5 * cm, height - 7.0 * cm)

    c.setFont(_FONT_NAME, 13)
    c.setFillColor(HexColor("#333333"))
    c.drawCentredString(center_x, height - 8.0 * cm, "курси омӯзиши")
    c.setFont(_FONT_BOLD, 17)
    c.drawCentredString(center_x, height - 8.8 * cm, "«1300 луғати русӣ-тоҷикӣ»")
    c.setFont(_FONT_NAME, 13)
    c.drawCentredString(center_x, height - 9.6 * cm, "-ро бомуваффақият анҷом дод.")

    c.setFont(_FONT_NAME, 12)
    c.setFillColor(HexColor("#444444"))
    stats = f"{TOTAL_WORDS} луғат      {TOTAL_LESSONS} дарс"
    c.drawCentredString(center_x, height - 11.0 * cm, stats)

    c.setFont(_FONT_NAME, 11)
    c.setFillColor(HexColor("#555555"))
    c.drawString(margin + 1.5 * cm, margin + 1.3 * cm, f"Санаи хатм: {date_str}")
    c.drawRightString(width - margin - 1.5 * cm, margin + 1.3 * cm, f"№ {cert_id}")

    c.showPage()
    c.save()


def generate_certificate(user_id: int, full_name: str):
    existing = get_existing_certificate(user_id)
    if existing:
        return existing

    cert_id = _next_certificate_id()
    date_str = datetime.now(timezone.utc).strftime("%d.%m.%Y")
    filename = f"{cert_id}.pdf"
    path = os.path.join(CERTIFICATES_DIR, filename)

    _draw_certificate(path, full_name, cert_id, date_str)

    execute(
        "INSERT INTO certificates (user_id, certificate_id, full_name, issued_at, file_path) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, cert_id, full_name, datetime.now(timezone.utc).isoformat(), path),
    )

    return get_existing_certificate(user_id)
