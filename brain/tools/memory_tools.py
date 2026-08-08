"""Tool wrappers for AURA's persistent key/value memory."""

from brain.ai.memory_retrieval import retrieve_memories
from brain.database import delete_memory, normalize_memory_key, save_memory


def validate_search(arguments):
    _require_only(arguments, {"query"})
    if not isinstance(arguments["query"], str) or not arguments["query"].strip():
        raise ValueError("'query' must be a non-empty string.")


def validate_save(arguments):
    if not isinstance(arguments, dict) or set(arguments) not in ({"key", "value"}, {"key", "value", "category"}):
        raise ValueError("Expected arguments: key, value, and optional category.")
    if not all(isinstance(arguments[key], str) and arguments[key].strip() for key in ("key", "value")):
        raise ValueError("'key' and 'value' must be non-empty strings.")
    if "category" in arguments and not isinstance(arguments["category"], str):
        raise ValueError("'category' must be text.")


def validate_delete(arguments):
    _require_only(arguments, {"key"})
    if not isinstance(arguments["key"], str) or not arguments["key"].strip():
        raise ValueError("'key' must be a non-empty string.")


def search(arguments):
    return {"memories": retrieve_memories(arguments["query"])}


def save(arguments):
    key = normalize_memory_key(arguments["key"])
    value = arguments["value"].strip()
    category = arguments.get("category")
    save_memory(key, value, category)
    return {"key": key, "value": value, "category": category}


def delete(arguments):
    return {"deleted": delete_memory(arguments["key"])}


def _require_only(arguments, expected_keys):
    if not isinstance(arguments, dict) or set(arguments) != expected_keys:
        raise ValueError(f"Expected arguments: {', '.join(sorted(expected_keys))}.")
