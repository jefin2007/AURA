"""Offline unit tests for the Gemini adapter; no API key or network is required."""

import os
import unittest
from unittest.mock import patch

from brain.ai.schemas import ToolRequest, parse_tool_request
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
    def test_parse_tool_request_preserves_call_id(self):
        req = ToolRequest(tool="test.tool", arguments={"a": 1}, call_id="call-abc")
        parsed = parse_tool_request(req)
        self.assertEqual(parsed.call_id, "call-abc")

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
        # In the fake test fallback code (dictionary path), id is inside function_response
        self.assertEqual(response_part["id"], "call-1")
        self.assertEqual(response_part["response"], {"output": {"success": True, "result": {"result": 4}}})
        # Verify role is user in dictionary fallback
        self.assertEqual(client.models.calls[1]["contents"][-1]["role"], "user")

    def test_model_content_preserves_sdk_response(self):
        class MockCandidate:
            def __init__(self):
                self.content = "SDK_CONTENT"

        class MockResponse:
            def __init__(self):
                self.candidates = [MockCandidate()]

        res = GeminiAdapter._model_content(MockResponse(), "tool", {}, "call-1")
        self.assertEqual(res, "SDK_CONTENT")

    def test_model_content_preserves_sdk_response(self):
        class MockCandidate:
            def __init__(self):
                self.content = "SDK_CONTENT"

        class MockResponse:
            def __init__(self):
                self.candidates = [MockCandidate()]

        res = GeminiAdapter._model_content(MockResponse(), "tool", {}, "call-1")
        self.assertEqual(res, "SDK_CONTENT")

    def test_function_call_pending_contents_are_plain_dictionaries(self):
        # We simulate the _value function retrieving an object when asked for "content", which we will bypass
        # to ensure plain dictionary construction in _model_content.
        client = FakeClient([
            {"function_calls": [{"name": "calculator.evaluate", "args": {"expression": "2 + 2"}, "id": "call-1"}]},
        ])
        adapter = GeminiAdapter(client=client)
        adapter.respond([{"role": "user", "content": "Calculate"}], TOOLS)
        self.assertIsInstance(adapter._pending_contents[-1], dict)
        self.assertIn("role", adapter._pending_contents[-1])
        self.assertIn("parts", adapter._pending_contents[-1])
        self.assertEqual(adapter._pending_contents[-1]["role"], "model")

    def test_tool_result_to_gemini_uses_function_response_with_id(self):
        # We need to simulate the environment where self._types is real, but client might be a mock,
        # or we just instantiate a real adapter to test the structure logic, since tool_result_to_gemini is pure.
        with patch.dict(os.environ, {"GEMINI_API_KEY": "FAKE"}):
            adapter = GeminiAdapter()
        tool_result = {"success": True, "tool": "test", "call_id": "call-1", "result": 4}
        content = adapter.tool_result_to_gemini(tool_result)
        # Content object is returned
        self.assertEqual(content.role, "user")
        self.assertEqual(len(content.parts), 1)
        self.assertIsNotNone(content.parts[0].function_response)
        self.assertEqual(content.parts[0].function_response.id, "call-1")
        self.assertEqual(content.parts[0].function_response.name, "test")
        self.assertEqual(content.parts[0].function_response.response, {"output": {"success": True, "result": 4}})

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
    def test_live_tool_calling_integration(self):
        adapter = GeminiAdapter()
        registry = build_default_registry()
        result = run("What is 12345 + 54321? Use the calculator tool.", adapter, registry)
        self.assertIn("66666", result.get("response", ""))

    def test_live_text_response(self):
        adapter = GeminiAdapter()
        response = adapter.respond([{"role": "user", "content": "Reply with hello."}], [])
        self.assertIsInstance(response, str)


if __name__ == "__main__":
    unittest.main()
