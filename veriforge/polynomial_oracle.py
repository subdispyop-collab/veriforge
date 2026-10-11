"""Polynomial decision procedure for the arithmetic fragment over the integers.

Two expressions built from ``+``, ``-``, ``*``, unary ``+``/``-``, constants,
and variables denote the same function on all mathematical integers if and
only if their expanded polynomials are identical. Expansion is complete only
when it stays inside the declared term budget. Exceeding the budget yields
``not_computed`` and is not an equivalence result.

This oracle does not use Z3. It is not a decision procedure for unsigned
bit-vector functions: equal polynomials imply equal wraparound functions, but
unequal polynomials may still agree on a finite ring.
"""

from __future__ import annotations

from dataclasses import dataclass

from veriforge.independent_parser import IBinary, IExpr, ILit, IUnary, IVar

# Monomial: variable name to positive power, sorted by name.
Monomial = tuple[tuple[str, int], ...]
Poly = dict[Monomial, int]

DEFAULT_TERM_BUDGET = 4096


@dataclass(frozen=True, slots=True)
class PolynomialResult:
    verdict: str  # equivalent, counterexample, not_computed
    terms_original: int | None
    terms_candidate: int | None
    witness: dict[str, int] | None
    detail: str


def polynomial_compare(
    original: IExpr,
    candidate: IExpr,
    *,
    term_budget: int = DEFAULT_TERM_BUDGET,
) -> PolynomialResult:
    """Compare two independent expressions as integer polynomials."""

    try:
        left = _expand(original, term_budget)
        right = _expand(candidate, term_budget)
    except _BudgetExceeded as exc:
        return PolynomialResult(
            verdict="not_computed",
            terms_original=None,
            terms_candidate=None,
            witness=None,
            detail=str(exc),
        )
    if _canon(left) == _canon(right):
        return PolynomialResult(
            verdict="equivalent",
            terms_original=len(left),
            terms_candidate=len(right),
            witness=None,
            detail="expanded polynomials are identical",
        )
    witness = _witness(left, right)
    for name in sorted(_expr_names(original) | _expr_names(candidate)):
        witness.setdefault(name, 0)
    return PolynomialResult(
        verdict="counterexample",
        terms_original=len(left),
        terms_candidate=len(right),
        witness=witness,
        detail="expanded polynomials differ; witness evaluated on the difference",
    )


class _BudgetExceeded(Exception):
    pass


def _expand(node: IExpr, budget: int) -> Poly:
    if isinstance(node, ILit):
        return {(): node.value} if node.value != 0 else {}
    if isinstance(node, IVar):
        return {((node.name, 1),): 1}
    if isinstance(node, IUnary):
        inner = _expand(node.operand, budget)
        if node.op == "+":
            return inner
        if node.op == "-":
            return _scale(inner, -1)
        raise _BudgetExceeded(f"unsupported unary {node.op}")
    if isinstance(node, IBinary):
        left = _expand(node.left, budget)
        right = _expand(node.right, budget)
        if node.op == "+":
            return _add(left, right, budget)
        if node.op == "-":
            return _add(left, _scale(right, -1), budget)
        if node.op == "*":
            return _mul(left, right, budget)
        raise _BudgetExceeded(f"unsupported binary {node.op}")
    raise _BudgetExceeded(f"unsupported node {type(node).__name__}")


def _canon(poly: Poly) -> tuple[tuple[Monomial, int], ...]:
    return tuple(sorted((mono, coeff) for mono, coeff in poly.items() if coeff != 0))


def _guard(poly: Poly, budget: int) -> Poly:
    cleaned = {mono: coeff for mono, coeff in poly.items() if coeff != 0}
    if len(cleaned) > budget:
        raise _BudgetExceeded(
            f"polynomial term count {len(cleaned)} exceeds budget {budget}"
        )
    return cleaned


def _add(left: Poly, right: Poly, budget: int) -> Poly:
    out = dict(left)
    for mono, coeff in right.items():
        out[mono] = out.get(mono, 0) + coeff
    return _guard(out, budget)


def _scale(poly: Poly, factor: int) -> Poly:
    if factor == 0:
        return {}
    return {mono: coeff * factor for mono, coeff in poly.items()}


def _mul_mono(left: Monomial, right: Monomial) -> Monomial:
    powers: dict[str, int] = {}
    for name, power in left + right:
        powers[name] = powers.get(name, 0) + power
    return tuple(sorted((name, power) for name, power in powers.items() if power))


def _mul(left: Poly, right: Poly, budget: int) -> Poly:
    out: Poly = {}
    for m1, c1 in left.items():
        for m2, c2 in right.items():
            mono = _mul_mono(m1, m2)
            out[mono] = out.get(mono, 0) + c1 * c2
            if len(out) > budget * 4:
                # Intermediate products can cancel. Guard the blow-up anyway.
                raise _BudgetExceeded(
                    f"polynomial product exceeded intermediate budget {budget * 4}"
                )
    return _guard(out, budget)


def _expr_names(node: IExpr) -> set[str]:
    found: set[str] = set()

    def walk(current: IExpr) -> None:
        if isinstance(current, IVar):
            found.add(current.name)
        elif isinstance(current, IUnary):
            walk(current.operand)
        elif isinstance(current, IBinary):
            walk(current.left)
            walk(current.right)

    walk(node)
    return found


def _names(poly: Poly) -> list[str]:
    found: set[str] = set()
    for mono in poly:
        for name, _power in mono:
            found.add(name)
    return sorted(found)


def _eval_poly(poly: Poly, assignment: dict[str, int]) -> int:
    total = 0
    for mono, coeff in poly.items():
        term = coeff
        for name, power in mono:
            term *= assignment[name] ** power
        total += term
    return total


def _witness(left: Poly, right: Poly) -> dict[str, int]:
    """Find an integer assignment where the polynomials differ.

    Uses a base larger than the coefficient bound so distinct monomials
    cannot cancel (Kronecker substitution), then checks the difference.
    """

    diff = _add(left, _scale(right, -1), budget=10**9)
    names = _names(diff)
    if not names:
        # Constant difference. The empty assignment is the witness.
        return {}
    max_coeff = max(abs(coeff) for coeff in diff.values())
    base = max_coeff + 2
    assignment = {name: base ** (index + 1) for index, name in enumerate(names)}
    if _eval_poly(diff, assignment) == 0:
        # Fallback search. A nonzero integer polynomial has a small witness.
        for magnitude in range(0, 6):
            point = {name: magnitude for name in names}
            if _eval_poly(diff, point) != 0:
                return point
        raise RuntimeError("nonzero polynomial difference had no witness")
    return assignment
