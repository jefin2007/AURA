import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain import database
from brain.ai.memory_retrieval import retrieve_memories
from brain.ai.orchestrator import run
from brain.ai.schemas import ToolRequest, ToolRequestError, parse_tool_request
from brain.ai.tool_registry import RegisteredTool, ToolRegistry, build_default_registry
from brain.permissions import PermissionLevel, PermissionPolicy
from tests.fake_model_adapter import FakeModelAdapter


class ToolArchitectureTestCase(unittest.TestCase):
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

    def test_registry_registration_and_lookup(self):
        registry = ToolRegistry()
        tool = RegisteredTool(
            "test.echo",
            "Return a message.",
            lambda arguments: arguments,
            lambda arguments: None,
            PermissionLevel.READ,
        )
        registry.register(tool)
        self.assertIs(registry.get("test.echo"), tool)

    def test_unknown_tool_rejection(self):
        with self.assertRaises(ToolRequestError):
            self.registry.validate({"tool": "system.run", "arguments": {}})

    def test_parse_tool_request_preserves_call_id(self):
        request = ToolRequest(tool="memory.search", arguments={"query": "test"}, call_id="12345")
        parsed = parse_tool_request(request)
        self.assertEqual(parsed.call_id, "12345")
        self.assertEqual(parsed.tool, "memory.search")
        self.assertEqual(parsed.arguments, {"query": "test"})

    def test_malformed_request_rejection(self):
        with self.assertRaises(ToolRequestError):
            parse_tool_request({"tool": "calculator.evaluate"})
        with self.assertRaises(ToolRequestError):
            self.registry.validate(
                {"tool": "calculator.evaluate", "arguments": {"expression": 2}}
            )

    def test_permission_levels_and_denial(self):
        self.assertEqual(
            self.registry.get("calculator.evaluate").permission_level,
            PermissionLevel.READ,
        )
        self.assertEqual(
            self.registry.get("memory.save").permission_level,
            PermissionLevel.WRITE,
        )
        self.assertEqual(
            self.registry.get("notes.delete").permission_level,
            PermissionLevel.DELETE,
        )

        response = run(
            "save a memory",
            FakeModelAdapter({"tool": "memory.save", "arguments": {"key": "colour", "value": "blue"}}),
            self.registry,
            PermissionPolicy({PermissionLevel.READ}),
        )
        self.assertEqual(
            response,
            {
                "success": False,
                "tool": "memory.save",
                "error": "Permission denied for tool: memory.save.",
            },
        )

    def test_tool_wrappers(self):
        self.assertEqual(
            self.registry.execute({"tool": "calculator.evaluate", "arguments": {"expression": "2 + 2"}}),
            {"result": 4},
        )
        created = self.registry.execute(
            {"tool": "notes.create", "arguments": {"content": "Check wrappers"}}
        )
        note_id = created["note"]["id"]
        self.assertEqual(
            self.registry.execute({"tool": "notes.list", "arguments": {}})["notes"][0]["id"],
            note_id,
        )
        self.assertEqual(
            self.registry.execute({"tool": "notes.read", "arguments": {"note_id": note_id}})["note"]["content"],
            "Check wrappers",
        )
        self.assertEqual(
            self.registry.execute({"tool": "notes.delete", "arguments": {"note_id": note_id}}),
            {"deleted": True},
        )
        self.registry.execute(
            {"tool": "memory.save", "arguments": {"key": "favourite game", "value": "Minecraft"}}
        )
        self.assertEqual(
            self.registry.execute({"tool": "memory.search", "arguments": {"query": "favourite game"}}),
            {"memories": [{"key": "favourite game", "value": "Minecraft"}]},
        )
        self.assertEqual(
            self.registry.execute({"tool": "memory.delete", "arguments": {"key": "favourite game"}}),
            {"deleted": True},
        )
        self.assertIn("time", self.registry.execute({"tool": "time.current", "arguments": {}}))
        self.assertIn("date", self.registry.execute({"tool": "date.current", "arguments": {}}))
        self.assertIn("day", self.registry.execute({"tool": "day.current", "arguments": {}}))

    def test_orchestrator_text_and_tool_responses(self):
        text_adapter = FakeModelAdapter("Hello!")
        self.assertEqual(run("hello", text_adapter, self.registry), "Hello!")
        self.assertEqual(text_adapter.requests, ["hello"])

        tool_adapter = FakeModelAdapter(
            responses=[
                ToolRequest("calculator.evaluate", {"expression": "2 + 2"}),
                "The result is 4.",
            ]
        )
        self.assertEqual(
            run("calculate", tool_adapter, self.registry),
            "The result is 4.",
        )

    def test_orchestrator_invalid_and_unknown_requests(self):
        invalid = run("bad", FakeModelAdapter({"tool": "calculator.evaluate"}), self.registry)
        unknown = run(
            "unknown",
            FakeModelAdapter({"tool": "python.execute", "arguments": {}}),
            self.registry,
        )
        self.assertIn("Tool requests", invalid["error"])
        self.assertEqual(invalid["success"], False)
        self.assertEqual(
            unknown,
            {"success": False, "tool": "python.execute", "error": "Unknown tool: python.execute."},
        )

    def test_memory_retrieval(self):
        database.save_memory("user_favourite game", "Minecraft")
        database.save_memory("favourite colour", "blue")

        self.assertEqual(
            retrieve_memories("user_favourite game"),
            [{"key": "user_favourite game", "value": "Minecraft"}],
        )
        self.assertEqual(
            retrieve_memories("favourite"),
            [
                {"key": "favourite colour", "value": "blue"},
                {"key": "user_favourite game", "value": "Minecraft"},
            ],
        )
        self.assertEqual(retrieve_memories("unrelated"), [])


if __name__ == "__main__":
    unittest.main()
