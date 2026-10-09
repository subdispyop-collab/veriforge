"""Verifier must detect deliberately incorrect artificial mutations."""

from __future__ import annotations

import pytest

from veriforge.config import SemanticConfiguration
from veriforge.fuzzer_suite import (
    DEFAULT_MUTATION_SEED,
    analyze_mutation,
    generate_mutations,
    mutate_and_analyze,
)
from veriforge.models import (
    MutationCategory,
    SemanticMode,
    VerificationStatus,
)
from veriforge.parser_engine import parse_expression
from veriforge.reference_evaluator import evaluate


def mode_a() -> SemanticConfiguration:
    return SemanticConfiguration(mode=SemanticMode.MODE_A)


def mode_b(width: int = 32) -> SemanticConfiguration:
    return SemanticConfiguration(mode=SemanticMode.MODE_B, bit_width=width)


@pytest.mark.parametrize(
    "source,category",
    [
        ("x + y", MutationCategory.ADD_TO_SUB),
        ("x * y", MutationCategory.MUL_TO_ADD),
        ("x - y", MutationCategory.SWAP_SUB_OPERANDS),
        ("x + y", MutationCategory.DROP_RIGHT_OF_ADD),
        ("x + 0", MutationCategory.ZERO_TO_ONE),
        ("5", MutationCategory.LITERAL_PLUS_ONE),
    ],
)
@pytest.mark.parametrize("cfg_factory", [mode_a, mode_b])
def test_classic_incorrect_mutations_are_detected(
    source: str,
    category: MutationCategory,
    cfg_factory,
) -> None:
    cfg = cfg_factory()
    records = generate_mutations(
        source,
        cfg,
        seed=DEFAULT_MUTATION_SEED,
        categories=(category,),
    )
    assert records, f"expected at least one site for {category} on {source!r}"
    for record in records:
        analysis = analyze_mutation(record, cfg)
        assert analysis.accepted_into_production is False
        assert analysis.detected_as_non_equivalent is True
        assert (
            analysis.verification_result.status
            is not VerificationStatus.EQUIVALENT_WITHIN_MODEL
        )


@pytest.mark.parametrize("cfg_factory", [mode_a, mode_b])
def test_seeded_campaign_detects_all_generated_mutations(cfg_factory) -> None:
    cfg = cfg_factory()
    results = mutate_and_analyze(
        "(x + 3) * (y - 1)",
        cfg,
        seed=DEFAULT_MUTATION_SEED,
        max_mutations=20,
    )
    assert results
    # Some mutations can be semantically no-ops on particular sites (e.g.
    # DROP_RIGHT_OF_ADD when the right operand is literally 0, or swapping
    # equal sub-operands). Those are still artificial and labeled; filter to
    # cases where the reference evaluator can witness a difference.
    truly_incorrect: list = []
    for result in results:
        original = parse_expression(result.mutation.original_source, cfg)
        mutated = parse_expression(result.mutation.mutated_source, cfg)
        names = original.variables | mutated.variables
        # Probe a small fixed assignment grid for a witness.
        witnessed = False
        probes = _assignment_probes(names, cfg)
        for assignment in probes:
            if evaluate(original, assignment, cfg) != evaluate(
                mutated, assignment, cfg
            ):
                witnessed = True
                break
        if witnessed:
            truly_incorrect.append(result)

    assert truly_incorrect, "expected at least one witnessed-incorrect mutation"
    for result in truly_incorrect:
        assert result.detected_as_non_equivalent is True
        assert (
            result.verification_result.status
            is VerificationStatus.COUNTEREXAMPLE_FOUND
        )


def _assignment_probes(names: frozenset[str], cfg: SemanticConfiguration):
    ordered = sorted(names)
    if not ordered:
        return [{}]
    if cfg.mode is SemanticMode.MODE_A:
        values = [-2, -1, 0, 1, 2, 7]
    else:
        values = [0, 1, 2, min(7, cfg.max_unsigned), cfg.max_unsigned]
    # Cartesian product capped for small name sets.
    probes = [{}]
    for name in ordered:
        next_probes = []
        for base in probes:
            for value in values:
                row = dict(base)
                row[name] = value
                next_probes.append(row)
        probes = next_probes
        if len(probes) > 64:
            probes = probes[:64]
    return probes


def test_undetected_list_empty_for_forced_add_to_sub() -> None:
    """Regression-style: x+y vs x-y must be counterexample-found under Mode A."""
    cfg = mode_a()
    records = generate_mutations(
        "x + y",
        cfg,
        seed=0,
        categories=(MutationCategory.ADD_TO_SUB,),
    )
    analysis = analyze_mutation(records[0], cfg)
    assert analysis.verification_result.status is VerificationStatus.COUNTEREXAMPLE_FOUND
    assert analysis.detected_as_non_equivalent is True
