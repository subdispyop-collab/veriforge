"""Phase 3 optimizer tests: rules, pipeline, traces, and verification gating."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from veriforge.config import SemanticConfiguration
from veriforge.exceptions import OptimizerError
from veriforge.models import (
    BinaryOp,
    BinaryOperator,
    CandidateDecision,
    CorrectnessPolicy,
    IntLiteral,
    SemanticMode,
    Variable,
    VerificationPolicy,
    VerificationResult,
    VerificationStatus,
)
from veriforge.optimizer_engine import (
    RULE_ADD_ZERO,
    RULE_MUL_ONE,
    RULE_MUL_ZERO,
    RULE_SUB_ZERO,
    default_rules,
    expression_from_root,
    find_applicable_matches,
    optimize,
    render_expr,
    rule_by_id,
    try_apply_rule,
)
from veriforge.parser_engine import parse_expression
from veriforge.verifier_engine import verify_equivalence


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


# --- Rule metadata ------------------------------------------------------------------


def test_default_rules_have_required_metadata() -> None:
    rules = default_rules()
    assert len(rules) == 4
    ids = {rule.rule_id for rule in rules}
    assert ids == {
        "identity.add_zero",
        "identity.sub_zero",
        "identity.mul_one",
        "identity.mul_zero",
    }
    for rule in rules:
        assert rule.name
        assert rule.formal_description
        assert rule.preconditions
        assert rule.supported_modes == frozenset(
            {SemanticMode.MODE_A, SemanticMode.MODE_B}
        )
        assert (
            rule.verification_policy
            is VerificationPolicy.REQUIRE_EQUIVALENT_WITHIN_MODEL
        )


def test_rule_by_id_round_trip() -> None:
    assert rule_by_id("identity.add_zero") is RULE_ADD_ZERO
    with pytest.raises(OptimizerError, match="unknown optimization rule"):
        rule_by_id("identity.not_a_rule")


# --- Positive local rewrites (Mode A and Mode B) ------------------------------------


@pytest.mark.parametrize("cfg_factory", [mode_a, mode_b])
@pytest.mark.parametrize(
    ("source", "rule", "expected_source"),
    [
        ("x + 0", RULE_ADD_ZERO, "x"),
        ("x - 0", RULE_SUB_ZERO, "x"),
        ("x * 1", RULE_MUL_ONE, "x"),
        ("x * 0", RULE_MUL_ZERO, "0"),
    ],
)
def test_rule_positive_local_rewrite(
    cfg_factory: Any,
    source: str,
    rule: Any,
    expected_source: str,
) -> None:
    cfg = cfg_factory()
    expr = parse_expression(source, cfg)
    after = try_apply_rule(expr.root, rule)
    assert after is not None
    assert render_expr(after) == expected_source


@pytest.mark.parametrize("cfg_factory", [mode_a, mode_b])
def test_optimize_accepts_identity_rules_end_to_end(cfg_factory: Any) -> None:
    cfg = cfg_factory()
    result = optimize("(x + 0) * 1 - 0", cfg)
    assert result.accepted.source.replace(" ", "") in {"x", "(x)"}
    # Normalize via IR: accepted root should be the variable x.
    assert isinstance(result.accepted.root, Variable)
    assert result.accepted.root.name == "x"
    assert result.policy is CorrectnessPolicy.VERIFICATION_GUIDED
    assert result.accepted_steps
    assert not result.rejected_steps
    for step in result.accepted_steps:
        assert step.verification_result is not None
        assert (
            step.verification_result.status
            is VerificationStatus.EQUIVALENT_WITHIN_MODEL
        )
        assert step.decision is CandidateDecision.ACCEPTED


@pytest.mark.parametrize("cfg_factory", [mode_a, mode_b])
def test_mul_zero_folds_nested(cfg_factory: Any) -> None:
    cfg = cfg_factory()
    result = optimize("(x + y) * 0", cfg)
    assert isinstance(result.accepted.root, IntLiteral)
    assert result.accepted.root.value == 0
    assert any(step.rule_id == "identity.mul_zero" for step in result.accepted_steps)


# --- Negative / inapplicable --------------------------------------------------------


@pytest.mark.parametrize("cfg_factory", [mode_a, mode_b])
@pytest.mark.parametrize(
    ("source", "rule"),
    [
        ("x + 1", RULE_ADD_ZERO),
        ("0 + x", RULE_ADD_ZERO),  # left-zero form is not the specified rule
        ("x - 1", RULE_SUB_ZERO),
        ("x * 2", RULE_MUL_ONE),
        ("x * 1", RULE_MUL_ZERO),
        ("x + 0", RULE_SUB_ZERO),
        ("x", RULE_ADD_ZERO),
        ("1", RULE_MUL_ONE),
    ],
)
def test_rule_negative_inapplicable(
    cfg_factory: Any,
    source: str,
    rule: Any,
) -> None:
    cfg = cfg_factory()
    expr = parse_expression(source, cfg)
    assert try_apply_rule(expr.root, rule) is None


@pytest.mark.parametrize("cfg_factory", [mode_a, mode_b])
def test_no_applicable_rules_returns_original(cfg_factory: Any) -> None:
    cfg = cfg_factory()
    result = optimize("x + y * 2", cfg)
    assert result.accepted.source == result.original.source
    assert result.trace == ()


# --- Mode support -------------------------------------------------------------------


def test_rule_skipped_when_mode_not_supported() -> None:
    """A rule whose supported_modes exclude the active mode must not match."""
    restricted = RULE_ADD_ZERO.__class__(
        rule_id=RULE_ADD_ZERO.rule_id,
        name=RULE_ADD_ZERO.name,
        formal_description=RULE_ADD_ZERO.formal_description,
        preconditions=RULE_ADD_ZERO.preconditions,
        supported_modes=frozenset({SemanticMode.MODE_B}),
        verification_policy=RULE_ADD_ZERO.verification_policy,
    )
    matches = find_applicable_matches("x + 0", mode_a(), rules=(restricted,))
    assert matches == ()
    # Same rule still matches under Mode B.
    matches_b = find_applicable_matches("x + 0", mode_b(), rules=(restricted,))
    assert len(matches_b) == 1


# --- Verification gating ------------------------------------------------------------


def test_rejects_when_verifier_finds_counterexample() -> None:
    """A candidate that fails equivalence must not be accepted."""
    cfg = mode_a()
    # Inject a bogus rewrite implementation path by mocking verify_equivalence
    # to claim COUNTEREXAMPLE_FOUND for any generated candidate.
    real_verify = verify_equivalence

    def fake_verify(original: Any, candidate: Any, config: Any) -> VerificationResult:
        # Allow the first call structure but always reject.
        base = real_verify(original, candidate, config)
        return VerificationResult(
            status=VerificationStatus.COUNTEREXAMPLE_FOUND,
            mode=base.mode,
            bit_width=base.bit_width,
            timeout_seconds=base.timeout_seconds,
            original_source=base.original_source,
            candidate_source=base.candidate_source,
            counterexample=base.counterexample,
            solver_status=base.solver_status,
            reason="injected counterexample for gating test",
        )

    with patch(
        "veriforge.optimizer_engine.verify_equivalence",
        side_effect=fake_verify,
    ):
        result = optimize("x + 0", cfg)

    assert result.accepted.source == result.original.source
    assert result.rejected_steps
    assert not result.accepted_steps
    assert all(
        step.decision is CandidateDecision.REJECTED for step in result.rejected_steps
    )
    assert all(
        step.verification_result is not None
        and step.verification_result.status
        is VerificationStatus.COUNTEREXAMPLE_FOUND
        for step in result.rejected_steps
    )


@pytest.mark.parametrize(
    "status",
    [
        VerificationStatus.UNKNOWN,
        VerificationStatus.TIMEOUT,
        VerificationStatus.TRANSLATION_ERROR,
        VerificationStatus.VERIFICATION_ERROR,
        VerificationStatus.UNSUPPORTED,
        VerificationStatus.INVALID_INPUT,
        VerificationStatus.COUNTEREXAMPLE_VALIDATION_FAILED,
        VerificationStatus.SEMANTIC_DISAGREEMENT,
    ],
)
def test_does_not_accept_inconclusive_or_error_statuses(
    status: VerificationStatus,
) -> None:
    cfg = mode_a()

    def fake_verify(original: Any, candidate: Any, config: Any) -> VerificationResult:
        return VerificationResult(
            status=status,
            mode=config.mode,
            bit_width=None,
            timeout_seconds=config.limits.solver_timeout_seconds,
            original_source=getattr(original, "source", str(original)),
            candidate_source=getattr(candidate, "source", str(candidate)),
            reason=f"injected {status.value}",
        )

    with patch(
        "veriforge.optimizer_engine.verify_equivalence",
        side_effect=fake_verify,
    ):
        result = optimize("x * 1", cfg)

    assert result.accepted.source == result.original.source
    assert result.rejected_steps
    assert not result.accepted_steps
    assert result.rejected_steps[0].verification_result is not None
    assert result.rejected_steps[0].verification_result.status is status
    assert "rejected under verification-guided policy" in (
        result.rejected_steps[0].rejection_reason or ""
    )


def test_evaluation_only_policy_is_rejected() -> None:
    with pytest.raises(OptimizerError, match="EVALUATION_ONLY"):
        optimize(
            "x + 0",
            mode_a(),
            policy=CorrectnessPolicy.EVALUATION_ONLY,
        )


# --- Trace completeness -------------------------------------------------------------


def test_trace_records_rule_preconditions_and_sources() -> None:
    cfg = mode_a()
    result = optimize("x + 0", cfg)
    assert len(result.trace) == 1
    step = result.trace[0]
    assert step.rule_id == "identity.add_zero"
    assert step.rule_name == RULE_ADD_ZERO.name
    assert step.formal_description == RULE_ADD_ZERO.formal_description
    assert step.preconditions == RULE_ADD_ZERO.preconditions
    assert step.matched_preconditions == RULE_ADD_ZERO.preconditions
    assert step.before_source == "x + 0"
    assert step.after_source == "x"
    assert step.verification_policy is (
        VerificationPolicy.REQUIRE_EQUIVALENT_WITHIN_MODEL
    )
    assert step.verification_result is not None


def test_multi_step_trace_is_ordered() -> None:
    cfg = mode_a()
    result = optimize("(x + 0) * 1", cfg)
    assert len(result.accepted_steps) >= 2
    indices = [step.step_index for step in result.trace]
    assert indices == list(range(len(result.trace)))
    assert all(step.decision is CandidateDecision.ACCEPTED for step in result.trace)


# --- Mode A vs Mode B separate validation -------------------------------------------


def test_add_zero_verified_independently_in_each_mode() -> None:
    for cfg in (mode_a(), mode_b(8)):
        original = parse_expression("x + 0", cfg)
        candidate = parse_expression("x", cfg)
        verification = verify_equivalence(original, candidate, cfg)
        assert verification.status is VerificationStatus.EQUIVALENT_WITHIN_MODEL
        result = optimize(original, cfg)
        assert isinstance(result.accepted.root, Variable)


def test_mul_zero_verified_independently_in_each_mode() -> None:
    for cfg in (mode_a(), mode_b(8)):
        original = parse_expression("x * 0", cfg)
        candidate = parse_expression("0", cfg)
        verification = verify_equivalence(original, candidate, cfg)
        assert verification.status is VerificationStatus.EQUIVALENT_WITHIN_MODEL
        result = optimize(original, cfg)
        assert isinstance(result.accepted.root, IntLiteral)
        assert result.accepted.root.value == 0


# --- Rendering / IR helpers ---------------------------------------------------------


def test_render_and_expression_from_root_round_trip() -> None:
    cfg = mode_a()
    original = parse_expression("(x + y) * 2", cfg)
    rendered = render_expr(original.root)
    rebuilt = parse_expression(rendered, cfg)
    assert verify_equivalence(original, rebuilt, cfg).status is (
        VerificationStatus.EQUIVALENT_WITHIN_MODEL
    )
    expr = expression_from_root(original.root)
    assert "x" in expr.variables and "y" in expr.variables


def test_try_apply_rule_on_binary_node_directly() -> None:
    node = BinaryOp(
        op=BinaryOperator.ADD,
        left=Variable("x"),
        right=IntLiteral(0),
    )
    after = try_apply_rule(node, RULE_ADD_ZERO)
    assert after == Variable("x")
