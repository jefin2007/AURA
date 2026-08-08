"""Bounded, controlled model-to-tool orchestration for AURA."""

from brain.ai.schemas import ToolRequestError, ToolResult, parse_tool_request
from brain.ai.tool_registry import build_default_registry
from brain.permissions import PermissionDeniedError, PermissionPolicy


MAX_TOOL_CALLS = 3


def run(user_request, model_adapter, registry=None, permissions=None, max_tool_calls=MAX_TOOL_CALLS):
    """Run a short model/tool conversation and return its final text or safe error."""
    registry = registry or build_default_registry()
    permissions = permissions or PermissionPolicy()
    messages = [{"role": "user", "content": user_request}]
    tools = _tool_descriptions(registry)

    for _ in range(max_tool_calls):
        model_response = model_adapter.respond(messages, tools)
        if isinstance(model_response, str):
            return model_response

        tool_result = _execute_tool_request(model_response, registry, permissions)
        if not tool_result.success:
            return tool_result.to_dict()

        messages.append({"role": "tool", "content": tool_result.to_dict()})

    return ToolResult(
        success=False,
        tool=None,
        error="Tool-call limit reached.",
    ).to_dict()


def _execute_tool_request(model_response, registry, permissions):
    tool_name = None
    call_id = None
    try:
        request = parse_tool_request(model_response)
        tool_name = request.tool
        call_id = request.call_id
        _, tool = registry.validate(request)
        permissions.require(tool.permission_level, tool.name)
        result = registry.execute(request)
        return ToolResult(success=True, tool=tool.name, result=result, call_id=request.call_id)
    except (ToolRequestError, PermissionDeniedError, ValueError) as error:
        return ToolResult(success=False, tool=tool_name, error=str(error), call_id=call_id)


def _tool_descriptions(registry):
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "permission_level": tool.permission_level.value,
            "parameters": tool.parameters,
        }
        for tool in registry.tools
    ]
