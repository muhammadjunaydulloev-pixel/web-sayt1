# -*- coding: utf-8 -*-
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load variables from a local .env file if one exists (never committed to git).
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except ImportError:
    pass
DB_PATH = os.path.join(BASE_DIR, "database", "app.db")
WORDS_JSON_PATH = os.path.join(BASE_DIR, "data", "words.json")
CERTIFICATES_DIR = os.path.join(BASE_DIR, "static", "certificates")
RECEIPTS_DIR = os.path.join(BASE_DIR, "static", "uploads", "receipts")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production-slovarho")

TOTAL_LESSONS = 26
WORDS_PER_LESSON = 50
TOTAL_WORDS = TOTAL_LESSONS * WORDS_PER_LESSON

WORDS_PER_TEST_ROUND = 10
CHOICES_COUNT = 4

CERT_PREFIX = "RTV"

PAYMENT_CARD_NUMBER = os.getenv("PAYMENT_CARD_NUMBER", "973015522")
PAYMENT_CARD_NAME = os.getenv("PAYMENT_CARD_NAME", "Корти Душанбе Сити")
COURSE_PRICE = os.getenv("COURSE_PRICE", "89")

# The first lesson is free so visitors can try the course before paying.
FREE_LESSON = 1

# Preset avatars users can pick from their profile page — an emoji on a
# themed background color, no external images or uploads needed.
AVATARS = [
    "🦊", "🐼", "🐯", "🐶", "🐱", "🦁", "🐨", "🐵",
    "🦄", "🐸", "🐧", "🦉", "🐺", "🐰", "🐻", "🦋",
]

os.makedirs(CERTIFICATES_DIR, exist_ok=True)
os.makedirs(RECEIPTS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# ---------- AI Assistant ----------
# The API key must NEVER be hardcoded here or shipped to the frontend.
# Set these in a local ".env" file (see ".env.example"). Supported providers:
# "openai", "anthropic". Leave AI_PROVIDER as "none" (or AI_API_KEY empty) to
# run the assistant in offline demo mode until real credentials are added.
AI_PROVIDER = os.getenv("AI_PROVIDER", "none").strip().lower()
AI_API_KEY = os.getenv("AI_API_KEY", "").strip()
AI_MODEL = os.getenv("AI_MODEL", "").strip()
