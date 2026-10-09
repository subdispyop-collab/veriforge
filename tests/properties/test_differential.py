"""Differential testing: verifier claims vs independent reference evaluator."""

from __future__ import annotations

import random

from hypothesis import given, settings, seed
from hypothesis import strategies as st

from veriforge.fuzzer_suite import (
    DEFAULT_MUTATION_SEED,
    generate_mutations,
    rebuild_mutated,
)
from veriforge.models import MutationCategory, VerificationStatus
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
SAMPLE_SEED = 20261009


def _sample_assignments_mode_a(
    names: frozenset[str],
    *,
    rng: random.Random,
    count: int = 12,
) -> list[dict[str, int]]:
    if not names:
        return [{}]
    samples = []
    for _ in range(count):
        samples.append(
            {name: rng.randint(-40, 40) for name in sorted(names)}
        )
    return samples


def _sample_assignments_mode_b(
    names: frozenset[str],
    width: int,
    *,
    rng: random.Random,
    count: int = 12,
) -> list[dict[str, int]]:
    if not names:
        return [{}]
    maximum = (1 << width) - 1
    samples = []
    for _ in range(count):
        samples.append(
            {name: rng.randint(0, maximum) for name in sorted(names)}
        )
    return samples


@seed(HYPOTHESIS_SEED)
@settings(max_examples=40, deadline=None)
@given(mode_a_expr_trees(max_leaves=4), mode_a_expr_trees(max_leaves=4))
def test_equivalent_claim_survives_reference_samples_mode_a(left, right) -> None:
    cfg = mode_a_config()
    left_expr = parse_expression(render_expr(left), cfg)
    right_expr = parse_expression(render_expr(right), cfg)
    result = verify_equivalence(left_expr, right_expr, cfg)
    if result.status is not VerificationStatus.EQUIVALENT_WITHIN_MODEL:
        return
    rng = random.Random(SAMPLE_SEED)
    names = left_expr.variables | right_expr.variables
    for assignment in _sample_assignments_mode_a(names, rng=rng):
        assert evaluate(left_expr, assignment, cfg) == evaluate(
            right_expr, assignment, cfg
        )


@seed(HYPOTHESIS_SEED)
@settings(max_examples=40, deadline=None)
@given(mode_b_expr_trees(width=8, max_leaves=4), mode_b_expr_trees(width=8, max_leaves=4))
def test_equivalent_claim_survives_reference_samples_mode_b(left, right) -> None:
    cfg = mode_b_config(width=8)
    left_expr = parse_expression(render_expr(left), cfg)
    right_expr = parse_expression(render_expr(right), cfg)
    result = verify_equivalence(left_expr, right_expr, cfg)
    if result.status is not VerificationStatus.EQUIVALENT_WITHIN_MODEL:
        return
    rng = random.Random(SAMPLE_SEED)
    names = left_expr.variables | right_expr.variables
    for assignment in _sample_assignments_mode_b(names, 8, rng=rng):
        assert evaluate(left_expr, assignment, cfg) == evaluate(
            right_expr, assignment, cfg
        )


@seed(HYPOTHESIS_SEED)
@settings(max_examples=30, deadline=None)
@given(mode_a_expr_trees(max_leaves=4))
def test_optimizer_accepted_matches_reference_differential_mode_a(tree) -> None:
    cfg = mode_a_config()
    source = f"({render_expr(tree)}) + 0"
    opt = optimize(source, cfg)
    assert (
        verify_equivalence(opt.original, opt.accepted, cfg).status
        is VerificationStatus.EQUIVALENT_WITHIN_MODEL
    )
    rng = random.Random(SAMPLE_SEED)
    for assignment in _sample_assignments_mode_a(opt.original.variables, rng=rng):
        assert evaluate(opt.original, assignment, cfg) == evaluate(
            opt.accepted, assignment, cfg
        )


@st.composite
def mode_a_source_for_mutation(draw: st.DrawFn) -> str:
    tree = draw(mode_a_expr_trees(max_leaves=3))
    # Ensure at least one binary op site for ADD_TO_SUB / similar by wrapping.
    return f"({render_expr(tree)}) + (x * 1)"


@seed(HYPOTHESIS_SEED)
@settings(max_examples=25, deadline=None)
@given(mode_a_source_for_mutation())
def test_witnessed_mutations_disagree_with_equivalent_claim(source: str) -> None:
    cfg = mode_a_config()
    records = generate_mutations(
        source,
        cfg,
        seed=DEFAULT_MUTATION_SEED,
        categories=(
            MutationCategory.ADD_TO_SUB,
            MutationCategory.MUL_TO_ADD,
            MutationCategory.LITERAL_PLUS_ONE,
        ),
        max_mutations=8,
    )
    rng = random.Random(SAMPLE_SEED)
    for record in records:
        original = parse_expression(record.original_source, cfg)
        mutated = rebuild_mutated(record, cfg)
        names = original.variables | mutated.variables
        witnessed_diff = False
        for assignment in _sample_assignments_mode_a(names, rng=rng, count=20):
            if evaluate(original, assignment, cfg) != evaluate(
                mutated, assignment, cfg
            ):
                witnessed_diff = True
                break
        if not witnessed_diff:
            continue
        status = verify_equivalence(original, mutated, cfg).status
        assert status is not VerificationStatus.EQUIVALENT_WITHIN_MODEL
