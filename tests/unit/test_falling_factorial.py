"""Soundness tests for the unsigned falling-factorial checker."""

from __future__ import annotations

from pathlib import Path

from veriforge.canonical_certificate import CanonicalCertificate, check_certificate
from veriforge.config import SemanticConfiguration
from veriforge.exhaustive_oracle import exhaustive_compare
from veriforge.falling_factorial import (
    GRID_BUDGET,
    MAX_DEGREE,
    MAX_VARIABLES,
    TERM_BUDGET,
    CanonicalStatus,
    decide_mode_b,
)
from veriforge.independent_parser import parse_independent
from veriforge.models import SemanticMode


def _mode_b(width: int) -> SemanticConfiguration:
    return SemanticConfiguration(mode=SemanticMode.MODE_B, bit_width=width)


def _decide(original: str, candidate: str, width: int):
    return decide_mode_b(original, candidate, _mode_b(width))


def test_budgets_match_the_preregistered_protocol():
    assert TERM_BUDGET == 256
    assert GRID_BUDGET == 4096
    assert MAX_DEGREE == 12
    assert MAX_VARIABLES == 6


def test_modules_do_not_call_solvers_or_the_integer_oracle():
    root = Path(__file__).resolve().parents[2] / "veriforge"
    checker = (root / "canonical_certificate.py").read_text(encoding="utf-8")
    producer = (root / "falling_factorial.py").read_text(encoding="utf-8")
    for source in (checker, producer):
        imports = [
            line.strip()
            for line in source.splitlines()
            if line.startswith("import ") or line.startswith("from ")
        ]
        joined = "\n".join(imports)
        for banned in ("polynomial_oracle", "z3", "cvc5", "alive"):
            assert banned not in joined


def test_zero_and_one_and_nested_cancellation():
    assert _decide("0", "0", 4).status is CanonicalStatus.EQUIVALENT
    assert _decide("(a * 1)", "a", 4).status is CanonicalStatus.EQUIVALENT
    assert _decide("((a + 3) - 3)", "a", 4).status is CanonicalStatus.EQUIVALENT
    assert _decide("((a + 1) - 1)", "a", 1).status is CanonicalStatus.EQUIVALENT


def test_width_boundary_and_wrap():
    unsupported = _decide("(a * 2)", "(a + a)", 1)
    assert unsupported.status is CanonicalStatus.UNSUPPORTED
    wrapped = _decide("(a + a)", "(a * 2)", 8)
    assert wrapped.status is CanonicalStatus.EQUIVALENT
    assert wrapped.checker_accepted
    width_one = _decide("(a + a)", "0", 1)
    assert width_one.status is CanonicalStatus.EQUIVALENT
    width_two = _decide("(a + a)", "0", 2)
    assert width_two.status is CanonicalStatus.NOT_EQUIVALENT
    assert width_two.witness == {"a": 1}


def test_integer_versus_modular_traps():
    assert _decide("(a * (a - 1))", "0", 1).status is CanonicalStatus.EQUIVALENT
    wider = _decide("(a * (a - 1))", "0", 4)
    assert wider.status is CanonicalStatus.NOT_EQUIVALENT
    assert wider.witness is not None
    assert _decide("(a - b)", "(b - a)", 1).status is CanonicalStatus.EQUIVALENT
    swapped = _decide("(a - b)", "(b - a)", 2)
    assert swapped.status is CanonicalStatus.NOT_EQUIVALENT
    assert _decide("((a + 1) + 1)", "a", 1).status is CanonicalStatus.EQUIVALENT
    assert _decide("((a + 1) + 1)", "a", 2).status is CanonicalStatus.NOT_EQUIVALENT


def test_mode_a_is_unsupported():
    config = SemanticConfiguration(mode=SemanticMode.MODE_A, bit_width=32)
    decision = decide_mode_b("(a + a)", "0", config)
    assert decision.status is CanonicalStatus.UNSUPPORTED
    assert decision.checker_accepted is False


def test_malformed_certificate_is_rejected():
    config = _mode_b(4)
    decision = _decide("(a + 0)", "a", 4)
    assert decision.status is CanonicalStatus.EQUIVALENT
    certificate = decision.certificate
    assert certificate is not None
    terms = list(certificate.terms)
    alpha, raw, modulus, residue = terms[0]
    assert residue == 0 and modulus > 1
    terms[0] = (alpha, raw, modulus, 1)
    tampered = CanonicalCertificate(
        width=certificate.width,
        variables=certificate.variables,
        degrees=certificate.degrees,
        terms=tuple(terms),
    )
    left = parse_independent("(a + 0)", config).root
    right = parse_independent("a", config).root
    checked = check_certificate(
        left, right, tampered, grid_budget=GRID_BUDGET, deadline=1e12
    )
    assert checked.accepted is False
    assert checked.reason == "residue_mismatch"

    shifted = list(certificate.terms)
    alpha, raw, modulus, residue = shifted[0]
    shifted[0] = (alpha, raw + modulus, modulus, (raw + modulus) % modulus)
    shifted_certificate = CanonicalCertificate(
        width=certificate.width,
        variables=certificate.variables,
        degrees=certificate.degrees,
        terms=tuple(shifted),
    )
    shifted_check = check_certificate(
        left, right, shifted_certificate, grid_budget=GRID_BUDGET, deadline=1e12
    )
    assert shifted_check.accepted is False
    assert shifted_check.reason == "coefficient_mismatch"


def test_fast_newton_matches_the_direct_forward_difference():
    import math
    from itertools import product

    from veriforge.canonical_certificate import (
        _evaluate_grid,
        _forward_difference,
        _newton_raw_coefficients,
        syntactic_degrees,
    )

    config = _mode_b(4)
    left = parse_independent("((a + b) * (a + c)) + 1", config).root
    right = parse_independent("((a * b) + (b - c))", config).root
    names = ("a", "b", "c")
    degrees = syntactic_degrees(left, right, names)
    values = _evaluate_grid(left, right, names, degrees, deadline=1e12)
    raws = _newton_raw_coefficients(left, right, names, degrees, deadline=1e12)
    alphas = list(product(*[range(degree + 1) for degree in degrees]))
    assert len(raws) == len(alphas)
    for alpha, raw in zip(alphas, raws):
        difference = _forward_difference(values, alpha)
        divisor = math.prod(math.factorial(exponent) for exponent in alpha)
        assert difference % divisor == 0
        assert raw == difference // divisor


def test_unknown_is_not_equivalent_when_the_grid_cannot_be_checked():
    decision = decide_mode_b("(a + b)", "(b + a)", _mode_b(4), grid_budget=1)
    assert decision.status is not CanonicalStatus.EQUIVALENT
    assert decision.status is CanonicalStatus.UNKNOWN


def test_no_false_equivalent_on_a_small_exhaustive_domain():
    expressions = (
        "0",
        "1",
        "a",
        "b",
        "(a + a)",
        "(a - a)",
        "(a * a)",
        "(a * (a - 1))",
        "(a + b)",
        "(a - b)",
        "(b - a)",
        "(a * b)",
        "((a + b) + (a + b))",
        "((a + 1) + 1)",
    )
    failures = []
    for width in (1, 2, 3):
        config = _mode_b(width)
        for left in expressions:
            for right in expressions:
                decision = decide_mode_b(left, right, config)
                original = parse_independent(left, config).root
                candidate = parse_independent(right, config).root
                exhaustive = exhaustive_compare(
                    original, candidate, config, assignment_budget=65536
                )
                if exhaustive.verdict == "equivalent" and decision.status is not CanonicalStatus.EQUIVALENT:
                    failures.append((width, left, right, "missed", decision.status.value, decision.detail))
                if exhaustive.verdict == "counterexample" and decision.status is CanonicalStatus.EQUIVALENT:
                    failures.append((width, left, right, "false_equivalent", decision.detail))
                if exhaustive.verdict == "counterexample" and decision.status is not CanonicalStatus.NOT_EQUIVALENT:
                    failures.append((width, left, right, "not_rejected", decision.status.value, decision.detail))
    assert failures == []
