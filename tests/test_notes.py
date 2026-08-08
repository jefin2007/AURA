import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain import database
from brain.commands import process
from brain.notes import create_note, create_notes_table, delete_note, get_note, get_notes


class NotesTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_directory.name) / "isolated_data" / "memory.db"
        self.database_patch = patch.object(database, "DATABASE", self.database_path)
        self.database_patch.start()

    def tearDown(self):
        self.database_patch.stop()
        self.temp_directory.cleanup()

    def test_creating_a_note(self):
        note = create_note("Finish Aura v0.1.0")

        self.assertEqual(note["id"], 1)
        self.assertEqual(note["content"], "Finish Aura v0.1.0")
        self.assertTrue(note["created_at"])

    def test_retrieving_notes(self):
        create_note("First note")

        notes = get_notes()

        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]["content"], "First note")

    def test_retrieving_a_specific_note(self):
        created_note = create_note("Read me")

        self.assertEqual(get_note(created_note["id"]), created_note)

    def test_deleting_a_note(self):
        note = create_note("Delete me")

        self.assertTrue(delete_note(note["id"]))
        self.assertIsNone(get_note(note["id"]))

    def test_multiple_notes(self):
        create_note("First")
        create_note("Second")

        self.assertEqual([note["content"] for note in get_notes()], ["First", "Second"])

    def test_empty_note_rejection(self):
        self.assertIsNone(create_note("   "))
        self.assertEqual(get_notes(), [])

    def test_invalid_note_id(self):
        self.assertIsNone(get_note("not-an-id"))
        self.assertFalse(delete_note("0"))

    def test_nonexistent_note(self):
        self.assertIsNone(get_note(99))
        self.assertFalse(delete_note(99))

    def test_persistence_behavior(self):
        note = create_note("Saved between connections")

        create_notes_table()

        self.assertEqual(get_note(note["id"])["content"], "Saved between connections")

    def test_command_routing(self):
        self.assertEqual(process("take a note Finish Aura v0.1.0"), "Note 1 saved.")
        self.assertEqual(process("show my notes"), "Your notes:\n1. Finish Aura v0.1.0")
        self.assertEqual(process("read note 1"), "Note 1: Finish Aura v0.1.0")
        self.assertEqual(process("delete note 1"), "Deleted note 1.")
        self.assertEqual(process("list my notes"), "You don't have any notes yet.")
        self.assertEqual(process("note   "), "A note cannot be empty.")
        self.assertEqual(process("read note abc"), "Please provide a valid note ID.")


if __name__ == "__main__":
    unittest.main()
