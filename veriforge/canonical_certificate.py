"""Independent check of a falling-factorial certificate.

The checker recomputes Newton coefficients from integer evaluations and
forward differences. It does not expand monomials, does not call Stirling
numbers, and does not call Z3, cvc5, Alive2, or ``polynomial_oracle``.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from itertools import product

from veriforge.independent_parser import IBinary, IExpr, ILit, IUnary, IVar


@dataclass(frozen=True, slots=True)
class CanonicalCertificate:
    """Canonical falling-factorial coefficients of one integer difference.

    ``terms`` lists every multiindex in the syntactic degree box, in
    lexicographic order. ``raw_coefficient`` is the integer Newton
    coefficient of ``prod (x_i)_{alpha_i}``. ``residue`` is that
    coefficient reduced modulo ``modulus``.
    """

    width: int
    variables: tuple[str, ...]
    degrees: tuple[int, ...]
    terms: tuple[tuple[tuple[int, ...], int, int, int], ...]


@dataclass(frozen=True, slots=True)
class CheckResult:
    accepted: bool
    all_residues_zero: bool | None
    reason: str


def factorial_valuation_2(n: int) -> int:
    """2-adic valuation of ``n!``. Separate from the producer on purpose."""

    if n < 0:
        raise ValueError("factorial valuation is defined for n >= 0")
    valuation = 0
    power = 2
    while power <= n:
        valuation += n // power
        power *= 2
    return valuation


def canonical_modulus(alpha: tuple[int, ...], width: int) -> int:
    """Modulus ``2^{max(0, w - sum v_2(alpha_i!))}`` for one multiindex."""

    if width < 1:
        raise ValueError("width must be at least 1")
    valuation = sum(factorial_valuation_2(exponent) for exponent in alpha)
    power = width - valuation
    if power < 0:
        power = 0
    return 1 << power


def iter_box(degrees: tuple[int, ...]):
    if not degrees:
        yield tuple()
        return
    ranges = [range(degree + 1) for degree in degrees]
    yield from product(*ranges)


def check_certificate(
    original: IExpr,
    candidate: IExpr,
    certificate: CanonicalCertificate,
    *,
    grid_budget: int,
    deadline: float,
) -> CheckResult:
    """Accept the certificate only when recomputed coefficients match."""

    if certificate.width < 1:
        return CheckResult(False, None, "width")
    if len(certificate.variables) != len(certificate.degrees):
        return CheckResult(False, None, "degree_mismatch")
    names = tuple(sorted(certificate.variables))
    if names != certificate.variables:
        return CheckResult(False, None, "degree_mismatch")
    degrees = syntactic_degrees(original, candidate, names)
    if degrees != certificate.degrees:
        return CheckResult(False, None, "degree_mismatch")
    size = 1
    for degree in degrees:
        size *= degree + 1
        if size > grid_budget:
            return CheckResult(False, None, "grid_budget")
    if time.perf_counter() >= deadline:
        return CheckResult(False, None, "timeout")
    try:
        values = _evaluate_grid(original, candidate, names, degrees, deadline)
    except _CheckerTimeout:
        return CheckResult(False, None, "timeout")
    expected = []
    all_zero = True
    for alpha in iter_box(degrees):
        if time.perf_counter() >= deadline:
            return CheckResult(False, None, "timeout")
        difference = _forward_difference(values, alpha)
        divisor = math.prod(math.factorial(exponent) for exponent in alpha)
        if divisor == 0 or difference % divisor != 0:
            return CheckResult(False, None, "not_divisible")
        raw = difference // divisor
        modulus = canonical_modulus(alpha, certificate.width)
        residue = raw % modulus
        if residue != 0:
            all_zero = False
        expected.append((alpha, raw, modulus, residue))
    if tuple(expected) != certificate.terms:
        return _mismatch(expected, certificate.terms)
    return CheckResult(True, all_zero, "accepted")


def syntactic_degrees(
    original: IExpr,
    candidate: IExpr,
    variables: tuple[str, ...],
) -> tuple[int, ...]:
    left = _degree_vector(original, variables)
    right = _degree_vector(candidate, variables)
    return tuple(max(a, b) for a, b in zip(left, right))


class _CheckerTimeout(Exception):
    pass


def _degree_vector(node: IExpr, variables: tuple[str, ...]) -> tuple[int, ...]:
    if isinstance(node, ILit):
        return tuple(0 for _ in variables)
    if isinstance(node, IVar):
        return tuple(1 if node.name == name else 0 for name in variables)
    if isinstance(node, IUnary):
        return _degree_vector(node.operand, variables)
    if isinstance(node, IBinary):
        left = _degree_vector(node.left, variables)
        right = _degree_vector(node.right, variables)
        if node.op == "*":
            return tuple(a + b for a, b in zip(left, right))
        if node.op in {"+", "-"}:
            return tuple(max(a, b) for a, b in zip(left, right))
    raise ValueError(f"unsupported node in degree walk: {type(node).__name__}")


def _integer_value(node: IExpr, assignment: dict[str, int]) -> int:
    if isinstance(node, ILit):
        return node.value
    if isinstance(node, IVar):
        return assignment[node.name]
    if isinstance(node, IUnary):
        value = _integer_value(node.operand, assignment)
        if node.op == "+":
            return value
        if node.op == "-":
            return -value
    if isinstance(node, IBinary):
        left = _integer_value(node.left, assignment)
        right = _integer_value(node.right, assignment)
        if node.op == "+":
            return left + right
        if node.op == "-":
            return left - right
        if node.op == "*":
            return left * right
    raise ValueError(f"unsupported node in integer evaluation: {type(node).__name__}")


def _evaluate_grid(
    original: IExpr,
    candidate: IExpr,
    variables: tuple[str, ...],
    degrees: tuple[int, ...],
    deadline: float,
) -> dict[tuple[int, ...], int]:
    values: dict[tuple[int, ...], int] = {}
    ranges = [range(degree + 1) for degree in degrees] or [()]
    points = product(*ranges) if degrees else [()]
    for point in points:
        if time.perf_counter() >= deadline:
            raise _CheckerTimeout
        assignment = {name: int(value) for name, value in zip(variables, point)}
        values[tuple(point)] = _integer_value(original, assignment) - _integer_value(
            candidate, assignment
        )
    return values


def _forward_difference(values: dict[tuple[int, ...], int], alpha: tuple[int, ...]) -> int:
    if not alpha:
        return values[()]
    total = 0
    for beta in product(*[range(exponent + 1) for exponent in alpha]):
        sign_exponent = sum(a - b for a, b in zip(alpha, beta))
        sign = -1 if sign_exponent % 2 else 1
        multiplier = math.prod(math.comb(a, b) for a, b in zip(alpha, beta))
        total += sign * multiplier * values[beta]
    return total


def _mismatch(
    expected: list[tuple[tuple[int, ...], int, int, int]],
    actual: tuple[tuple[tuple[int, ...], int, int, int], ...],
) -> CheckResult:
    if len(expected) != len(actual):
        return CheckResult(False, None, "box_mismatch")
    for got, claimed in zip(expected, actual):
        if got[0] != claimed[0]:
            return CheckResult(False, None, "box_mismatch")
        if got[2] != claimed[2]:
            return CheckResult(False, None, "modulus_mismatch")
        if got[1] != claimed[1]:
            return CheckResult(False, None, "coefficient_mismatch")
        if got[3] != claimed[3]:
            return CheckResult(False, None, "residue_mismatch")
    return CheckResult(False, None, "coefficient_mismatch")
