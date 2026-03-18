import os

os.makedirs("lavender_memory", exist_ok=True)
os.makedirs("lavender_memory/backups", exist_ok=True)

DB_PATH = "lavender_memory/lavender_memory.db"

import aiosqlite
import os

import shutil
import time

def backup_memory():
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = f"lavender_memory/backups/memory_backup_{timestamp}.db"
    shutil.copy(DB_PATH, backup_path)
    prune_old_backups() # auto-clean

    return backup_path


def prune_old_backups(max_backups=20):
    backups = sorted(os.listdir("lavender_memory/backups"))
    if len(backups) > max_backups:
        to_delete = backups[0:len(backups)-max_backups]
        for f in to_delete:
            os.remove(f"lavender_memory/backups/{f}")


async def init_db():
    """Create the memory database if it doesn't exist."""
    if not os.path.exists(DB_PATH):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT,
                    value TEXT
                )
            """)
            await db.commit()


async def remember(key: str, value: str):
    """Store a new memory."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO memories (key, value) VALUES (?, ?)",
            (key, value)
        )
        await db.commit()


async def recall(key: str):
    """Retrieve a memory by key."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT value FROM memories WHERE key = ?",
            (key,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None


async def forget(key: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM memories WHERE key = ?",
            (key,)
        )
        await db.commit()
        return cursor.rowcount > 0


async def update_memory(key: str, new_value: str):
    """Update an existing memory."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE memories SET value = ? WHERE key = ?",
            (new_value, key)
        )
        await db.commit()


async def load_all_memories():
    """Return all memories as a dictionary."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT key, value FROM memories")
        rows = await cursor.fetchall()
        return {key: value for key, value in rows}

async def remember_image(filename: str, tags: list, description: str):
    """Store image metadata in memory."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS image_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                tags TEXT,
                description TEXT
            )
        """)
        await db.execute(
            "INSERT INTO image_memories (filename, tags, description) VALUES (?, ?, ?)",
            (filename, ", ".join(tags), description)
        )
        await db.commit()


async def search_images_by_tag(tag: str):
    """Return all images whose tags contain the given tag."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT filename, tags FROM image_memories WHERE tags LIKE ?",
            (f"%{tag}%",)
        )
        return await cursor.fetchall()

async def list_memories():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT key FROM memories")
        rows = await cursor.fetchall()
        return [r[0] for r in rows]


async def search_memories(query: str):
    """Search all memory values for a keyword."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT key, value FROM memories WHERE value LIKE ?",
            (f"%{query}%",)
        )
        rows = await cursor.fetchall()
        return rows  # list of (key, value)

import difflib

async def fuzzy_search_memories(query: str, threshold: float = 0.5):
    """
    Fuzzy search memory values using similarity scoring.
    Returns list of (key, value, score).
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT key, value FROM memories")
        rows = await cursor.fetchall()

    results = []
    for key, value in rows:
        # Compare query to both key and value
        score_key = difflib.SequenceMatcher(None, query.lower(), key.lower()).ratio()
        score_value = difflib.SequenceMatcher(None, query.lower(), value.lower()).ratio()

        score = max(score_key, score_value)

        if score >= threshold:
            results.append((key, value, score))

    # Sort by best match first
    results.sort(key=lambda x: x[2], reverse=True)
    return results
