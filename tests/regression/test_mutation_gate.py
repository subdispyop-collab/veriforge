"""Regression: artificial mutations never enter the production optimizer path."""

from __future__ import annotations

import pytest

from veriforge.config import SemanticConfiguration
from veriforge.exceptions import OptimizerError
from veriforge.fuzzer_suite import (
    DEFAULT_MUTATION_SEED,
    analyze_mutation,
    assert_mutation_isolation,
    generate_mutations,
)
from veriforge.models import (
    CorrectnessPolicy,
    MutationCategory,
    SemanticMode,
    VerificationStatus,
)
from veriforge.optimizer_engine import default_rules, optimize


def mode_a() -> SemanticConfiguration:
    return SemanticConfiguration(mode=SemanticMode.MODE_A)


def test_regression_mutations_disjoint_from_production_rules() -> None:
    assert_mutation_isolation()
    production = {rule.rule_id for rule in default_rules()}
    for category in MutationCategory:
        assert category.value not in production


def test_regression_optimize_rejects_evaluation_only_policy() -> None:
    with pytest.raises(OptimizerError, match="fuzzer_suite"):
        optimize("x * 1", mode_a(), policy=CorrectnessPolicy.EVALUATION_ONLY)


def test_regression_incorrect_add_to_sub_detected_not_accepted() -> None:
    cfg = mode_a()
    records = generate_mutations(
        "a + b",
        cfg,
        seed=DEFAULT_MUTATION_SEED,
        categories=(MutationCategory.ADD_TO_SUB,),
    )
    assert len(records) == 1
    analysis = analyze_mutation(records[0], cfg)
    assert analysis.policy is CorrectnessPolicy.EVALUATION_ONLY
    assert analysis.accepted_into_production is False
    assert (
        analysis.verification_result.status
        is VerificationStatus.COUNTEREXAMPLE_FOUND
    )
    # Production path on the original still works and does not apply mutations.
    production = optimize(records[0].original_source, cfg)
    assert production.policy is CorrectnessPolicy.VERIFICATION_GUIDED
    for step in production.trace:
        assert not step.rule_id.startswith("mutation.")
