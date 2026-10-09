"""Hand-checked Mode B (unsigned fixed-width bit-vector) semantic tests."""

from __future__ import annotations

import pytest

from veriforge import (
    DomainError,
    InvalidLiteralError,
    MissingVariableError,
    SemanticConfiguration,
    SemanticMode,
    evaluate,
    parse_expression,
)


def config(width: int = 32) -> SemanticConfiguration:
    return SemanticConfiguration(mode=SemanticMode.MODE_B, bit_width=width)


def ev(source: str, assignment: dict[str, int] | None = None, width: int = 32) -> int:
    cfg = config(width)
    expression = parse_expression(source, cfg)
    return evaluate(expression, assignment or {}, cfg)


class TestModeBHandChecked:
    def test_literal_in_range(self) -> None:
        assert ev("0", width=8) == 0
        assert ev("255", width=8) == 255
        assert ev("0xFF", width=8) == 255

    def test_literal_out_of_range_not_reduced(self) -> None:
        # Locked decision: literals outside [0, 2^w-1] are rejected, not wrapped.
        with pytest.raises(InvalidLiteralError):
            parse_expression("256", config(8))
        with pytest.raises(InvalidLiteralError):
            parse_expression("0x100", config(8))

    def test_addition_wraps(self) -> None:
        # 200 + 100 = 300; 300 mod 256 = 44
        assert ev("200 + 100", width=8) == 44
        assert ev("255 + 1", width=8) == 0

    def test_subtraction_wraps(self) -> None:
        # 0 - 1 mod 256 = 255
        assert ev("0 - 1", width=8) == 255
        assert ev("5 - 10", width=8) == 251

    def test_multiplication_wraps(self) -> None:
        # 16 * 16 = 256 ≡ 0 (mod 256)
        assert ev("16 * 16", width=8) == 0
        # 20 * 20 = 400 ≡ 144 (mod 256)
        assert ev("20 * 20", width=8) == 144

    def test_unary_plus(self) -> None:
        assert ev("+7", width=8) == 7
        assert ev("+x", {"x": 3}, width=8) == 3

    def test_unary_minus_is_bv_negation(self) -> None:
        # -x ≡ (2^w - x) mod 2^w for unsigned wrap.
        assert ev("-0", width=8) == 0
        assert ev("-1", width=8) == 255
        assert ev("-1", width=32) == (1 << 32) - 1
        assert ev("-x", {"x": 1}, width=8) == 255
        assert ev("-x", {"x": 128}, width=8) == 128
        assert ev("--x", {"x": 5}, width=8) == 5

    def test_default_width_is_32(self) -> None:
        cfg = SemanticConfiguration(mode=SemanticMode.MODE_B)
        assert cfg.bit_width == 32
        expression = parse_expression("1 + 2", cfg)
        assert evaluate(expression, {}, cfg) == 3
        # Wrap at 2^32.
        expression = parse_expression("x + 1", cfg)
        assert evaluate(expression, {"x": (1 << 32) - 1}, cfg) == 0

    def test_modes_not_conflated(self) -> None:
        # Same text, different modes: Mode A is unbounded; Mode B wraps.
        mode_a = SemanticConfiguration(mode=SemanticMode.MODE_A)
        mode_b = config(8)
        # Mode A can use a large literal; Mode B rejects it.
        expr_a = parse_expression("300", mode_a)
        assert evaluate(expr_a, {}, mode_a) == 300
        with pytest.raises(InvalidLiteralError):
            parse_expression("300", mode_b)

        # Arithmetic: Mode A 200+100=300; Mode B wraps to 44.
        assert evaluate(parse_expression("200 + 100", mode_a), {}, mode_a) == 300
        assert evaluate(parse_expression("200 + 100", mode_b), {}, mode_b) == 44

    def test_variable_domain(self) -> None:
        expression = parse_expression("x", config(8))
        assert evaluate(expression, {"x": 255}, config(8)) == 255
        with pytest.raises(DomainError):
            evaluate(expression, {"x": 256}, config(8))
        with pytest.raises(DomainError):
            evaluate(expression, {"x": -1}, config(8))

    def test_missing_variable(self) -> None:
        expression = parse_expression("x", config(8))
        with pytest.raises(MissingVariableError):
            evaluate(expression, {}, config(8))

    def test_nested_wrapping(self) -> None:
        # ((200 + 200) * 2) mod 256: 400 mod 256 = 144; 144 * 2 = 288 mod 256 = 32
        assert ev("(200 + 200) * 2", width=8) == 32

    def test_identity_shapes_under_wrap(self) -> None:
        assert ev("x + 0", {"x": 200}, width=8) == 200
        assert ev("x - 0", {"x": 200}, width=8) == 200
        assert ev("x * 1", {"x": 200}, width=8) == 200
        assert ev("x * 0", {"x": 200}, width=8) == 0
