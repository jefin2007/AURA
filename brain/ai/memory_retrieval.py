"""Focused retrieval of relevant memories for future AI tool use."""

from brain.database import search_memories


def retrieve_memories(query, limit=3):
    """Return exact or keyword-matching memories, never the full memory store."""
    return [
        {"key": _display_key(memory["key"]), "value": memory["value"]}
        for memory in search_memories(query, limit)
    ]


def _display_key(key):
    if key.startswith("user_"):
        return "user_" + key[5:].replace("_", " ")
    return key.replace("_", " ")
