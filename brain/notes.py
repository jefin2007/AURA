"""Persistent note storage for AURA."""

from brain.database import connect


def create_notes_table():
    """Create the notes table when it does not already exist."""
    connection = connect()
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.commit()
    finally:
        connection.close()


def create_note(content):
    """Save a note and return it, or return None for empty content."""
    if not isinstance(content, str) or not content.strip():
        return None

    create_notes_table()
    connection = connect()
    try:
        cursor = connection.execute(
            "INSERT INTO notes (content) VALUES (?)",
            (content.strip(),),
        )
        connection.commit()
        return get_note(cursor.lastrowid)
    finally:
        connection.close()


def get_notes():
    """Return all saved notes in creation order."""
    create_notes_table()
    connection = connect()
    try:
        rows = connection.execute(
            "SELECT id, content, created_at FROM notes ORDER BY id"
        ).fetchall()
        return [_note_from_row(row) for row in rows]
    finally:
        connection.close()


def get_note(note_id):
    """Return a note by ID, or None when the ID is invalid or absent."""
    note_id = _normalise_note_id(note_id)
    if note_id is None:
        return None

    create_notes_table()
    connection = connect()
    try:
        row = connection.execute(
            "SELECT id, content, created_at FROM notes WHERE id = ?",
            (note_id,),
        ).fetchone()
        return _note_from_row(row) if row else None
    finally:
        connection.close()


def delete_note(note_id):
    """Delete a note by ID and report whether a note was deleted."""
    note_id = _normalise_note_id(note_id)
    if note_id is None:
        return False

    create_notes_table()
    connection = connect()
    try:
        cursor = connection.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        connection.commit()
        return cursor.rowcount > 0
    finally:
        connection.close()


def is_valid_note_id(note_id):
    """Return whether a value is a positive integer note ID."""
    return _normalise_note_id(note_id) is not None


def _normalise_note_id(note_id):
    if isinstance(note_id, bool):
        return None
    if isinstance(note_id, int):
        return note_id if note_id > 0 else None
    if isinstance(note_id, str) and note_id.isdigit():
        value = int(note_id)
        return value if value > 0 else None
    return None


def _note_from_row(row):
    return {"id": row[0], "content": row[1], "created_at": row[2]}
