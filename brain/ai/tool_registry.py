"""Allowlisted tool registration and execution for future AI requests."""

from dataclasses import dataclass

from brain.ai.schemas import ToolRequestError, parse_tool_request
from brain.permissions import PermissionLevel


@dataclass(frozen=True)
class RegisteredTool:
    name: str
    description: str
    handler: object
    validator: object
    permission_level: PermissionLevel
    parameters: dict | None = None


class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, tool):
        if not isinstance(tool, RegisteredTool) or not tool.name:
            raise ValueError("A registered tool must have a name.")
        if tool.name in self._tools:
            raise ValueError(f"Tool is already registered: {tool.name}.")
        self._tools[tool.name] = tool

    def get(self, tool_name):
        try:
            return self._tools[tool_name]
        except KeyError as error:
            raise ToolRequestError(f"Unknown tool: {tool_name}.") from error

    def validate(self, request):
        request = parse_tool_request(request)
        tool = self.get(request.tool)
        try:
            tool.validator(request.arguments)
        except (TypeError, ValueError) as error:
            raise ToolRequestError(f"Invalid arguments for {tool.name}: {error}") from error
        return request, tool

    def execute(self, request):
        request, tool = self.validate(request)
        return tool.handler(request.arguments)

    @property
    def tools(self):
        return tuple(self._tools.values())


def build_default_registry():
    """Build AURA's fixed allowlist of existing-domain tool wrappers."""
    from brain.tools import calculator_tools, memory_tools, notes_tools, time_tools

    registry = ToolRegistry()
    definitions = (
        RegisteredTool("calculator.evaluate", "Evaluate a safe arithmetic expression.", calculator_tools.evaluate_expression, calculator_tools.validate_evaluate, PermissionLevel.READ, _schema({"expression": {"type": "string"}}, ["expression"])),
        RegisteredTool("notes.create", "Create a persistent note.", notes_tools.create, notes_tools.validate_create, PermissionLevel.WRITE, _schema({"content": {"type": "string"}}, ["content"])),
        RegisteredTool("notes.list", "List persistent notes.", notes_tools.list_notes, notes_tools.validate_empty, PermissionLevel.READ, _schema()),
        RegisteredTool("notes.read", "Read one note by ID.", notes_tools.read, notes_tools.validate_note_id, PermissionLevel.READ, _schema({"note_id": {"type": "integer"}}, ["note_id"])),
        RegisteredTool("notes.delete", "Delete one note by ID.", notes_tools.delete, notes_tools.validate_note_id, PermissionLevel.DELETE, _schema({"note_id": {"type": "integer"}}, ["note_id"])),
        RegisteredTool("memory.search", "Find relevant stored memories.", memory_tools.search, memory_tools.validate_search, PermissionLevel.READ, _schema({"query": {"type": "string"}}, ["query"])),
        RegisteredTool("memory.save", "Save one memory key/value pair.", memory_tools.save, memory_tools.validate_save, PermissionLevel.WRITE, _schema({"key": {"type": "string"}, "value": {"type": "string"}, "category": {"type": "string"}}, ["key", "value"])),
        RegisteredTool("memory.delete", "Delete one exact memory key.", memory_tools.delete, memory_tools.validate_delete, PermissionLevel.DELETE, _schema({"key": {"type": "string"}}, ["key"])),
        RegisteredTool("time.current", "Get the current local time.", time_tools.current_time, time_tools.validate_empty, PermissionLevel.READ, _schema()),
        RegisteredTool("date.current", "Get the current local date.", time_tools.current_date, time_tools.validate_empty, PermissionLevel.READ, _schema()),
        RegisteredTool("day.current", "Get the current weekday.", time_tools.current_day, time_tools.validate_empty, PermissionLevel.READ, _schema()),
    )
    for tool in definitions:
        registry.register(tool)
    return registry


def _schema(properties=None, required=None):
    return {"type": "object", "properties": properties or {}, "required": required or []}
