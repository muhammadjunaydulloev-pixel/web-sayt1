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
    avatar TEXT,
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

-- Group chat: one shared room, visible to every logged-in user and the admin.
CREATE TABLE IF NOT EXISTS group_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_group_messages_id ON group_messages(id);

-- Private support chat: one thread per user, shared with every admin.
CREATE TABLE IF NOT EXISTS admin_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    sender TEXT NOT NULL,
    message TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_admin_messages_user ON admin_messages(user_id, id);

-- ---------- Мусобиқа (live multiplayer vocabulary duel, 2-4 players) ----------

-- One game room = one match. Created the moment someone sends an invite,
-- lives through the lobby, the live rounds, and the final results screen.
CREATE TABLE IF NOT EXISTS game_rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    host_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'lobby',      -- lobby | playing | finished
    phase TEXT NOT NULL DEFAULT 'lobby',       -- lobby | starting | question | reveal | finished
    max_players INTEGER NOT NULL DEFAULT 4,
    total_rounds INTEGER NOT NULL DEFAULT 10,
    round_number INTEGER NOT NULL DEFAULT 0,
    round_seconds INTEGER NOT NULL DEFAULT 12,
    used_word_ids TEXT NOT NULL DEFAULT '[]',
    current_word_id INTEGER,
    current_choices TEXT,
    phase_ends_at TEXT,
    last_reveal TEXT,
    created_at TEXT NOT NULL,
    finished_at TEXT,
    FOREIGN KEY (host_id) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_game_rooms_status ON game_rooms(status);

CREATE TABLE IF NOT EXISTS game_players (
    room_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    correct_count INTEGER NOT NULL DEFAULT 0,
    joined_at TEXT NOT NULL,
    left_at TEXT,
    PRIMARY KEY (room_id, user_id),
    FOREIGN KEY (room_id) REFERENCES game_rooms(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_game_players_room ON game_players(room_id);

CREATE TABLE IF NOT EXISTS game_answers (
    room_id INTEGER NOT NULL,
    round_number INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    choice_word_id INTEGER,
    is_correct INTEGER NOT NULL DEFAULT 0,
    points INTEGER NOT NULL DEFAULT 0,
    answered_at TEXT NOT NULL,
    PRIMARY KEY (room_id, round_number, user_id)
);

CREATE TABLE IF NOT EXISTS game_invites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,
    from_user_id INTEGER NOT NULL,
    to_user_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',    -- pending | accepted | declined | cancelled
    created_at TEXT NOT NULL,
    responded_at TEXT,
    FOREIGN KEY (room_id) REFERENCES game_rooms(id),
    FOREIGN KEY (from_user_id) REFERENCES users(id),
    FOREIGN KEY (to_user_id) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_game_invites_to ON game_invites(to_user_id, status);
CREATE INDEX IF NOT EXISTS idx_game_invites_room ON game_invites(room_id, status);
"""
