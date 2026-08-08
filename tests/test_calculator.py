import unittest

from brain.calculator import calculate, evaluate
from brain.commands import process


class CalculatorTestCase(unittest.TestCase):
    def test_basic_arithmetic(self):
        self.assertEqual(evaluate("2 + 2"), 4)
        self.assertEqual(evaluate("15 * 8"), 120)
        self.assertEqual(evaluate("100 / 4"), 25.0)

    def test_operator_precedence(self):
        self.assertEqual(evaluate("2 + 3 * 4"), 14)

    def test_parentheses(self):
        self.assertEqual(evaluate("(12 + 8) * 3"), 60)

    def test_exponentiation(self):
        self.assertEqual(evaluate("2 ** 10"), 1024)

    def test_modulo(self):
        self.assertEqual(evaluate("25 % 7"), 4)

    def test_square_root(self):
        self.assertEqual(evaluate("sqrt(81)"), 9.0)

    def test_decimal_numbers(self):
        self.assertEqual(evaluate("2.5 * 4"), 10.0)

    def test_division_by_zero(self):
        self.assertEqual(calculate("10 / 0"), "Cannot divide by zero.")

    def test_invalid_expressions(self):
        self.assertEqual(calculate("2 +"), "Invalid expression.")
        self.assertEqual(calculate("sqrt(-1)"), "Cannot calculate the square root of a negative number.")
        self.assertEqual(calculate(""), "Please enter a calculation.")

    def test_unsupported_operations(self):
        self.assertEqual(calculate("2 // 3"), "Unsupported operation.")
        self.assertEqual(calculate("sum(1, 2)"), "Unsupported operation.")

    def test_command_routing(self):
        self.assertEqual(process("2 + 2"), "The result is 4.")
        self.assertEqual(process("calculate sqrt(81)"), "The result is 9.0.")
        self.assertEqual(process("what is 25 % 7"), "The result is 4.")


if __name__ == "__main__":
    unittest.main()
