# -*- coding: utf-8 -*-
"""SQL schema for the web app's SQLite database."""

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    paid INTEGER NOT NULL DEFAULT 0,
    joined_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS words (
    id INTEGER PRIMARY KEY,
    lesson INTEGER NOT NULL,
    lesson_title TEXT NOT NULL,
    ru TEXT NOT NULL,
    tj TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_words_lesson ON words(lesson);

CREATE TABLE IF NOT EXISTS user_word_progress (
    user_id INTEGER NOT NULL,
    word_id INTEGER NOT NULL,
    correct_count INTEGER NOT NULL DEFAULT 0,
    wrong_count INTEGER NOT NULL DEFAULT 0,
    learned INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, word_id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS lesson_progress (
    user_id INTEGER NOT NULL,
    lesson INTEGER NOT NULL,
    completed INTEGER NOT NULL DEFAULT 0,
    correct_count INTEGER NOT NULL DEFAULT 0,
    wrong_count INTEGER NOT NULL DEFAULT 0,
    completed_at TEXT,
    PRIMARY KEY (user_id, lesson),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS test_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    lesson INTEGER NOT NULL,
    word_ids TEXT NOT NULL,
    current_index INTEGER NOT NULL DEFAULT 0,
    correct_count INTEGER NOT NULL DEFAULT 0,
    wrong_count INTEGER NOT NULL DEFAULT 0,
    current_choices TEXT,
    current_correct_id INTEGER,
    answered INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    started_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_test_sessions_user_status ON test_sessions(user_id, status);

CREATE TABLE IF NOT EXISTS certificates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    certificate_id TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    issued_at TEXT NOT NULL,
    file_path TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    note TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_payments_user_status ON payments(user_id, status);
"""
