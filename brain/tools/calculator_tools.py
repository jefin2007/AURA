"""Tool wrapper for AURA's safe calculator."""

from brain.calculator import evaluate


def validate_evaluate(arguments):
    _require_only(arguments, {"expression"})
    if not isinstance(arguments["expression"], str) or not arguments["expression"].strip():
        raise ValueError("'expression' must be a non-empty string.")


def evaluate_expression(arguments):
    return {"result": evaluate(arguments["expression"])}


def _require_only(arguments, expected_keys):
    if not isinstance(arguments, dict) or set(arguments) != expected_keys:
        raise ValueError(f"Expected arguments: {', '.join(sorted(expected_keys))}.")
