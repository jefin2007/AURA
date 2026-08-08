"""Safe arithmetic evaluation for AURA commands."""

import ast
import math
import re


class CalculatorError(ValueError):
    """Raised when an expression cannot be calculated safely."""


MAX_EXPONENT = 10_000
MATH_EXPRESSION = re.compile(r"^[\d\s.+\-*/%()]+$")


def calculate(expression):
    """Return a user-facing result or error message for an expression."""
    try:
        return f"The result is {evaluate(expression)}."
    except CalculatorError as error:
        return str(error)


def is_calculation_expression(expression):
    """Return whether input is shaped like a direct math expression."""
    expression = expression.strip()
    return expression.lower().startswith("sqrt(") or bool(MATH_EXPRESSION.fullmatch(expression))


def evaluate(expression):
    """Evaluate a restricted arithmetic expression without using eval()."""
    if not isinstance(expression, str) or not expression.strip():
        raise CalculatorError("Please enter a calculation.")

    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except SyntaxError as error:
        raise CalculatorError("Invalid expression.") from error

    try:
        return _evaluate_node(tree.body)
    except ZeroDivisionError as error:
        raise CalculatorError("Cannot divide by zero.") from error
    except OverflowError as error:
        raise CalculatorError("Result is too large.") from error


def _evaluate_node(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise CalculatorError("Unsupported value.")
        return node.value

    if isinstance(node, ast.UnaryOp):
        value = _evaluate_node(node.operand)
        if isinstance(node.op, ast.UAdd):
            return value
        if isinstance(node.op, ast.USub):
            return -value
        raise CalculatorError("Unsupported operation.")

    if isinstance(node, ast.BinOp):
        left = _evaluate_node(node.left)
        right = _evaluate_node(node.right)

        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Mod):
            return left % right
        if isinstance(node.op, ast.Pow):
            if abs(right) > MAX_EXPONENT:
                raise CalculatorError("Exponent is too large.")
            return left ** right
        raise CalculatorError("Unsupported operation.")

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id != "sqrt":
            raise CalculatorError("Unsupported operation.")
        if len(node.args) != 1 or node.keywords:
            raise CalculatorError("sqrt() accepts exactly one value.")

        value = _evaluate_node(node.args[0])
        if value < 0:
            raise CalculatorError("Cannot calculate the square root of a negative number.")
        return math.sqrt(value)

    raise CalculatorError("Unsupported operation.")
