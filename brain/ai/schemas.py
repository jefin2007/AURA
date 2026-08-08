"""Safe data structures exchanged between a future model and AURA tools."""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class ToolRequestError(ValueError):
    """Raised when a proposed tool request is malformed."""


@dataclass(frozen=True)
class ToolRequest:
    tool: str
    arguments: dict
    call_id: str | None = None


@dataclass(frozen=True)
class ToolResult:
    """Structured result returned from a registered tool execution."""

    success: bool
    tool: str | None
    result: dict | None = None
    error: str | None = None
    call_id: str | None = None

    def to_dict(self):
        response = {"success": self.success, "tool": self.tool}
        if self.call_id:
            response["call_id"] = self.call_id
        if self.success:
            response["result"] = self.result
        else:
            response["error"] = self.error
        return response


@runtime_checkable
class ModelAdapter(Protocol):
    """Provider-independent interface for future model adapters."""

    def respond(self, messages, tools):
        """Return text or a ToolRequest-compatible structure."""


def parse_tool_request(payload):
    """Validate and convert model output into a ToolRequest without executing it."""
    if isinstance(payload, ToolRequest):
        tool = payload.tool
        arguments = payload.arguments
    elif isinstance(payload, dict) and set(payload) in ({"tool", "arguments"}, {"tool", "arguments", "call_id"}):
        tool = payload["tool"]
        arguments = payload["arguments"]
        call_id = payload.get("call_id")
    else:
        raise ToolRequestError("Tool requests must contain 'tool', 'arguments', and optional 'call_id'.")

    if not isinstance(tool, str) or not tool.strip():
        raise ToolRequestError("Tool name must be a non-empty string.")
    if not isinstance(arguments, dict):
        raise ToolRequestError("Tool arguments must be an object.")
    if "call_id" in locals() and call_id is not None and not isinstance(call_id, str):
        raise ToolRequestError("Tool call ID must be text.")

    return ToolRequest(tool=tool, arguments=arguments, call_id=locals().get("call_id"))
