"""Offline unit tests for the Gemini adapter; no API key or network is required."""

import os
import unittest
from unittest.mock import patch

from brain.ai.gemini_adapter import GEMINI_MODEL, GeminiAdapter, GeminiUnavailableError
from brain.ai.orchestrator import run
from brain.ai.tool_registry import build_default_registry
from brain.permissions import PermissionLevel, PermissionPolicy


class FakeModels:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeClient:
    def __init__(self, responses):
        self.models = FakeModels(responses)


TOOLS = [{"name": "calculator.evaluate", "description": "Calculate.", "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}}}]


class GeminiAdapterTestCase(unittest.TestCase):
    def test_missing_key_does_not_initialize(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(GeminiUnavailableError):
                GeminiAdapter()

    def test_initialization_with_injected_client_uses_stable_model(self):
        adapter = GeminiAdapter(client=FakeClient([]))
        self.assertTrue(adapter.available)
        self.assertEqual(adapter.model, GEMINI_MODEL)

    def test_normal_text_response_and_declarations(self):
        client = FakeClient([{"text": "Hello from AURA."}])
        adapter = GeminiAdapter(client=client)
        self.assertEqual(adapter.respond([{"role": "user", "content": "Hello"}], TOOLS), "Hello from AURA.")
        self.assertEqual(client.models.calls[0]["config"]["tools"][0]["function_declarations"][0]["name"], "calculator.evaluate")

    def test_function_call_converts_to_tool_request_and_result(self):
        client = FakeClient([
            {"function_calls": [{"name": "calculator.evaluate", "args": {"expression": "2 + 2"}, "id": "call-1"}]},
            {"text": "The result is 4."},
        ])
        adapter = GeminiAdapter(client=client)
        request = adapter.respond([{"role": "user", "content": "Calculate"}], TOOLS)
        self.assertEqual(request.tool, "calculator.evaluate")
        self.assertEqual(request.arguments, {"expression": "2 + 2"})
        self.assertEqual(request.call_id, "call-1")
        self.assertEqual(adapter.respond([{"role": "tool", "content": {"success": True, "tool": request.tool, "call_id": request.call_id, "result": {"result": 4}}}], TOOLS), "The result is 4.")
        response_part = client.models.calls[1]["contents"][-1]["parts"][0]["function_response"]
        self.assertEqual(response_part["id"], "call-1")
        self.assertEqual(response_part["response"], {"output": {"success": True, "result": {"result": 4}}})

    def test_malformed_function_call_is_rejected(self):
        adapter = GeminiAdapter(client=FakeClient([{"function_calls": [{"name": "calculator.evaluate", "args": "bad"}]}]))
        with self.assertRaises(GeminiUnavailableError):
            adapter.respond([{"role": "user", "content": "Calculate"}], TOOLS)

    def test_unknown_function_is_passed_to_registry_for_rejection(self):
        adapter = GeminiAdapter(client=FakeClient([{"function_calls": [{"name": "python.execute", "args": {}}]}]))
        result = run("Do it", adapter, build_default_registry())
        self.assertFalse(result["success"])
        self.assertIn("Unknown tool", result["error"])

    def test_api_errors_are_sanitized(self):
        adapter = GeminiAdapter(client=FakeClient([RuntimeError("credential details")]))
        with self.assertRaisesRegex(GeminiUnavailableError, "AI brain is unavailable right now"):
            adapter.respond([{"role": "user", "content": "Hello"}], TOOLS)

    def test_permission_error_remains_controlled(self):
        adapter = GeminiAdapter(client=FakeClient([{"function_calls": [{"name": "notes.create", "args": {"content": "Blocked"}}]}]))
        result = run("Save", adapter, build_default_registry(), PermissionPolicy({PermissionLevel.READ}))
        self.assertEqual(result["error"], "Permission denied for tool: notes.create.")


@unittest.skipUnless(os.getenv("AURA_LIVE_GEMINI_TEST") == "1", "Set AURA_LIVE_GEMINI_TEST=1 to run live Gemini test.")
class LiveGeminiIntegrationTestCase(unittest.TestCase):
    def test_live_text_response(self):
        adapter = GeminiAdapter()
        response = adapter.respond([{"role": "user", "content": "Reply with hello."}], [])
        self.assertIsInstance(response, str)


if __name__ == "__main__":
    unittest.main()
