import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain import database
from brain.ai.orchestrator import MAX_TOOL_CALLS, run
from brain.ai.schemas import ModelAdapter
from brain.ai.tool_registry import build_default_registry
from brain.permissions import PermissionLevel, PermissionPolicy
from brain.notes import get_notes
from tests.fake_model_adapter import (
    FakeModelAdapter,
    LoopingFakeModelAdapter,
    ScenarioFakeModelAdapter,
)


class SimulatedAiBrainTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_directory.name) / "isolated_data" / "memory.db"
        self.database_patch = patch.object(database, "DATABASE", self.database_path)
        self.database_patch.start()
        database.create_memory_table()
        self.registry = build_default_registry()

    def tearDown(self):
        self.database_patch.stop()
        self.temp_directory.cleanup()

    def test_fake_adapter_matches_model_adapter_interface(self):
        self.assertIsInstance(FakeModelAdapter("Hello!"), ModelAdapter)

    def test_normal_text_response_does_not_call_a_tool(self):
        adapter = ScenarioFakeModelAdapter()

        self.assertEqual(run("Hello", adapter, self.registry), "Hello!")
        self.assertEqual(adapter.tool_calls, [])

    def test_memory_tool_flow(self):
        database.save_memory("favourite_game", "Minecraft", "preference")
        adapter = ScenarioFakeModelAdapter()

        response = run("What is my favourite game?", adapter, self.registry)

        self.assertEqual(response, "Your favourite game is Minecraft.")
        self.assertEqual(adapter.tool_calls, ["memory.search"])

    def test_calculator_tool_flow(self):
        adapter = ScenarioFakeModelAdapter()

        self.assertEqual(run("What is 827 * 91?", adapter, self.registry), "827 * 91 is 75257.")
        self.assertEqual(adapter.tool_calls, ["calculator.evaluate"])

    def test_notes_tool_flow(self):
        adapter = ScenarioFakeModelAdapter()

        response = run("Remember that I need to study tomorrow.", adapter, self.registry)

        self.assertEqual(response, "I've saved your note: I need to study tomorrow.")
        self.assertEqual(get_notes()[0]["content"], "I need to study tomorrow.")
        self.assertEqual(adapter.tool_calls, ["notes.create"])

    def test_time_tool_flow(self):
        adapter = ScenarioFakeModelAdapter()

        response = run("What time is it?", adapter, self.registry)

        self.assertRegex(response, r"The current time is \d{2}:\d{2} (AM|PM)\.")
        self.assertEqual(adapter.tool_calls, ["time.current"])

    def test_structured_tool_result_is_returned_to_adapter(self):
        adapter = FakeModelAdapter(
            responses=[
                {"tool": "calculator.evaluate", "arguments": {"expression": "2 + 2"}},
                "Done.",
            ]
        )

        self.assertEqual(run("calculate", adapter, self.registry), "Done.")
        tool_message = adapter.messages[1][-1]
        self.assertEqual(tool_message["role"], "tool")
        self.assertEqual(
            tool_message["content"],
            {"success": True, "tool": "calculator.evaluate", "result": {"result": 4}},
        )

    def test_unknown_malformed_and_invalid_requests_are_rejected(self):
        unknown = run(
            "unknown",
            FakeModelAdapter({"tool": "python.execute", "arguments": {}}),
            self.registry,
        )
        malformed = run(
            "malformed",
            FakeModelAdapter({"tool": "calculator.evaluate"}),
            self.registry,
        )
        invalid_arguments = run(
            "invalid",
            FakeModelAdapter({"tool": "calculator.evaluate", "arguments": {"expression": 2}}),
            self.registry,
        )

        self.assertFalse(unknown["success"])
        self.assertIn("Unknown tool", unknown["error"])
        self.assertFalse(malformed["success"])
        self.assertFalse(invalid_arguments["success"])

    def test_write_and_delete_permissions_are_enforced(self):
        read_only = PermissionPolicy({PermissionLevel.READ})
        write_denied = run(
            "write",
            FakeModelAdapter({"tool": "notes.create", "arguments": {"content": "Blocked"}}),
            self.registry,
            read_only,
        )
        delete_denied = run(
            "delete",
            FakeModelAdapter({"tool": "notes.delete", "arguments": {"note_id": 1}}),
            self.registry,
            PermissionPolicy({PermissionLevel.READ, PermissionLevel.WRITE}),
        )

        self.assertEqual(write_denied["error"], "Permission denied for tool: notes.create.")
        self.assertEqual(delete_denied["error"], "Permission denied for tool: notes.delete.")

    def test_tool_call_limit(self):
        response = run(
            "loop",
            LoopingFakeModelAdapter(),
            self.registry,
            max_tool_calls=MAX_TOOL_CALLS,
        )

        self.assertEqual(
            response,
            {"success": False, "tool": None, "error": "Tool-call limit reached."},
        )


if __name__ == "__main__":
    unittest.main()
