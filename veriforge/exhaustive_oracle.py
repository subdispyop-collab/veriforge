"""Exhaustive ground truth for unsigned bit-vector expressions.

The assignment space for ``k`` variables and width ``w`` is ``2**(w*k)``.
The oracle enumerates that space only when it is within ``assignment_budget``.
Otherwise the result is ``not_computed``. A sample is never labeled exhaustive.
"""

from __future__ import annotations

from dataclasses import dataclass

from veriforge.config import SemanticConfiguration
from veriforge.independent_evaluator import evaluate_independent
from veriforge.independent_parser import IExpr, variables_of
from veriforge.models import SemanticMode


@dataclass(frozen=True, slots=True)
class ExhaustiveResult:
    verdict: str  # equivalent, counterexample, not_computed, not_applicable
    width: int | None
    variable_count: int
    domain_size: int | None
    assignments_evaluated: int
    elapsed_seconds: float | None
    witness: dict[str, int] | None
    original_value: int | None
    candidate_value: int | None
    detail: str


def domain_size(width: int, variable_count: int) -> int:
    if variable_count < 0 or width < 1:
        raise ValueError("domain size requires a positive width and non-negative k")
    return 1 << (width * variable_count)


def exhaustive_compare(
    original: IExpr,
    candidate: IExpr,
    config: SemanticConfiguration,
    *,
    assignment_budget: int,
) -> ExhaustiveResult:
    """Compare two expressions on every Mode B assignment, when tractable."""

    from time import perf_counter

    if config.mode is not SemanticMode.MODE_B:
        return ExhaustiveResult(
            verdict="not_applicable",
            width=None,
            variable_count=len(variables_of(original) | variables_of(candidate)),
            domain_size=None,
            assignments_evaluated=0,
            elapsed_seconds=None,
            witness=None,
            original_value=None,
            candidate_value=None,
            detail="exhaustive enumeration is not a proof over unbounded integers",
        )
    names = tuple(sorted(variables_of(original) | variables_of(candidate)))
    width = config.bit_width
    size = domain_size(width, len(names))
    if size > assignment_budget:
        return ExhaustiveResult(
            verdict="not_computed",
            width=width,
            variable_count=len(names),
            domain_size=size,
            assignments_evaluated=0,
            elapsed_seconds=None,
            witness=None,
            original_value=None,
            candidate_value=None,
            detail=(
                f"domain 2^({width}*{len(names)})={size} exceeds "
                f"assignment budget {assignment_budget}"
            ),
        )
    modulus = 1 << width
    started = perf_counter()
    for index in range(size):
        assignment: dict[str, int] = {}
        cursor = index
        for name in names:
            assignment[name] = cursor % modulus
            cursor //= modulus
        left = evaluate_independent(original, assignment, config)
        right = evaluate_independent(candidate, assignment, config)
        if left != right:
            return ExhaustiveResult(
                verdict="counterexample",
                width=width,
                variable_count=len(names),
                domain_size=size,
                assignments_evaluated=index + 1,
                elapsed_seconds=perf_counter() - started,
                witness=assignment,
                original_value=left,
                candidate_value=right,
                detail="outputs differ on a fully enumerated assignment",
            )
    return ExhaustiveResult(
        verdict="equivalent",
        width=width,
        variable_count=len(names),
        domain_size=size,
        assignments_evaluated=size,
        elapsed_seconds=perf_counter() - started,
        witness=None,
        original_value=None,
        candidate_value=None,
        detail="outputs match on every assignment in the finite domain",
    )
