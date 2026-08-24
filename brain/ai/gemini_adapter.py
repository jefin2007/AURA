"""Google Gemini implementation of AURA's controlled ModelAdapter interface."""

import os

from brain.ai.prompts import AURA_SYSTEM_INSTRUCTION
from brain.ai.schemas import ToolRequest


GEMINI_MODEL = "gemini-3.6-flash"
MAX_HISTORY_MESSAGES = 12


class GeminiUnavailableError(RuntimeError):
    """Raised when Gemini cannot be used without revealing provider internals."""


class GeminiAdapter:
    """Translate Gemini responses into requests; never execute tools directly."""

    def __init__(self, client=None, api_key=None, model=GEMINI_MODEL, history_limit=MAX_HISTORY_MESSAGES):
        self.model = model
        self.history_limit = history_limit
        self._history = []
        self._pending_contents = None
        self._client = client
        self._types = None
        if client is None:
            api_key = api_key if api_key is not None else os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise GeminiUnavailableError("AI brain is unavailable. Deterministic commands are still working.")
            try:
                from google import genai
            except ImportError as error:
                raise GeminiUnavailableError("AI brain is unavailable. Deterministic commands are still working.") from error
            self._client = genai.Client(api_key=api_key)
            self._types = genai.types

    @property
    def available(self):
        return self._client is not None

    def respond(self, messages, tools):
        """Send bounded conversation state and translate text or function calls."""
        if not messages:
            raise GeminiUnavailableError("AI brain is unavailable right now. Please try again later.")
        last_message = messages[-1]
        if last_message.get("role") == "user":
            contents = list(self._history) + [{"role": "user", "parts": [{"text": last_message.get("content", "")}]}]
        elif last_message.get("role") == "tool" and self._pending_contents is not None:
            contents = self._pending_contents + [self.tool_result_to_gemini(last_message["content"])]
        else:
            raise GeminiUnavailableError("AI brain is unavailable right now. Please try again later.")

        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=contents,
                config=self._provider_config(tools),
            )
        except Exception as error:
            raise GeminiUnavailableError("AI brain is unavailable right now. Please try again later.") from error

        function_call = self._function_call(response)
        if function_call is not None:
            name, arguments, call_id = function_call
            if not isinstance(name, str) or not name or not isinstance(arguments, dict):
                raise GeminiUnavailableError("AI brain returned an invalid tool request.")
            self._pending_contents = contents + [self._model_content(response, name, arguments, call_id)]
            return ToolRequest(name, arguments, call_id)

        text = self._response_text(response)
        if not text:
            raise GeminiUnavailableError("AI brain returned an invalid response.")
        self._history = (contents + [{"role": "model", "parts": [{"text": text}]}])[-self.history_limit:]
        self._pending_contents = None
        return text

    @staticmethod
    def tool_declarations(tools):
        """Convert allowlisted registry descriptions into Gemini declarations."""
        return [
            {"name": tool["name"], "description": tool["description"], "parameters": tool.get("parameters") or {"type": "object", "properties": {}}}
            for tool in tools
        ]

    def _provider_config(self, tools):
        declarations = self.tool_declarations(tools)
        if self._types is None:
            return {"system_instruction": AURA_SYSTEM_INSTRUCTION, "tools": [{"function_declarations": declarations}]}
        functions = [
            self._types.FunctionDeclaration(
                name=declaration["name"],
                description=declaration["description"],
                parameters_json_schema=declaration["parameters"],
            )
            for declaration in declarations
        ]
        return self._types.GenerateContentConfig(
            system_instruction=AURA_SYSTEM_INSTRUCTION,
            tools=[self._types.Tool(function_declarations=functions)],
        )

    @staticmethod
    def tool_result_to_gemini(tool_result):
        """Translate only serializable controlled results to a function response."""
        payload = {"success": bool(tool_result.get("success"))}
        if payload["success"]:
            payload["result"] = tool_result.get("result")
            response = {"output": payload}
        else:
            payload["error"] = tool_result.get("error", "Tool request failed.")
            response = {"error": payload}
        part = {"function_response": {"name": tool_result.get("tool") or "unknown", "response": response}}
        if tool_result.get("call_id"):
            part["function_response"]["id"] = tool_result["call_id"]
        return {"role": "tool", "parts": [part]}

    @staticmethod
    def _function_call(response):
        calls = _value(response, "function_calls") or []
        if calls:
            return _call_values(calls[0])
        for candidate in _value(response, "candidates") or []:
            for part in _value(_value(candidate, "content"), "parts") or []:
                call = _value(part, "function_call")
                if call is not None:
                    return _call_values(call)
        return None

    @staticmethod
    def _response_text(response):
        text = _value(response, "text")
        if isinstance(text, str):
            return text.strip()
        for candidate in _value(response, "candidates") or []:
            for part in _value(_value(candidate, "content"), "parts") or []:
                text = _value(part, "text")
                if isinstance(text, str) and text.strip():
                    return text.strip()
        return ""

    @staticmethod
    def _model_content(response, name, arguments, call_id):
        call = {"name": name, "args": arguments}
        if call_id:
            call["id"] = call_id
        return {"role": "model", "parts": [{"function_call": call}]}


def _value(item, name):
    if isinstance(item, dict):
        return item.get(name)
    return getattr(item, name, None)


def _call_values(call):
    name = _value(call, "name")
    arguments = _value(call, "args")
    if arguments is None:
        arguments = _value(call, "arguments")
    try:
        arguments = dict(arguments)
    except (TypeError, ValueError):
        arguments = None
    return name, arguments, _value(call, "id")
