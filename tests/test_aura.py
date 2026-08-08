import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from brain import database
from brain.commands import process
from brain.profile import (
    get_age,
    get_birthday,
    get_location,
    get_name,
    set_age,
    set_birthday,
    set_location,
    set_name,
)
from brain.time_utils import get_date, get_day, get_time


class AuraTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_directory.name) / "isolated_data" / "memory.db"
        self.database_patch = patch.object(database, "DATABASE", self.database_path)
        self.database_patch.start()
        database.create_memory_table()

    def tearDown(self):
        self.database_patch.stop()
        self.temp_directory.cleanup()

    def test_database_table_creation(self):
        connection = database.connect()
        try:
            table = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'memory'"
            ).fetchone()
        finally:
            connection.close()

        self.assertEqual(table[0], "memory")

    def test_save_and_retrieve_memory(self):
        database.save_memory("favourite game", "valorant")

        self.assertEqual(database.get_memory("favourite game"), "valorant")
        self.assertIsNone(database.get_memory("unknown key"))

    def test_profile_name(self):
        set_name("Jefin")
        self.assertEqual(get_name(), "Jefin")

    def test_profile_age(self):
        set_age("19")
        self.assertEqual(get_age(), "19")

    def test_profile_location(self):
        set_location("Kollam")
        self.assertEqual(get_location(), "Kollam")

    def test_profile_birthday(self):
        set_birthday("16 July")
        self.assertEqual(get_birthday(), "16 July")

    def test_time_utility(self):
        self.assertRegex(get_time(), r"^\d{2}:\d{2} (AM|PM)$")

    def test_date_utility(self):
        self.assertEqual(get_date(), datetime.now().strftime("%d %B %Y"))

    def test_day_utility(self):
        self.assertEqual(get_day(), datetime.now().strftime("%A"))

    def test_important_command_routing(self):
        self.assertIn("Artificial Universal Responsive Assistant", process("who are you"))
        self.assertEqual(process("unknown command"), "Sorry, I don't understand that command yet.")

        self.assertEqual(process("my name is Jefin"), "Nice to meet you, Jefin!")
        self.assertEqual(process("what is my name"), "Your name is Jefin.")

        self.assertEqual(
            process("remember my favourite game is Minecraft"),
            "Okay! I'll remember that your favourite game is Minecraft.",
        )
        self.assertEqual(
            process("what is my favourite game"),
            "Your favourite game is Minecraft.",
        )


if __name__ == "__main__":
    unittest.main()
