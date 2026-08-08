"""Central permission checks for controlled tool execution."""

from enum import Enum


class PermissionLevel(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    SENSITIVE = "sensitive"


class PermissionDeniedError(PermissionError):
    """Raised when a tool is not allowed by the active permission policy."""


class PermissionPolicy:
    """Allow only explicitly permitted categories of registered tools."""

    def __init__(self, allowed_levels=None):
        self.allowed_levels = set(PermissionLevel if allowed_levels is None else allowed_levels)

    def allows(self, permission_level):
        return permission_level in self.allowed_levels

    def require(self, permission_level, tool_name):
        if not self.allows(permission_level):
            raise PermissionDeniedError(f"Permission denied for tool: {tool_name}.")
