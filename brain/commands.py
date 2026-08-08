import config
from brain.database import MemoryConflictError, delete_memory, get_memories, get_memory, save_memory
from brain.fun import get_joke, get_motivation
from brain.profile import (
    set_name,
    get_name,
    set_age,
    get_age,
    set_location,
    get_location,
    set_birthday,
    get_birthday,
)
from brain.time_utils import get_time, get_date, get_day
from brain.calculator import calculate, is_calculation_expression
from brain.notes import create_note, delete_note, get_note, get_notes, is_valid_note_id


HELP_TEXT = (
    "Available commands:\n"
    "Basic: who are you, what is your name, what is your version, hello\n"
    "Memory: remember <key> is <value>, show my memories, forget <key>\n"
    "Profile: my name is, i am, i live in, my birthday is\n"
    "Time & Date: time, date, day\n"
    "Calculator: calculate <expression> or enter an expression\n"
    "Notes: take a note <text>, show my notes, read note <id>, delete note <id>\n"
    "Fun: tell me a joke, give me a quote, motivate me"
)

CHANGELOG_TEXT = (
    "AURA v0.1.0: first core release with memory management, notes, "
    "safe calculations, time and profile tools, plus built-in jokes, motivation, and help."
)


def _display_memory_key(key):
    if key.startswith("user_"):
        return "your " + key[5:].replace("_", " ")
    return key.replace("_", " ")


UNKNOWN_COMMAND = object()


def process(command, unknown_response="Sorry, I don't understand that command yet."):

    original = command.strip()
    command = original.lower()

    # ----------------------------
    # Basic Commands
    # ----------------------------
    if command in ["help", "what can you do", "show commands"]:
        return HELP_TEXT

    elif command in ["what's new", "whats new", "changelog"]:
        return CHANGELOG_TEXT

    elif command in ["tell me a joke", "joke"]:
        return get_joke()

    elif command in ["give me a quote", "motivate me", "give me motivation"]:
        return get_motivation()

    elif command == "who are you":
        return (
            f"I am {config.FULL_NAME}.\n"
            f"My creator is {config.OWNER}."
        )

    elif command == "what is your name":
        return f"My name is {config.AI_NAME}."

    elif command == "what is your version":
        return f"I am currently running Version {config.VERSION}."

    elif command == "hello":
        return f"Hello {config.OWNER}! Nice to see you."

    # ----------------------------
    # Time & Date
    # ----------------------------
    elif command in ["what time is it", "time"]:
        return f"The current time is {get_time()}."

    elif command in ["what is today's date", "what is the date", "date"]:
        return f"Today's date is {get_date()}."

    elif command in ["what day is today", "day"]:
        return f"Today is {get_day()}."

    # ----------------------------
    # Calculator
    # ----------------------------
    elif command == "calculate" or command.startswith("calculate "):
        return calculate(original[9:].strip())

    elif command.startswith("calculate:"):
        return calculate(original[10:].strip())

    # ----------------------------
    # Notes
    # ----------------------------
    elif command == "take a note" or command.startswith("take a note "):
        note = create_note(original[11:].strip())
        if note:
            return f"Note {note['id']} saved."
        return "A note cannot be empty."

    elif command == "note" or command.startswith("note "):
        note = create_note(original[4:].strip())
        if note:
            return f"Note {note['id']} saved."
        return "A note cannot be empty."

    elif command in ["show my note", "show my notes", "list my note", "list my notes"]:
        notes = get_notes()
        if not notes:
            return "You don't have any notes yet."
        return "Your notes:\n" + "\n".join(
            f"{note['id']}. {note['content']}" for note in notes
        )

    elif command == "read note" or command.startswith("read note "):
        note_id = original[9:].strip()
        if not is_valid_note_id(note_id):
            return "Please provide a valid note ID."
        note = get_note(note_id)
        if note:
            return f"Note {note['id']}: {note['content']}"
        return f"I couldn't find note {note_id}."

    elif command == "delete note" or command.startswith("delete note "):
        note_id = original[11:].strip()
        if not is_valid_note_id(note_id):
            return "Please provide a valid note ID."
        if delete_note(note_id):
            return f"Deleted note {note_id}."
        return f"I couldn't find note {note_id}."

    # ----------------------------
    # Profile Commands
    # ----------------------------
    elif command.startswith("my name is "):
        name = original[11:].strip()
        set_name(name)
        return f"Nice to meet you, {name}!"

    elif command == "what is my name":
        name = get_name()
        if name:
            return f"Your name is {name}."
        return "I don't know your name yet."

    elif command.startswith("i am "):
        age = original[5:].strip()
        if age.isdigit():
            set_age(age)
            return f"Got it! You are {age} years old."
        return "Please tell me your age as a number."

    elif command == "how old am i":
        age = get_age()
        if age:
            return f"You are {age} years old."
        return "I don't know your age yet."

    elif command.startswith("i live in "):
        location = original[10:].strip()
        set_location(location)
        return f"I'll remember that you live in {location}."

    elif command == "where do i live":
        location = get_location()
        if location:
            return f"You live in {location}."
        return "I don't know where you live yet."

    elif command.startswith("my birthday is "):
        birthday = original[15:].strip()
        set_birthday(birthday)
        return f"I'll remember your birthday is {birthday}."

    elif command == "when is my birthday":
        birthday = get_birthday()
        if birthday:
            return f"Your birthday is {birthday}."
        return "I don't know your birthday yet."

    # ----------------------------
    # Generic Remember Command
    # ----------------------------
    elif command in ["show my memories", "list my memories"]:
        memories = get_memories()
        if not memories:
            return "You don't have any memories yet."
        return "Your memories:\n" + "\n".join(
            f"- {_display_memory_key(memory['key'])}: {memory['value']}"
            for memory in memories
        )

    elif command == "forget" or command == "forget my":
        return "Please provide a memory to forget."

    elif command.startswith("forget my "):
        key = "user_" + command[10:].strip()
        if delete_memory(key):
            return f"Forgot your {key[5:]}."
        return "I couldn't find that memory."

    elif command.startswith("forget "):
        key = command[7:].strip()
        if delete_memory(key):
            return f"Forgot {key}."
        return "I couldn't find that memory."

    elif command.startswith("remember "):
        text = original[9:].strip()

        if " is " in text.lower():
            index = text.lower().find(" is ")

            key = text[:index].strip().lower()
            value = text[index + 4:].strip()

            if key.startswith("my "):
                key = "user_" + key[3:]

            try:
                save_memory(key, value)
            except MemoryConflictError:
                return "I found conflicting memories for that key. Please inspect them before updating."

            return f"Okay! I'll remember that {key.replace('user_', 'your ')} is {value}."

        return "Please use: remember <something> is <value>"

    # ----------------------------
    # Generic Natural Memory
    # ----------------------------
    elif command.startswith("my ") and " is " in command:

        index = command.find(" is ")

        key = command[:index].strip()[3:]
        value = original[index + 4:].strip()

        try:
            save_memory("user_" + key, value)
        except MemoryConflictError:
            return "I found conflicting memories for that key. Please inspect them before updating."

        return f"Got it! I'll remember your {key}."

    # ----------------------------
    # Recall Generic Memory
    # ----------------------------
    elif command.startswith("what is ") and is_calculation_expression(command[8:]):
        return calculate(original[8:].strip())

    elif is_calculation_expression(command):
        return calculate(original)

    elif command.startswith("what is "):

        key = command[8:].strip()

        if key.startswith("my "):
            key = "user_" + key[3:]

        value = get_memory(key)

        if value:
            return f"{key.replace('user_', 'Your ')} is {value}."

        return "I don't know that yet."

    # ----------------------------
    # Unknown Command
    # ----------------------------
    else:
        return unknown_response


def process_deterministic(command):
    """Return a response only for a recognized offline command."""
    return process(command, unknown_response=UNKNOWN_COMMAND)
