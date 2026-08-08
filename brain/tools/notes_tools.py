"""Tool wrappers for persistent AURA notes."""

from brain.notes import create_note, delete_note, get_note, get_notes, is_valid_note_id


def validate_create(arguments):
    _require_only(arguments, {"content"})
    if not isinstance(arguments["content"], str) or not arguments["content"].strip():
        raise ValueError("'content' must be a non-empty string.")


def validate_empty(arguments):
    _require_only(arguments, set())


def validate_note_id(arguments):
    _require_only(arguments, {"note_id"})
    if not is_valid_note_id(arguments["note_id"]):
        raise ValueError("'note_id' must be a positive integer.")


def create(arguments):
    return {"note": create_note(arguments["content"])}


def list_notes(arguments):
    return {"notes": get_notes()}


def read(arguments):
    return {"note": get_note(arguments["note_id"])}


def delete(arguments):
    return {"deleted": delete_note(arguments["note_id"])}


def _require_only(arguments, expected_keys):
    if not isinstance(arguments, dict) or set(arguments) != expected_keys:
        expected = ", ".join(sorted(expected_keys)) or "no arguments"
        raise ValueError(f"Expected arguments: {expected}.")
