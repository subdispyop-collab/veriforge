"""Structural isolation of artificial mutations from production rules."""

from __future__ import annotations

import pytest

from veriforge.config import SemanticConfiguration
from veriforge.exceptions import OptimizerError
from veriforge.fuzzer_suite import (
    DEFAULT_MUTATION_SEED,
    analyze_mutation,
    assert_mutation_isolation,
    generate_mutations,
    mutate_and_analyze,
    mutation_categories,
    production_rule_ids,
)
from veriforge.models import (
    CorrectnessPolicy,
    MutationCategory,
    MutationRecord,
    SemanticMode,
)
from veriforge.optimizer_engine import default_rules, optimize


def mode_a() -> SemanticConfiguration:
    return SemanticConfiguration(mode=SemanticMode.MODE_A)


def test_mutation_categories_prefixed_and_disjoint_from_production() -> None:
    assert_mutation_isolation()
    prod = production_rule_ids()
    for category in mutation_categories():
        assert category.value.startswith("mutation.")
        assert category.value not in prod
    for rule in default_rules():
        assert not rule.rule_id.startswith("mutation.")


def test_optimize_still_rejects_evaluation_only() -> None:
    with pytest.raises(OptimizerError, match="fuzzer_suite"):
        optimize("x + 0", mode_a(), policy=CorrectnessPolicy.EVALUATION_ONLY)


def test_generated_records_are_artificial_with_id_and_method() -> None:
    records = generate_mutations("x + y * 2", mode_a(), seed=DEFAULT_MUTATION_SEED)
    assert records
    for record in records:
        assert record.artificial is True
        assert record.mutation_id
        assert record.generation_method.startswith("artificial_ast_rewrite:")
        assert record.seed == DEFAULT_MUTATION_SEED
        assert record.original_source
        assert record.mutated_source
        assert record.category.value.startswith("mutation.")


def test_generation_is_reproducible_for_fixed_seed() -> None:
    cfg = mode_a()
    first = generate_mutations(
        "(x + 1) * (y - 2)",
        cfg,
        seed=42,
        max_mutations=10,
    )
    second = generate_mutations(
        "(x + 1) * (y - 2)",
        cfg,
        seed=42,
        max_mutations=10,
    )
    assert first == second
    third = generate_mutations(
        "(x + 1) * (y - 2)",
        cfg,
        seed=43,
        max_mutations=10,
    )
    assert [r.mutation_id for r in first] != [r.mutation_id for r in third] or [
        r.mutated_source for r in first
    ] != [r.mutated_source for r in third]


def test_analysis_never_accepts_into_production() -> None:
    results = mutate_and_analyze("x + 1", mode_a(), seed=DEFAULT_MUTATION_SEED)
    assert results
    for result in results:
        assert result.policy is CorrectnessPolicy.EVALUATION_ONLY
        assert result.accepted_into_production is False
        assert result.mutation.artificial is True


def test_mutation_record_rejects_non_artificial_label() -> None:
    with pytest.raises(ValueError, match="artificial"):
        MutationRecord(
            mutation_id="mutation.literal_plus_one#0",
            category=MutationCategory.LITERAL_PLUS_ONE,
            generation_method="artificial_ast_rewrite:mutation.literal_plus_one",
            seed=0,
            original_source="1",
            mutated_source="2",
            site_path=(),
            artificial=False,
        )


def test_analyze_mutation_uses_verifier_not_optimize() -> None:
    records = generate_mutations(
        "x + y",
        mode_a(),
        seed=1,
        categories=(MutationCategory.ADD_TO_SUB,),
    )
    assert records
    analysis = analyze_mutation(records[0], mode_a())
    assert analysis.accepted_into_production is False
    assert analysis.verification_result is not None
