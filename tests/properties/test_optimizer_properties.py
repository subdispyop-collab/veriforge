"""Hypothesis properties for verification-guided optimizer acceptance."""

from __future__ import annotations

from hypothesis import given, settings, seed
from hypothesis import strategies as st

from veriforge.models import CandidateDecision, CorrectnessPolicy, VerificationStatus
from veriforge.optimizer_engine import optimize, render_expr
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


def _with_identity_noise_mode_a(draw: st.DrawFn):
    """Build a Mode A expression that often admits identity rewrites."""
    base = draw(mode_a_expr_trees(max_leaves=3))
    source = render_expr(base)
    # Wrap with identity-preserving noise that the optimizer should remove.
    wrappers = [
        f"({source}) + 0",
        f"({source}) - 0",
        f"({source}) * 1",
        f"(({source}) + 0) * 1",
    ]
    return draw(st.sampled_from(wrappers))


def _with_identity_noise_mode_b(draw: st.DrawFn, width: int = 8):
    base = draw(mode_b_expr_trees(width=width, max_leaves=3))
    source = render_expr(base)
    wrappers = [
        f"({source}) + 0",
        f"({source}) - 0",
        f"({source}) * 1",
        f"(({source}) + 0) * 1",
    ]
    return draw(st.sampled_from(wrappers))


@st.composite
def mode_a_optimizable_source(draw: st.DrawFn) -> str:
    return _with_identity_noise_mode_a(draw)


@st.composite
def mode_b_optimizable_source(draw: st.DrawFn) -> str:
    return _with_identity_noise_mode_b(draw, width=8)


@seed(HYPOTHESIS_SEED)
@settings(max_examples=50, deadline=None)
@given(mode_a_optimizable_source())
def test_accepted_candidates_remain_equivalent_mode_a(source: str) -> None:
    cfg = mode_a_config()
    result = optimize(source, cfg)
    assert result.policy is CorrectnessPolicy.VERIFICATION_GUIDED
    for step in result.accepted_steps:
        assert step.decision is CandidateDecision.ACCEPTED
        assert step.verification_result is not None
        assert (
            step.verification_result.status
            is VerificationStatus.EQUIVALENT_WITHIN_MODEL
        )
    verification = verify_equivalence(result.original, result.accepted, cfg)
    assert verification.status is VerificationStatus.EQUIVALENT_WITHIN_MODEL


@seed(HYPOTHESIS_SEED)
@settings(max_examples=50, deadline=None)
@given(mode_b_optimizable_source())
def test_accepted_candidates_remain_equivalent_mode_b(source: str) -> None:
    cfg = mode_b_config(width=8)
    result = optimize(source, cfg)
    assert result.policy is CorrectnessPolicy.VERIFICATION_GUIDED
    verification = verify_equivalence(result.original, result.accepted, cfg)
    assert verification.status is VerificationStatus.EQUIVALENT_WITHIN_MODEL


@st.composite
def mode_a_opt_and_assignment(draw: st.DrawFn):
    source = _with_identity_noise_mode_a(draw)
    cfg = mode_a_config()
    original = parse_expression(source, cfg)
    names = original.variables
    assignment = {
        name: draw(st.integers(min_value=-32, max_value=32)) for name in sorted(names)
    }
    return source, assignment


@seed(HYPOTHESIS_SEED)
@settings(max_examples=60, deadline=None)
@given(mode_a_opt_and_assignment())
def test_accepted_matches_reference_evaluator_samples_mode_a(pair) -> None:
    source, assignment = pair
    cfg = mode_a_config()
    result = optimize(source, cfg)
    left = evaluate(result.original, assignment, cfg)
    right = evaluate(result.accepted, assignment, cfg)
    assert left == right
