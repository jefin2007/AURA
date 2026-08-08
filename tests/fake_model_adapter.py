"""Test-only adapters that simulate provider-independent model behavior."""

from brain.ai.schemas import ToolRequest


class FakeModelAdapter:
    """Return predefined text or tool requests in a controlled test sequence."""

    def __init__(self, response=None, responses=None):
        self.responses = list(responses) if responses is not None else [response]
        self.requests = []
        self.messages = []
        self.tools = []

    def respond(self, messages, tools):
        self.messages.append(messages)
        self.tools.append(tools)
        if messages[-1]["role"] == "user":
            self.requests.append(messages[-1]["content"])
        if self.responses:
            return self.responses.pop(0)
        return "Tool completed."


class ScenarioFakeModelAdapter:
    """Simulate realistic single-tool AURA conversations for integration tests."""

    def __init__(self):
        self.tool_calls = []

    def respond(self, messages, tools):
        last_message = messages[-1]
        if last_message["role"] == "tool":
            tool_result = last_message["content"]
            self.tool_calls.append(tool_result["tool"])
            return self._final_response(tool_result)

        user_request = last_message["content"]
        normalized = user_request.lower()
        if normalized == "what is my favourite game?":
            return ToolRequest("memory.search", {"query": "favourite game"})
        if normalized == "what is 827 * 91?":
            return ToolRequest("calculator.evaluate", {"expression": "827 * 91"})
        if normalized == "remember that i need to study tomorrow.":
            return ToolRequest("notes.create", {"content": "I need to study tomorrow."})
        if normalized == "what time is it?":
            return ToolRequest("time.current", {})
        if normalized == "hello":
            return "Hello!"
        return "I do not have a simulated response for that request."

    def _final_response(self, tool_result):
        result = tool_result["result"]
        if tool_result["tool"] == "memory.search":
            memories = result["memories"]
            if memories:
                return f"Your favourite game is {memories[0]['value']}."
            return "I do not know your favourite game yet."
        if tool_result["tool"] == "calculator.evaluate":
            return f"827 * 91 is {result['result']}."
        if tool_result["tool"] == "notes.create":
            return f"I've saved your note: {result['note']['content']}"
        if tool_result["tool"] == "time.current":
            return f"The current time is {result['time']}."
        return "Tool completed."


class LoopingFakeModelAdapter:
    """Continuously requests a safe registered tool to test loop limits."""

    def respond(self, messages, tools):
        return ToolRequest("time.current", {})
