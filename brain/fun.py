"""Built-in, offline fun responses for AURA."""

import random


JOKES = (
    "Why did the computer go to the doctor? Because it caught a virus.",
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "What do you call a helpful AI? A byte-sized friend.",
)

MOTIVATION = (
    "Small, consistent steps can build remarkable progress.",
    "Start with the next useful step; momentum follows action.",
    "Progress is still progress, even when it is quiet.",
)


def get_joke():
    """Return one clean built-in joke."""
    return random.choice(JOKES)


def get_motivation():
    """Return one built-in motivational message."""
    return random.choice(MOTIVATION)
