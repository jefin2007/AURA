"""SQLite persistence and normalized memory management for AURA."""

import re
import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE = PROJECT_ROOT / "data" / "memory.db"
MEMORY_CATEGORIES = {"profile", "preference", "fact", "general"}


class MemoryConflictError(ValueError):
    """Raised when multiple legacy records map to the same normalized key."""


def connect():
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DATABASE)


def normalize_memory_key(key):
    """Create one stable key form without changing the key's meaning."""
    if not isinstance(key, str):
        raise ValueError("Memory keys must be text.")

    normalized = re.sub(r"[\s_-]+", "_", key.strip().lower())
    normalized = normalized.strip("_")
    if not normalized:
        raise ValueError("Memory keys cannot be empty.")
    return normalized


def create_memory_table():
    """Create or safely migrate the existing persistent memory database."""
    connection = connect()
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT,
                category TEXT NOT NULL DEFAULT 'general',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_conflicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                normalized_key TEXT NOT NULL,
                memory_id INTEGER NOT NULL,
                original_key TEXT NOT NULL,
                value TEXT,
                category TEXT NOT NULL DEFAULT 'general',
                detected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(normalized_key, memory_id)
            )
            """
        )
        _add_missing_memory_columns(connection)
        _migrate_memory_rows(connection)
        connection.commit()
    finally:
        connection.close()


def save_memory(key, value, category=None):
    """Create or update one normalized memory while preserving its creation time."""
    normalized_key = normalize_memory_key(key)
    if not isinstance(value, str):
        raise ValueError("Memory values must be text.")
    category = _validate_category(category, normalized_key)

    create_memory_table()
    connection = connect()
    try:
        matches = _matching_memory_rows(connection, normalized_key)
        if len(matches) > 1:
            _record_conflicts(connection, normalized_key, matches)
            connection.commit()
            raise MemoryConflictError(
                f"Conflicting memories exist for '{normalized_key}'."
            )

        if matches:
            connection.execute(
                """
                UPDATE memory
                SET key = ?, value = ?, category = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (normalized_key, value, category, matches[0][0]),
            )
        else:
            connection.execute(
                """
                INSERT INTO memory (key, value, category)
                VALUES (?, ?, ?)
                """,
                (normalized_key, value, category),
            )
        connection.commit()
    finally:
        connection.close()


def get_memory(key):
    """Return one exact normalized memory value, or None when absent/ambiguous."""
    normalized_key = normalize_memory_key(key)
    create_memory_table()
    connection = connect()
    try:
        matches = _matching_memory_rows(connection, normalized_key)
        return matches[0][2] if len(matches) == 1 else None
    finally:
        connection.close()


def get_memories():
    """Return all stored memories with metadata for user-facing management."""
    create_memory_table()
    connection = connect()
    try:
        rows = connection.execute(
            "SELECT id, key, value, category, created_at, updated_at FROM memory ORDER BY key"
        ).fetchall()
        return [_memory_from_row(row) for row in rows]
    finally:
        connection.close()


def search_memories(query, limit=5):
    """Return only the strongest exact or normalized keyword memory matches."""
    if not isinstance(query, str) or not query.strip() or not isinstance(limit, int) or limit < 1:
        return []

    normalized_query = normalize_memory_key(query)
    create_memory_table()
    connection = connect()
    try:
        rows = connection.execute(
            "SELECT id, key, value, category, created_at, updated_at FROM memory"
        ).fetchall()
        memories = [_memory_from_row(row) for row in rows]
    finally:
        connection.close()

    exact_matches = [memory for memory in memories if normalize_memory_key(memory["key"]) == normalized_query]
    if exact_matches:
        return exact_matches[:limit]

    query_terms = set(normalized_query.split("_"))
    ranked = []
    for memory in memories:
        key_terms = set(normalize_memory_key(memory["key"]).split("_"))
        overlap = len(query_terms & key_terms)
        if overlap:
            ranked.append((overlap, memory))

    ranked.sort(key=lambda item: (-item[0], item[1]["key"]))
    return [memory for _, memory in ranked[:limit]]


def delete_memory(key):
    """Delete one exact normalized key, never a similarly named memory."""
    normalized_key = normalize_memory_key(key)
    create_memory_table()
    connection = connect()
    try:
        matches = _matching_memory_rows(connection, normalized_key)
        if len(matches) != 1:
            return False
        cursor = connection.execute("DELETE FROM memory WHERE id = ?", (matches[0][0],))
        connection.commit()
        return cursor.rowcount > 0
    finally:
        connection.close()


def get_memory_conflicts():
    """Expose legacy normalization conflicts without deleting either memory."""
    create_memory_table()
    connection = connect()
    try:
        rows = connection.execute(
            """
            SELECT normalized_key, memory_id, original_key, value, category, detected_at
            FROM memory_conflicts
            ORDER BY normalized_key, memory_id
            """
        ).fetchall()
        return [
            {
                "normalized_key": row[0],
                "memory_id": row[1],
                "original_key": row[2],
                "value": row[3],
                "category": row[4],
                "detected_at": row[5],
            }
            for row in rows
        ]
    finally:
        connection.close()


def _add_missing_memory_columns(connection):
    columns = {row[1] for row in connection.execute("PRAGMA table_info(memory)")}
    if "category" not in columns:
        connection.execute("ALTER TABLE memory ADD COLUMN category TEXT DEFAULT 'general'")
    if "created_at" not in columns:
        connection.execute("ALTER TABLE memory ADD COLUMN created_at TEXT")
    if "updated_at" not in columns:
        connection.execute("ALTER TABLE memory ADD COLUMN updated_at TEXT")
    connection.execute(
        """
        UPDATE memory
        SET category = COALESCE(category, 'general'),
            created_at = COALESCE(created_at, CURRENT_TIMESTAMP),
            updated_at = COALESCE(updated_at, CURRENT_TIMESTAMP)
        """
    )


def _migrate_memory_rows(connection):
    rows = connection.execute(
        "SELECT id, key, value, category FROM memory ORDER BY id"
    ).fetchall()
    groups = {}
    for row in rows:
        normalized_key = normalize_memory_key(row[1])
        groups.setdefault(normalized_key, []).append(row)

    for normalized_key, group in groups.items():
        if len(group) == 1:
            memory_id, original_key, _, category = group[0]
            inferred_category = _validate_category(category, normalized_key)
            connection.execute(
                "UPDATE memory SET key = ?, category = ? WHERE id = ?",
                (normalized_key, inferred_category, memory_id),
            )
        else:
            _record_conflicts(connection, normalized_key, group)


def _matching_memory_rows(connection, normalized_key):
    rows = connection.execute(
        "SELECT id, key, value, category FROM memory"
    ).fetchall()
    return [row for row in rows if normalize_memory_key(row[1]) == normalized_key]


def _record_conflicts(connection, normalized_key, rows):
    for memory_id, original_key, value, category in rows:
        connection.execute(
            """
            INSERT OR IGNORE INTO memory_conflicts
            (normalized_key, memory_id, original_key, value, category)
            VALUES (?, ?, ?, ?, ?)
            """,
            (normalized_key, memory_id, original_key, value, category or "general"),
        )


def _validate_category(category, normalized_key):
    if category is None:
        if normalized_key in {"user_name", "user_age", "user_location", "user_birthday"}:
            return "profile"
        if "favourite" in normalized_key or "favorite" in normalized_key:
            return "preference"
        return "general"
    if not isinstance(category, str) or category.lower() not in MEMORY_CATEGORIES:
        raise ValueError("Invalid memory category.")
    return category.lower()


def _memory_from_row(row):
    return {
        "id": row[0],
        "key": row[1],
        "value": row[2],
        "category": row[3],
        "created_at": row[4],
        "updated_at": row[5],
    }
