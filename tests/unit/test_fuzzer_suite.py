"""Unit tests for the isolated Phase 4 mutation module."""

from __future__ import annotations

import pytest

from veriforge.config import SemanticConfiguration
from veriforge.exceptions import OptimizerError
from veriforge.fuzzer_suite import (
    DEFAULT_MUTATION_SEED,
    apply_mutation_at_site,
    assert_mutation_isolation,
    generate_mutations,
    mutate_and_analyze,
    mutation_categories,
    rebuild_mutated,
)
from veriforge.models import (
    CorrectnessPolicy,
    MutationAnalysisResult,
    MutationCategory,
    SemanticMode,
)
from veriforge.parser_engine import parse_expression


def mode_a() -> SemanticConfiguration:
    return SemanticConfiguration(mode=SemanticMode.MODE_A)


def mode_b(width: int = 8) -> SemanticConfiguration:
    return SemanticConfiguration(mode=SemanticMode.MODE_B, bit_width=width)


def test_default_seed_constant() -> None:
    assert DEFAULT_MUTATION_SEED == 20261009


def test_all_categories_exposed() -> None:
    cats = mutation_categories()
    assert set(cats) == set(MutationCategory)


def test_mode_b_literal_plus_one_skips_overflow_site() -> None:
    cfg = mode_b(width=8)
    expr = parse_expression("255", cfg)
    # Site at root cannot become 256 under Mode B.
    assert (
        apply_mutation_at_site(expr, MutationCategory.LITERAL_PLUS_ONE, (), cfg)
        is None
    )
    records = generate_mutations(
        "255",
        cfg,
        categories=(MutationCategory.LITERAL_PLUS_ONE,),
    )
    assert records == ()


def test_rebuild_mutated_roundtrip() -> None:
    cfg = mode_a()
    records = generate_mutations(
        "x + 2",
        cfg,
        seed=7,
        categories=(MutationCategory.LITERAL_PLUS_ONE,),
    )
    assert records
    rebuilt = rebuild_mutated(records[0], cfg)
    assert rebuilt.source == records[0].mutated_source


def test_analysis_result_rejects_production_acceptance_flag() -> None:
    cfg = mode_a()
    results = mutate_and_analyze(
        "x + 1",
        cfg,
        seed=0,
        categories=(MutationCategory.LITERAL_PLUS_ONE,),
    )
    assert results
    sample = results[0]
    with pytest.raises(ValueError, match="never accept"):
        MutationAnalysisResult(
            mutation=sample.mutation,
            config=cfg,
            policy=CorrectnessPolicy.EVALUATION_ONLY,
            verification_result=sample.verification_result,
            detected_as_non_equivalent=sample.detected_as_non_equivalent,
            accepted_into_production=True,
        )


def test_assert_mutation_isolation_ok() -> None:
    assert_mutation_isolation()


def test_max_mutations_negative_rejected() -> None:
    with pytest.raises(OptimizerError, match="max_mutations"):
        generate_mutations("x", mode_a(), max_mutations=-1)
