import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain import database
from brain.commands import CHANGELOG_TEXT, HELP_TEXT, process
from brain.fun import JOKES, MOTIVATION


class CoreReleaseTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_directory.name) / "isolated_data" / "memory.db"
        self.database_patch = patch.object(database, "DATABASE", self.database_path)
        self.database_patch.start()
        database.create_memory_table()

    def tearDown(self):
        self.database_patch.stop()
        self.temp_directory.cleanup()

    def test_list_memories(self):
        database.save_memory("favourite game", "Minecraft")

        response = process("show my memories")

        self.assertIn("Your memories:", response)
        self.assertIn("favourite game: Minecraft", response)

    def test_delete_memory(self):
        database.save_memory("user_favourite game", "Minecraft")

        self.assertEqual(process("forget my favourite game"), "Forgot your favourite game.")
        self.assertIsNone(database.get_memory("user_favourite game"))

    def test_nonexistent_memory(self):
        self.assertEqual(process("forget my favourite game"), "I couldn't find that memory.")

    def test_empty_memory_state(self):
        self.assertEqual(process("list my memories"), "You don't have any memories yet.")

    def test_joke_commands(self):
        self.assertIn(process("tell me a joke"), JOKES)
        self.assertIn(process("joke"), JOKES)

    def test_quote_and_motivation_commands(self):
        self.assertIn(process("give me a quote"), MOTIVATION)
        self.assertIn(process("motivate me"), MOTIVATION)
        self.assertIn(process("give me motivation"), MOTIVATION)

    def test_help_commands(self):
        for command in ("help", "what can you do", "show commands"):
            response = process(command)
            self.assertEqual(response, HELP_TEXT)
            for category in (
                "Basic",
                "Memory",
                "Profile",
                "Time & Date",
                "Calculator",
                "Notes",
                "Fun",
            ):
                self.assertIn(category, response)

    def test_changelog_commands(self):
        for command in ("what's new", "whats new", "changelog"):
            self.assertEqual(process(command), CHANGELOG_TEXT)

    def test_existing_feature_regression(self):
        self.assertEqual(process("my name is Jefin"), "Nice to meet you, Jefin!")
        self.assertEqual(process("i am 19"), "Got it! You are 19 years old.")
        self.assertEqual(process("i live in Kollam"), "I'll remember that you live in Kollam.")
        self.assertEqual(
            process("my birthday is 16 July"),
            "I'll remember your birthday is 16 July.",
        )
        self.assertEqual(process("what is my name"), "Your name is Jefin.")
        self.assertEqual(process("how old am i"), "You are 19 years old.")
        self.assertEqual(process("where do i live"), "You live in Kollam.")
        self.assertEqual(process("when is my birthday"), "Your birthday is 16 July.")
        self.assertEqual(process("remember colour is blue"), "Okay! I'll remember that colour is blue.")
        self.assertEqual(process("what is colour"), "colour is blue.")
        self.assertEqual(process("2 + 2"), "The result is 4.")
        self.assertEqual(process("note Check tests"), "Note 1 saved.")
        self.assertEqual(process("show my note"), "Your notes:\n1. Check tests")
        self.assertRegex(process("time"), r"The current time is \d{2}:\d{2} (AM|PM)\.")
        self.assertRegex(process("date"), r"Today's date is \d{2} .+ \d{4}\.")
        self.assertRegex(process("day"), r"Today is .+\.")


if __name__ == "__main__":
    unittest.main()
