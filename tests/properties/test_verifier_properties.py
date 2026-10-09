"""Hypothesis properties for the Phase 2 verifier under the locked contract."""

from __future__ import annotations

from hypothesis import assume, given, settings, seed
from hypothesis import strategies as st

from veriforge.models import VerificationStatus
from veriforge.optimizer_engine import render_expr
from veriforge.parser_engine import parse_expression
from veriforge.reference_evaluator import evaluate
from veriforge.verifier_engine import verify_equivalence

from tests.properties.strategies import (
    collect_variables,
    mode_a_config,
    mode_a_expr_trees,
    mode_b_config,
    mode_b_expr_trees,
)

HYPOTHESIS_SEED = 20261009


@st.composite
def mode_a_pair_with_assignment(draw: st.DrawFn):
    left = draw(mode_a_expr_trees(max_leaves=4))
    right = draw(mode_a_expr_trees(max_leaves=4))
    names = collect_variables(left) | collect_variables(right)
    assignment = {
        name: draw(st.integers(min_value=-24, max_value=24)) for name in sorted(names)
    }
    return left, right, assignment


@st.composite
def mode_b_pair_with_assignment(draw: st.DrawFn, width: int = 8):
    left = draw(mode_b_expr_trees(width=width, max_leaves=4))
    right = draw(mode_b_expr_trees(width=width, max_leaves=4))
    names = collect_variables(left) | collect_variables(right)
    maximum = (1 << width) - 1
    assignment = {
        name: draw(st.integers(min_value=0, max_value=maximum))
        for name in sorted(names)
    }
    return left, right, assignment, width


@seed(HYPOTHESIS_SEED)
@settings(max_examples=60, deadline=None)
@given(mode_a_expr_trees(max_leaves=5))
def test_identical_expressions_are_equivalent_mode_a(tree) -> None:
    cfg = mode_a_config()
    source = render_expr(tree)
    result = verify_equivalence(source, source, cfg)
    assert result.status is VerificationStatus.EQUIVALENT_WITHIN_MODEL


@seed(HYPOTHESIS_SEED)
@settings(max_examples=60, deadline=None)
@given(mode_b_expr_trees(width=8, max_leaves=5))
def test_identical_expressions_are_equivalent_mode_b(tree) -> None:
    cfg = mode_b_config(width=8)
    source = render_expr(tree)
    result = verify_equivalence(source, source, cfg)
    assert result.status is VerificationStatus.EQUIVALENT_WITHIN_MODEL


@seed(HYPOTHESIS_SEED)
@settings(max_examples=80, deadline=None)
@given(mode_a_pair_with_assignment())
def test_reference_difference_implies_not_equivalent_mode_a(triple) -> None:
    left, right, assignment = triple
    cfg = mode_a_config()
    left_expr = parse_expression(render_expr(left), cfg)
    right_expr = parse_expression(render_expr(right), cfg)
    left_val = evaluate(left_expr, assignment, cfg)
    right_val = evaluate(right_expr, assignment, cfg)
    assume(left_val != right_val)
    result = verify_equivalence(left_expr, right_expr, cfg)
    assert result.status is not VerificationStatus.EQUIVALENT_WITHIN_MODEL
    assert result.status in {
        VerificationStatus.COUNTEREXAMPLE_FOUND,
        VerificationStatus.UNKNOWN,
        VerificationStatus.TIMEOUT,
        VerificationStatus.VERIFICATION_ERROR,
        VerificationStatus.TRANSLATION_ERROR,
    }


@seed(HYPOTHESIS_SEED)
@settings(max_examples=80, deadline=None)
@given(mode_b_pair_with_assignment(width=8))
def test_reference_difference_implies_not_equivalent_mode_b(quad) -> None:
    left, right, assignment, width = quad
    cfg = mode_b_config(width=width)
    left_expr = parse_expression(render_expr(left), cfg)
    right_expr = parse_expression(render_expr(right), cfg)
    left_val = evaluate(left_expr, assignment, cfg)
    right_val = evaluate(right_expr, assignment, cfg)
    assume(left_val != right_val)
    result = verify_equivalence(left_expr, right_expr, cfg)
    assert result.status is not VerificationStatus.EQUIVALENT_WITHIN_MODEL
