"""Regression: verification-guided optimizer must not accept non-equivalent candidates.

These cases lock the Phase 3 acceptance gate. They are not the Phase 4 mutation
module; they only assert that inconclusive or disproved verification outcomes
never produce an accepted rewrite on the production path.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from veriforge.config import SemanticConfiguration
from veriforge.models import (
    CandidateDecision,
    CorrectnessPolicy,
    SemanticMode,
    VerificationResult,
    VerificationStatus,
)
from veriforge.optimizer_engine import optimize
from veriforge.parser_engine import parse_expression
from veriforge.verifier_engine import verify_equivalence


def mode_a() -> SemanticConfiguration:
    return SemanticConfiguration(mode=SemanticMode.MODE_A)


def mode_b() -> SemanticConfiguration:
    return SemanticConfiguration(mode=SemanticMode.MODE_B, bit_width=32)


@pytest.mark.parametrize("cfg_factory", [mode_a, mode_b])
def test_regression_identity_rules_remain_equivalent(cfg_factory: Any) -> None:
    """Accepted identity rewrites stay equivalent under the active mode."""
    cfg = cfg_factory()
    cases = [
        ("x + 0", "x"),
        ("x - 0", "x"),
        ("x * 1", "x"),
        ("x * 0", "0"),
        ("(a + 0) * 1 - 0", "a"),
    ]
    for source, expected_source in cases:
        result = optimize(source, cfg)
        assert result.policy is CorrectnessPolicy.VERIFICATION_GUIDED
        verification = verify_equivalence(result.original, result.accepted, cfg)
        assert verification.status is VerificationStatus.EQUIVALENT_WITHIN_MODEL
        expected_expr = parse_expression(expected_source, cfg)
        assert (
            verify_equivalence(result.accepted, expected_expr, cfg).status
            is VerificationStatus.EQUIVALENT_WITHIN_MODEL
        )


@pytest.mark.parametrize(
    "bad_status",
    [
        VerificationStatus.COUNTEREXAMPLE_FOUND,
        VerificationStatus.UNKNOWN,
        VerificationStatus.TIMEOUT,
        VerificationStatus.VERIFICATION_ERROR,
    ],
)
@pytest.mark.parametrize("cfg_factory", [mode_a, mode_b])
def test_regression_non_equivalent_statuses_never_accepted(
    bad_status: VerificationStatus,
    cfg_factory: Any,
) -> None:
    cfg = cfg_factory()

    def fake_verify(original: Any, candidate: Any, config: Any) -> VerificationResult:
        return VerificationResult(
            status=bad_status,
            mode=config.mode,
            bit_width=config.bit_width if config.mode is SemanticMode.MODE_B else None,
            timeout_seconds=config.limits.solver_timeout_seconds,
            original_source=getattr(original, "source", None),
            candidate_source=getattr(candidate, "source", None),
            reason=f"regression injection: {bad_status.value}",
        )

    with patch(
        "veriforge.optimizer_engine.verify_equivalence",
        side_effect=fake_verify,
    ):
        result = optimize("x + 0", cfg)

    assert result.accepted.source == result.original.source
    assert result.accepted_steps == ()
    assert result.rejected_steps
    for step in result.rejected_steps:
        assert step.decision is CandidateDecision.REJECTED
        assert step.verification_result is not None
        assert step.verification_result.status is bad_status
