"""Phase 2 verifier tests: translation, classification, counterexamples, errors."""

from __future__ import annotations

from typing import Any

import pytest
import z3

from veriforge.config import SemanticConfiguration
from veriforge.models import (
    CounterexampleValidationStatus,
    SemanticMode,
    VerificationStatus,
)
from veriforge.parser_engine import parse_expression
from veriforge.reference_evaluator import evaluate
from veriforge.verifier_engine import (
    classify_check_result,
    translate_to_z3,
    verify_equivalence,
)


def mode_a(**limit_changes: float | int) -> SemanticConfiguration:
    cfg = SemanticConfiguration(mode=SemanticMode.MODE_A)
    if limit_changes:
        return cfg.with_limits(**limit_changes)
    return cfg


def mode_b(width: int = 32, **limit_changes: float | int) -> SemanticConfiguration:
    cfg = SemanticConfiguration(mode=SemanticMode.MODE_B, bit_width=width)
    if limit_changes:
        return cfg.with_limits(**limit_changes)
    return cfg


# --- Translation and mode selection -------------------------------------------------


def test_mode_a_translates_to_int_sort() -> None:
    expr = parse_expression("x + 1", mode_a())
    term, symbols = translate_to_z3(expr, mode_a())
    assert term.sort() == z3.IntSort()
    assert symbols["x"].sort() == z3.IntSort()


def test_mode_b_translates_to_bitvector_sort() -> None:
    cfg = mode_b(8)
    expr = parse_expression("x + 1", cfg)
    term, symbols = translate_to_z3(expr, cfg)
    assert term.sort() == z3.BitVecSort(8)
    assert symbols["x"].sort() == z3.BitVecSort(8)


def test_mode_selection_is_not_interchangeable() -> None:
    """Same text under Mode A and Mode B yields different Z3 sorts."""
    a = translate_to_z3(parse_expression("x", mode_a()), mode_a())[0]
    b = translate_to_z3(parse_expression("x", mode_b(16)), mode_b(16))[0]
    assert a.sort() != b.sort()


def test_constants_translate_mode_a() -> None:
    term, _ = translate_to_z3(parse_expression("42", mode_a()), mode_a())
    assert z3.simplify(term).as_long() == 42


def test_constants_translate_mode_b() -> None:
    cfg = mode_b(8)
    term, _ = translate_to_z3(parse_expression("255", cfg), cfg)
    assert z3.simplify(term).as_long() == 255


def test_variable_consistency_across_original_and_candidate() -> None:
    cfg = mode_a()
    result = verify_equivalence("x + y", "y + x", cfg)
    assert result.status is VerificationStatus.EQUIVALENT_WITHIN_MODEL


def test_unary_and_binary_operators_mode_a() -> None:
    cfg = mode_a()
    result = verify_equivalence("-(x) + +y * 2", "(-x) + (y * 2)", cfg)
    assert result.status is VerificationStatus.EQUIVALENT_WITHIN_MODEL


# --- Equivalence and incorrect candidates -------------------------------------------


def test_equivalent_identity_mode_a() -> None:
    result = verify_equivalence("x + 0", "x", mode_a())
    assert result.status is VerificationStatus.EQUIVALENT_WITHIN_MODEL
    assert result.counterexample is None
    assert result.solver_status == "unsat"


def test_equivalent_identity_mode_b() -> None:
    result = verify_equivalence("x + 0", "x", mode_b())
    assert result.status is VerificationStatus.EQUIVALENT_WITHIN_MODEL


def test_incorrect_candidate_mode_a_finds_counterexample() -> None:
    result = verify_equivalence("x + 1", "x + 2", mode_a())
    assert result.status is VerificationStatus.COUNTEREXAMPLE_FOUND
    assert result.counterexample is not None
    cex = result.counterexample
    assert cex.validation_status is CounterexampleValidationStatus.CONFIRMED
    assert cex.original_value != cex.candidate_value
    # Independently re-check with the reference evaluator.
    orig = parse_expression("x + 1", mode_a())
    cand = parse_expression("x + 2", mode_a())
    assert evaluate(orig, cex.assignment, mode_a()) == cex.original_value
    assert evaluate(cand, cex.assignment, mode_a()) == cex.candidate_value


def test_incorrect_candidate_mode_b_finds_counterexample() -> None:
    cfg = mode_b(8)
    result = verify_equivalence("x + 1", "x", cfg)
    assert result.status is VerificationStatus.COUNTEREXAMPLE_FOUND
    assert result.counterexample is not None
    assert result.counterexample.validation_status is CounterexampleValidationStatus.CONFIRMED
    x = result.counterexample.assignment["x"]
    assert 0 <= x <= 255


def test_constant_inequivalence() -> None:
    result = verify_equivalence("1 + 1", "3", mode_a())
    assert result.status is VerificationStatus.COUNTEREXAMPLE_FOUND
    assert result.counterexample is not None
    assert result.counterexample.assignment == {}
    assert result.counterexample.original_value == 2
    assert result.counterexample.candidate_value == 3


def test_constant_equivalence() -> None:
    result = verify_equivalence("1 + 1", "2", mode_a())
    assert result.status is VerificationStatus.EQUIVALENT_WITHIN_MODEL


# --- Mode B boundaries and wrapping -------------------------------------------------


def test_mode_b_wrap_boundary_counterexample() -> None:
    """x+1 is not equivalent to x; a wrapping input is a valid counterexample."""
    cfg = mode_b(4)
    result = verify_equivalence("x + 1", "x", cfg)
    assert result.status is VerificationStatus.COUNTEREXAMPLE_FOUND
    assert result.counterexample is not None
    x = result.counterexample.assignment["x"]
    assert 0 <= x <= 15
    assert result.counterexample.original_value == ((x + 1) % 16)
    assert result.counterexample.candidate_value == x


def test_mode_b_unary_minus_matches_bv_negation() -> None:
    cfg = mode_b(8)
    result = verify_equivalence("-1", "255", cfg)
    assert result.status is VerificationStatus.EQUIVALENT_WITHIN_MODEL


def test_mode_b_modular_add_equivalence() -> None:
    cfg = mode_b(8)
    # (x + 200) + 100 ≡ x + 44  (mod 256) because 300 ≡ 44.
    result = verify_equivalence("(x + 200) + 100", "x + 44", cfg)
    assert result.status is VerificationStatus.EQUIVALENT_WITHIN_MODEL


def test_mode_a_no_wrap_differs_from_mode_b_story() -> None:
    """Under Mode A, 255 + 1 is 256, not a wrap to 0."""
    result = verify_equivalence("255 + 1", "256", mode_a())
    assert result.status is VerificationStatus.EQUIVALENT_WITHIN_MODEL
    result_b = verify_equivalence("255 + 1", "0", mode_b(8))
    assert result_b.status is VerificationStatus.EQUIVALENT_WITHIN_MODEL


# --- Unsupported / invalid / errors -------------------------------------------------


def test_unsupported_syntax() -> None:
    result = verify_equivalence("x / 2", "x", mode_a())
    assert result.status is VerificationStatus.UNSUPPORTED
    assert result.counterexample is None


def test_unsupported_call() -> None:
    result = verify_equivalence("abs(x)", "x", mode_a())
    assert result.status is VerificationStatus.UNSUPPORTED


def test_invalid_input_resource_limit() -> None:
    cfg = mode_a(max_source_length=3)
    result = verify_equivalence("x + 1", "x", cfg)
    assert result.status is VerificationStatus.INVALID_INPUT


def test_invalid_literal_mode_b() -> None:
    cfg = mode_b(8)
    result = verify_equivalence("256", "0", cfg)
    assert result.status is VerificationStatus.INVALID_INPUT


def test_boolean_literal_rejected() -> None:
    result = verify_equivalence("True", "1", mode_a())
    assert result.status is VerificationStatus.INVALID_INPUT


def test_statuses_are_never_boolean() -> None:
    result = verify_equivalence("x", "x", mode_a())
    assert isinstance(result.status, VerificationStatus)
    assert not isinstance(result.status, bool)
    assert not hasattr(result, "success")


# --- Classification: timeout and UNKNOWN --------------------------------------------


def test_classify_unsat() -> None:
    assert (
        classify_check_result(z3.unsat)
        is VerificationStatus.EQUIVALENT_WITHIN_MODEL
    )


def test_classify_sat_provisional() -> None:
    assert (
        classify_check_result(z3.sat) is VerificationStatus.COUNTEREXAMPLE_FOUND
    )


def test_classify_unknown() -> None:
    assert (
        classify_check_result(z3.unknown, "incomplete")
        is VerificationStatus.UNKNOWN
    )


@pytest.mark.parametrize(
    "reason",
    ["timeout", "canceled", "cancelled", "interrupted", "smt tactic timeout"],
)
def test_classify_timeout_reasons(reason: str) -> None:
    assert (
        classify_check_result(z3.unknown, reason) is VerificationStatus.TIMEOUT
    )


def test_timeout_path_via_solver_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_check(self: z3.Solver) -> z3.CheckSatResult:
        return z3.unknown

    def fake_reason(self: z3.Solver) -> str:
        return "timeout"

    monkeypatch.setattr(z3.Solver, "check", fake_check)
    monkeypatch.setattr(z3.Solver, "reason_unknown", fake_reason)

    result = verify_equivalence("x + 1", "x + 1", mode_a(solver_timeout_seconds=5.0))
    assert result.status is VerificationStatus.TIMEOUT
    assert result.timeout_seconds == 5.0
    assert result.solver_status == "unknown"


def test_unknown_path_via_solver_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_check(self: z3.Solver) -> z3.CheckSatResult:
        return z3.unknown

    def fake_reason(self: z3.Solver) -> str:
        return "incomplete (theory combination)"

    monkeypatch.setattr(z3.Solver, "check", fake_check)
    monkeypatch.setattr(z3.Solver, "reason_unknown", fake_reason)

    result = verify_equivalence("x", "x", mode_a())
    assert result.status is VerificationStatus.UNKNOWN


def test_default_solver_timeout_is_five_seconds() -> None:
    cfg = mode_a()
    assert cfg.limits.solver_timeout_seconds == 5.0
    result = verify_equivalence("x", "x", cfg)
    assert result.timeout_seconds == 5.0


def test_configurable_timeout_is_recorded() -> None:
    cfg = mode_a(solver_timeout_seconds=1.5)
    result = verify_equivalence("x", "x", cfg)
    assert result.timeout_seconds == 1.5


# --- Counterexample reconstruction and discrepancy ----------------------------------


def test_counterexample_reconstruction_mode_b_width() -> None:
    cfg = mode_b(4)
    result = verify_equivalence("x * 2", "x + x + 1", cfg)
    assert result.status is VerificationStatus.COUNTEREXAMPLE_FOUND
    assert result.bit_width == 4
    assert result.counterexample is not None
    assignment = result.counterexample.assignment
    orig = parse_expression("x * 2", cfg)
    cand = parse_expression("x + x + 1", cfg)
    assert evaluate(orig, assignment, cfg) != evaluate(cand, assignment, cfg)


def test_discrepancy_not_labeled_confirmed(monkeypatch: pytest.MonkeyPatch) -> None:
    """If the reference evaluator agrees on a SAT model, report a defect, not CEX."""

    real_evaluate = evaluate

    def agreeing_evaluate(expression: Any, assignment: Any, config: Any) -> int:
        # Force both sides to the same value so validation fails to confirm.
        return 0

    monkeypatch.setattr(
        "veriforge.verifier_engine.evaluate", agreeing_evaluate
    )
    # Keep a real sat path: x+1 vs x.
    result = verify_equivalence("x + 1", "x", mode_a())
    # Failed validation is its own status. It is never equivalence, and it is
    # no longer collapsed into VERIFICATION_ERROR (unexpected engine failures).
    assert result.status is VerificationStatus.COUNTEREXAMPLE_VALIDATION_FAILED
    assert result.counterexample is not None
    assert (
        result.counterexample.validation_status
        is CounterexampleValidationStatus.DISCREPANCY
    )
    # Restore sanity: real evaluator would have differed.
    monkeypatch.setattr("veriforge.verifier_engine.evaluate", real_evaluate)


def test_unvalidatable_counterexample(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args: Any, **_kwargs: Any) -> int:
        raise RuntimeError("evaluator unavailable")

    monkeypatch.setattr("veriforge.verifier_engine.evaluate", boom)
    result = verify_equivalence("x + 1", "x", mode_a())
    assert result.status is VerificationStatus.COUNTEREXAMPLE_VALIDATION_FAILED
    assert result.counterexample is not None
    assert (
        result.counterexample.validation_status
        is CounterexampleValidationStatus.UNVALIDATABLE
    )


def test_accepts_preparsed_expressions() -> None:
    cfg = mode_a()
    original = parse_expression("x * 1", cfg)
    candidate = parse_expression("x", cfg)
    result = verify_equivalence(original, candidate, cfg)
    assert result.status is VerificationStatus.EQUIVALENT_WITHIN_MODEL
    assert result.original_source == "x * 1"


def test_result_preserves_mode_metadata() -> None:
    cfg = mode_b(16)
    result = verify_equivalence("x", "x", cfg)
    assert result.mode is SemanticMode.MODE_B
    assert result.bit_width == 16
