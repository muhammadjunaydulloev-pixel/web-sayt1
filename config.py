# -*- coding: utf-8 -*-
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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

os.makedirs(CERTIFICATES_DIR, exist_ok=True)
os.makedirs(RECEIPTS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
