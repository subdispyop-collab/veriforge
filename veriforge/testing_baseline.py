"""Testing-only baseline: boundary values plus deterministic random inputs.

This baseline does not prove equivalence. A pair is called distinguished when
some tested assignment makes the independent evaluator disagree. Otherwise
the baseline reports ``undistinguished``, which is not an equivalence proof.

Mode B rejects assignments outside ``[0, 2**w - 1]``, including ``-1``.
Those points are not wrapped into the domain.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from veriforge.config import SemanticConfiguration
from veriforge.exceptions import DomainError, MissingVariableError
from veriforge.independent_evaluator import evaluate_independent
from veriforge.independent_parser import IExpr, variables_of
from veriforge.models import SemanticMode


@dataclass(frozen=True, slots=True)
class TestingResult:
    distinguished: bool
    budget: int
    evaluated: int
    skipped_out_of_domain: int
    witness: dict[str, int] | None
    elapsed_seconds: float
    detail: str


def boundary_pool(mode: SemanticMode, width: int | None) -> list[int]:
    """Return the preregistered boundary set for one variable."""

    if mode is SemanticMode.MODE_A:
        values = [-2, -1, 0, 1, 2]
        for value in list(values):
            values.extend((value - 1, value + 1))
        return sorted(set(values))
    if width is None or width < 1:
        raise ValueError("Mode B boundary values require a width")
    modulus = 1 << width
    seeds = [0, 1, 2, modulus - 1, modulus // 2, (modulus // 2) - 1]
    pool: set[int] = set()
    for seed in seeds:
        for neighbor in (seed - 1, seed, seed + 1):
            if 0 <= neighbor < modulus:
                pool.add(neighbor)
    return sorted(pool)


def testing_compare(
    original: IExpr,
    candidate: IExpr,
    config: SemanticConfiguration,
    *,
    budget: int,
    seed: int,
) -> TestingResult:
    """Search up to ``budget`` in-domain assignments for a difference."""

    from time import perf_counter

    if budget < 1:
        raise ValueError("budget must be positive")
    names = tuple(sorted(variables_of(original) | variables_of(candidate)))
    started = perf_counter()
    if not names:
        try:
            left = evaluate_independent(original, {}, config)
            right = evaluate_independent(candidate, {}, config)
        except (DomainError, MissingVariableError) as exc:
            return TestingResult(
                distinguished=False,
                budget=budget,
                evaluated=0,
                skipped_out_of_domain=0,
                witness=None,
                elapsed_seconds=perf_counter() - started,
                detail=f"constant expressions could not be evaluated: {exc}",
            )
        return TestingResult(
            distinguished=left != right,
            budget=budget,
            evaluated=1,
            skipped_out_of_domain=0,
            witness={} if left != right else None,
            elapsed_seconds=perf_counter() - started,
            detail="constant expressions compared",
        )

    pool = boundary_pool(config.mode, config.bit_width if config.mode is SemanticMode.MODE_B else None)
    plans: list[dict[str, int]] = []
    seen: set[tuple[int, ...]] = set()

    def add(assignment: dict[str, int]) -> None:
        key = tuple(assignment[name] for name in names)
        if key in seen:
            return
        seen.add(key)
        plans.append(dict(assignment))

    # One variable varies across the boundary pool; the others stay at 0
    # when 0 is legal, which it is in both modes.
    for name in names:
        for value in pool:
            assignment = {other: 0 for other in names}
            assignment[name] = value
            add(assignment)
    # Diagonal boundary tuples.
    for value in pool:
        add({name: value for name in names})

    rng = random.Random(seed)
    if config.mode is SemanticMode.MODE_B:
        modulus = 1 << config.bit_width
        while len(plans) < budget:
            add({name: rng.randrange(modulus) for name in names})
            if len(seen) >= modulus ** len(names):
                break
    else:
        # Bounded random integers. This is a sample, not a proof.
        span = 50
        guard = 0
        while len(plans) < budget and guard < budget * 20:
            guard += 1
            add({name: rng.randint(-span, span) for name in names})

    evaluated = 0
    skipped = 0
    for assignment in plans[:budget]:
        try:
            left = evaluate_independent(original, assignment, config)
            right = evaluate_independent(candidate, assignment, config)
        except DomainError:
            skipped += 1
            continue
        evaluated += 1
        if left != right:
            return TestingResult(
                distinguished=True,
                budget=budget,
                evaluated=evaluated,
                skipped_out_of_domain=skipped,
                witness=assignment,
                elapsed_seconds=perf_counter() - started,
                detail="testing baseline found a differentiating assignment",
            )
    return TestingResult(
        distinguished=False,
        budget=budget,
        evaluated=evaluated,
        skipped_out_of_domain=skipped,
        witness=None,
        elapsed_seconds=perf_counter() - started,
        detail="testing baseline did not distinguish the expressions",
    )
