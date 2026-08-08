import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain import database
from brain.ai.memory_retrieval import retrieve_memories
from brain.commands import process
from brain.profile import get_name, set_name
from brain.tools.memory_tools import save as save_memory_tool


class MemoryIntelligenceTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_directory.name) / "isolated_data" / "memory.db"
        self.database_patch = patch.object(database, "DATABASE", self.database_path)
        self.database_patch.start()
        database.create_memory_table()

    def tearDown(self):
        self.database_patch.stop()
        self.temp_directory.cleanup()

    def test_key_normalization(self):
        self.assertEqual(database.normalize_memory_key(" Favourite   Game "), "favourite_game")
        self.assertEqual(database.normalize_memory_key("favourite-game"), "favourite_game")
        self.assertEqual(database.normalize_memory_key("FAVOURITE_GAME"), "favourite_game")

    def test_duplicate_prevention_and_update_behavior(self):
        database.save_memory("favourite_game", "Minecraft")
        original = database.get_memories()[0]
        database.save_memory(" Favourite Game ", "Valorant")
        memories = database.get_memories()

        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0]["key"], "favourite_game")
        self.assertEqual(memories[0]["value"], "Valorant")
        self.assertEqual(memories[0]["created_at"], original["created_at"])
        self.assertTrue(memories[0]["updated_at"])

    def test_categories_and_profile_category(self):
        database.save_memory("favourite game", "Minecraft", "preference")
        set_name("Jefin")
        categories = {memory["key"]: memory["category"] for memory in database.get_memories()}

        self.assertEqual(categories["favourite_game"], "preference")
        self.assertEqual(categories["user_name"], "profile")
        self.assertEqual(get_name(), "Jefin")

    def test_exact_keyword_ranking_and_limit(self):
        database.save_memory("favourite game", "Minecraft")
        database.save_memory("favourite colour", "blue")
        database.save_memory("game platform", "PC")

        self.assertEqual(database.search_memories("Favourite Game")[0]["value"], "Minecraft")
        results = database.search_memories("favourite game", limit=2)
        self.assertEqual([memory["key"] for memory in results], ["favourite_game"])
        self.assertEqual(len(database.search_memories("game", limit=1)), 1)

    def test_empty_and_nonexistent_search(self):
        self.assertEqual(database.search_memories(""), [])
        self.assertEqual(database.search_memories("not stored"), [])

    def test_safe_deletion(self):
        database.save_memory("favourite game", "Minecraft")
        database.save_memory("favourite colour", "blue")

        self.assertTrue(database.delete_memory(" Favourite-Game "))
        self.assertIsNone(database.get_memory("favourite game"))
        self.assertEqual(database.get_memory("favourite colour"), "blue")

    def test_conflict_detection(self):
        self._create_legacy_database(
            [("favourite game", "Minecraft"), ("favourite_game", "Valorant")]
        )

        database.create_memory_table()

        conflicts = database.get_memory_conflicts()
        self.assertEqual(len(conflicts), 2)
        self.assertFalse(database.delete_memory("favourite game"))
        with self.assertRaises(database.MemoryConflictError):
            database.save_memory("favourite game", "Chess")

    def test_legacy_migration_and_persistence(self):
        self._create_legacy_database([(" Favourite Game ", "Minecraft")])

        database.create_memory_table()
        first_memory = database.get_memories()[0]
        database.create_memory_table()
        migrated_memory = database.get_memories()[0]

        self.assertEqual(first_memory["key"], "favourite_game")
        self.assertEqual(first_memory["value"], "Minecraft")
        self.assertTrue(first_memory["created_at"])
        self.assertTrue(first_memory["updated_at"])
        self.assertEqual(migrated_memory["value"], "Minecraft")

    def test_memory_tool_and_retrieval_integration(self):
        result = save_memory_tool(
            {"key": "Favourite Game", "value": "Minecraft", "category": "preference"}
        )

        self.assertEqual(result["key"], "favourite_game")
        self.assertEqual(retrieve_memories("favourite game")[0]["value"], "Minecraft")

    def test_existing_command_regression(self):
        self.assertEqual(
            process("remember my favourite game is Minecraft"),
            "Okay! I'll remember that your favourite game is Minecraft.",
        )
        self.assertEqual(process("what is my favourite game"), "Your favourite game is Minecraft.")
        self.assertEqual(process("forget my favourite game"), "Forgot your favourite game.")

    def _create_legacy_database(self, rows):
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        if self.database_path.exists():
            self.database_path.unlink()
        connection = sqlite3.connect(self.database_path)
        try:
            connection.execute(
                """
                CREATE TABLE memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE,
                    value TEXT
                )
                """
            )
            connection.executemany("INSERT INTO memory (key, value) VALUES (?, ?)", rows)
            connection.commit()
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
