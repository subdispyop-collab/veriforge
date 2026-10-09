"""Hand-checked Mode A (mathematical integer) semantic tests."""

from __future__ import annotations

import pytest

from veriforge import (
    DomainError,
    MissingVariableError,
    SemanticConfiguration,
    SemanticMode,
    evaluate,
    parse_expression,
)


def config() -> SemanticConfiguration:
    return SemanticConfiguration(mode=SemanticMode.MODE_A)


def ev(source: str, assignment: dict[str, int] | None = None) -> int:
    expression = parse_expression(source, config())
    return evaluate(expression, assignment or {}, config())


class TestModeAHandChecked:
    def test_literal(self) -> None:
        assert ev("0") == 0
        assert ev("42") == 42
        assert ev("0x2A") == 42

    def test_unary_plus_and_minus(self) -> None:
        assert ev("+7") == 7
        assert ev("-7") == -7
        assert ev("--7") == 7
        assert ev("-+7") == -7
        assert ev("+-7") == -7

    def test_addition_subtraction_multiplication(self) -> None:
        assert ev("2 + 3") == 5
        assert ev("2 - 3") == -1
        assert ev("2 * 3") == 6
        assert ev("2 + 3 * 4") == 14
        assert ev("(2 + 3) * 4") == 20

    def test_variables(self) -> None:
        assert ev("x", {"x": 5}) == 5
        assert ev("x + y", {"x": 2, "y": 3}) == 5
        assert ev("x * y - z", {"x": 4, "y": 5, "z": 6}) == 14
        assert ev("-x", {"x": 9}) == -9

    def test_large_integers_unbounded(self) -> None:
        # Mode A must not wrap. 2**100 is a mathematical integer result.
        assert ev("x * y", {"x": 2**50, "y": 2**50}) == 2**100

    def test_identity_shapes(self) -> None:
        assert ev("x + 0", {"x": 17}) == 17
        assert ev("x - 0", {"x": 17}) == 17
        assert ev("x * 1", {"x": 17}) == 17
        assert ev("x * 0", {"x": 17}) == 0

    def test_missing_variable(self) -> None:
        expression = parse_expression("x + y", config())
        with pytest.raises(MissingVariableError):
            evaluate(expression, {"x": 1}, config())

    def test_bool_assignment_rejected(self) -> None:
        expression = parse_expression("x", config())
        with pytest.raises(DomainError):
            evaluate(expression, {"x": True}, config())  # type: ignore[dict-item]
