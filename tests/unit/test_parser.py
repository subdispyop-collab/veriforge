"""Parser acceptance, rejection, and resource-limit tests."""

from __future__ import annotations

import pytest

from veriforge import (
    BinaryOp,
    BinaryOperator,
    IntLiteral,
    InvalidLiteralError,
    ResourceLimitError,
    SemanticConfiguration,
    SemanticMode,
    UnapprovedASTNodeError,
    UnaryOp,
    UnaryOperator,
    UnsupportedSyntaxError,
    Variable,
    parse_expression,
)


def mode_a(**limit_changes: int) -> SemanticConfiguration:
    config = SemanticConfiguration(mode=SemanticMode.MODE_A)
    if limit_changes:
        return config.with_limits(**limit_changes)
    return config


def mode_b(width: int = 32, **limit_changes: int) -> SemanticConfiguration:
    config = SemanticConfiguration(mode=SemanticMode.MODE_B, bit_width=width)
    if limit_changes:
        return config.with_limits(**limit_changes)
    return config


class TestAcceptedForms:
    def test_decimal_literal(self) -> None:
        expr = parse_expression("42", mode_a())
        assert expr.root == IntLiteral(42)
        assert expr.variables == frozenset()

    def test_hex_bin_oct_and_underscores(self) -> None:
        assert parse_expression("0x10", mode_a()).root == IntLiteral(16)
        assert parse_expression("0b1010", mode_a()).root == IntLiteral(10)
        assert parse_expression("0o17", mode_a()).root == IntLiteral(15)
        assert parse_expression("1_000", mode_a()).root == IntLiteral(1000)
        assert parse_expression("0xFF_FF", mode_a()).root == IntLiteral(0xFFFF)

    def test_variable(self) -> None:
        expr = parse_expression("x", mode_a())
        assert expr.root == Variable("x")
        assert expr.variables == frozenset({"x"})

    def test_parenthesized(self) -> None:
        expr = parse_expression("(x + 1)", mode_a())
        assert isinstance(expr.root, BinaryOp)
        assert expr.root.op is BinaryOperator.ADD

    def test_binary_ops(self) -> None:
        add = parse_expression("x + y", mode_a())
        sub = parse_expression("x - y", mode_a())
        mul = parse_expression("x * y", mode_a())
        assert isinstance(add.root, BinaryOp) and add.root.op is BinaryOperator.ADD
        assert isinstance(sub.root, BinaryOp) and sub.root.op is BinaryOperator.SUB
        assert isinstance(mul.root, BinaryOp) and mul.root.op is BinaryOperator.MUL
        assert add.variables == frozenset({"x", "y"})

    def test_unary_ops(self) -> None:
        plus = parse_expression("+x", mode_a())
        minus = parse_expression("-x", mode_a())
        assert plus.root == UnaryOp(UnaryOperator.PLUS, Variable("x"))
        assert minus.root == UnaryOp(UnaryOperator.MINUS, Variable("x"))

    def test_nested_and_precedence_shape(self) -> None:
        # Python precedence: * binds tighter than +, so x + y * z is x + (y * z).
        expr = parse_expression("x + y * z", mode_a())
        assert isinstance(expr.root, BinaryOp)
        assert expr.root.op is BinaryOperator.ADD
        assert isinstance(expr.root.right, BinaryOp)
        assert expr.root.right.op is BinaryOperator.MUL

    def test_unary_minus_on_literal_is_unary_not_negative_token(self) -> None:
        expr = parse_expression("-1", mode_a())
        assert expr.root == UnaryOp(UnaryOperator.MINUS, IntLiteral(1))

    def test_repeated_unary(self) -> None:
        expr = parse_expression("--x", mode_a())
        assert expr.root == UnaryOp(
            UnaryOperator.MINUS,
            UnaryOp(UnaryOperator.MINUS, Variable("x")),
        )


class TestRejectedForms:
    @pytest.mark.parametrize(
        "source",
        [
            "f(x)",
            "x.attr",
            "x[0]",
            "x[1:2]",
            "import os",
            "[x for x in y]",
            "{x for x in y}",
            "{k: v for k, v in d}",
            "x = 1",
            "x += 1",
            "lambda x: x",
            "x if y else z",
            "x and y",
            "x or y",
            "not x",
            "x == y",
            "x < y",
            "x ** y",
            "x / y",
            "x // y",
            "x % y",
            "x & y",
            "x | y",
            "x ^ y",
            "x << y",
            "x >> y",
            "[1, 2]",
            "{1}",
            "{'a': 1}",
            "(x,)",
            "await x",
            "*x",
            "1.5",
            "'hi'",
            "None",
            "1j",
        ],
    )
    def test_unsupported_or_unapproved(self, source: str) -> None:
        with pytest.raises((UnsupportedSyntaxError, UnapprovedASTNodeError)):
            parse_expression(source, mode_a())

    def test_true_false_rejected(self) -> None:
        with pytest.raises(InvalidLiteralError):
            parse_expression("True", mode_a())
        with pytest.raises(InvalidLiteralError):
            parse_expression("False", mode_a())
        with pytest.raises(InvalidLiteralError):
            parse_expression("True + 1", mode_a())

    def test_empty_and_statement(self) -> None:
        with pytest.raises(UnsupportedSyntaxError):
            parse_expression("", mode_a())
        with pytest.raises(UnsupportedSyntaxError):
            parse_expression("x; y", mode_a())


class TestModeBLiterals:
    def test_literal_in_range_accepted(self) -> None:
        expr = parse_expression("255", mode_b(width=8))
        assert expr.root == IntLiteral(255)

    def test_literal_zero_accepted(self) -> None:
        assert parse_expression("0", mode_b(width=8)).root == IntLiteral(0)

    def test_literal_out_of_range_rejected(self) -> None:
        with pytest.raises(InvalidLiteralError):
            parse_expression("256", mode_b(width=8))

    def test_hex_out_of_range_rejected(self) -> None:
        with pytest.raises(InvalidLiteralError):
            parse_expression("0x100", mode_b(width=8))

    def test_default_width_32_boundary(self) -> None:
        max_u32 = (1 << 32) - 1
        assert parse_expression(str(max_u32), mode_b()).root == IntLiteral(max_u32)
        with pytest.raises(InvalidLiteralError):
            parse_expression(str(max_u32 + 1), mode_b())


class TestModeALiteralBitLength:
    def test_within_limit(self) -> None:
        # bit_length of 2**10 is 11; keep a small custom limit.
        config = mode_a(max_mode_a_literal_bit_length=11)
        assert parse_expression(str(2**10), config).root == IntLiteral(2**10)

    def test_over_limit(self) -> None:
        config = mode_a(max_mode_a_literal_bit_length=10)
        with pytest.raises(InvalidLiteralError):
            parse_expression(str(2**10), config)


class TestResourceLimits:
    def test_source_length(self) -> None:
        config = mode_a(max_source_length=5)
        with pytest.raises(ResourceLimitError):
            parse_expression("x + y + z", config)

    def test_ast_node_count(self) -> None:
        # "x" -> Expression, Name, Load = 3 nodes. Limit 2 must fail.
        config = mode_a(max_ast_nodes=2)
        with pytest.raises(ResourceLimitError):
            parse_expression("x", config)

    def test_nesting_depth(self) -> None:
        # (((x))) still depth 1 for Name; use nested BinOps.
        # x+1 depth: BinOp at 1, Name/Constant at 2. Nested (((x+1)+1)+1)...
        config = mode_a(max_nesting_depth=2)
        with pytest.raises(ResourceLimitError):
            parse_expression("((x + 1) + 1)", config)

    def test_nesting_within_limit(self) -> None:
        config = mode_a(max_nesting_depth=3)
        expr = parse_expression("((x + 1) + 1)", config)
        assert isinstance(expr.root, BinaryOp)
