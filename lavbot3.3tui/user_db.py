"""Simple user/settings database.

This module provides a small SQLite store (`user.db`) for storing:
- API tokens (Discord token, weather API key, etc.)
- Authorized user IDs and their personas (e.g. ally/muggy)

The goal is to keep all personal/secret data out of the source tree so it can
be safely published to GitHub.

The database is created automatically when the module is imported.
"""

import os
import sqlite3
from typing import Dict, List, Optional, Tuple

DB_PATH = os.getenv("LAVENDER_USER_DB", "user.db")


def _connect():
    # Ensure the containing directory exists (for future flexibility)
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    """Create the user DB and tables if they don't exist."""
    with _connect() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT,
                persona TEXT
            )"""
        )


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    with _connect() as conn:
        cursor = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else default


def set_setting(key: str, value: str):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        conn.commit()


def delete_setting(key: str) -> bool:
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM settings WHERE key = ?", (key,))
        conn.commit()
        return cursor.rowcount > 0


def list_settings() -> Dict[str, str]:
    with _connect() as conn:
        cursor = conn.execute("SELECT key, value FROM settings")
        return {k: v for k, v in cursor.fetchall()}


def add_user(user_id: int, name: Optional[str] = None, persona: Optional[str] = None):
    """Add or update a user in the allowlist."""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO users (id, name, persona) VALUES (?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET name = excluded.name, persona = excluded.persona",
            (user_id, name, persona),
        )
        conn.commit()


def remove_user(user_id: int) -> bool:
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0


def list_users() -> List[Dict[str, Optional[str]]]:
    with _connect() as conn:
        cursor = conn.execute("SELECT id, name, persona FROM users")
        return [
            {"id": row[0], "name": row[1], "persona": row[2]} for row in cursor.fetchall()
        ]


def get_user(user_id: int) -> Optional[Dict[str, Optional[str]]]:
    with _connect() as conn:
        cursor = conn.execute("SELECT id, name, persona FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return {"id": row[0], "name": row[1], "persona": row[2]}


def is_allowed_user(user_id: int) -> bool:
    return get_user(user_id) is not None


def get_persona_for_user(user_id: int) -> Optional[str]:
    user = get_user(user_id)
    if not user:
        return None
    return user.get("persona")


def get_user_id_by_persona(persona: str) -> Optional[int]:
    with _connect() as conn:
        cursor = conn.execute("SELECT id FROM users WHERE persona = ? LIMIT 1", (persona,))
        row = cursor.fetchone()
        return row[0] if row else None


# Ensure the DB always exists when imported
init_db()
