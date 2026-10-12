"""Mode B equivalence by the falling-factorial canonical form.

The univariate shape is the canonical representation attributed to Keller
and Olson, Duke Mathematical Journal 35(4):835–838, 1968, as stated in the
retrieved IACR eprint 2022/1364. That 1968 paper was not opened. The
attribution is second-hand. This module does not state a new theorem.

Several variables use the product basis. The argument that a coefficient
of ``prod (x_i)_{alpha_i}`` is free modulo
``2^{max(0, w - sum v_2(alpha_i!))}`` is the Newton identity plus
divisibility of falling factorials, written in ``research/NEW_METHOD_SPEC.md``.
It is not a second citation.

The producer expands and converts with Stirling numbers of the second kind.
``EQUIVALENT`` is returned only after ``canonical_certificate.check_certificate``
accepts a certificate whose residues are all zero. ``NOT_EQUIVALENT`` is
returned only after ``reference_evaluator.evaluate`` confirms a witness.
This module does not call Z3, cvc5, Alive2, or ``polynomial_oracle``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache

from veriforge.canonical_certificate import (
    CanonicalCertificate,
    check_certificate,
    iter_box,
)
from veriforge.config import SemanticConfiguration
from veriforge.exceptions import ParseError
from veriforge.independent_parser import (
    IBinary,
    IExpr,
    ILit,
    IUnary,
    IVar,
    parse_independent,
)
from veriforge.models import SemanticMode

TERM_BUDGET = 256
GRID_BUDGET = 4096
MAX_DEGREE = 12
MAX_VARIABLES = 6


class CanonicalStatus(Enum):
    EQUIVALENT = "EQUIVALENT"
    NOT_EQUIVALENT = "NOT_EQUIVALENT"
    UNKNOWN = "UNKNOWN"
    TIMEOUT = "TIMEOUT"
    UNSUPPORTED = "UNSUPPORTED"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class CanonicalDecision:
    status: CanonicalStatus
    width: int | None
    certificate: CanonicalCertificate | None
    witness: dict[str, int] | None
    checker_accepted: bool
    detail: str


class _BudgetExceeded(Exception):
    pass


class _TimedOut(Exception):
    pass


def decide_mode_b(
    original: str,
    candidate: str,
    config: SemanticConfiguration,
    *,
    term_budget: int = TERM_BUDGET,
    grid_budget: int = GRID_BUDGET,
    max_degree: int = MAX_DEGREE,
    max_variables: int = MAX_VARIABLES,
    timeout_seconds: float | None = None,
) -> CanonicalDecision:
    """Decide unsigned wraparound equivalence of two ``+`` ``-`` ``*`` expressions."""

    if config.mode is not SemanticMode.MODE_B:
        return CanonicalDecision(
            CanonicalStatus.UNSUPPORTED,
            None,
            None,
            None,
            False,
            "Mode A stays on the integer polynomial checker",
        )
    width = config.bit_width
    if width < 1:
        return CanonicalDecision(
            CanonicalStatus.UNSUPPORTED, None, None, None, False, "width must be at least 1"
        )
    limit = config.limits.solver_timeout_seconds if timeout_seconds is None else timeout_seconds
    deadline = time.perf_counter() + limit
    try:
        left = parse_independent(original, config).root
        right = parse_independent(candidate, config).root
    except ParseError as exc:
        return CanonicalDecision(
            CanonicalStatus.UNSUPPORTED, width, None, None, False, str(exc)
        )
    names = tuple(sorted(_names(left) | _names(right)))
    if len(names) > max_variables:
        return CanonicalDecision(
            CanonicalStatus.UNKNOWN,
            width,
            None,
            None,
            False,
            f"variable count {len(names)} exceeds {max_variables}",
        )
    degrees = _syntactic_degrees(left, right, names)
    if any(degree > max_degree for degree in degrees):
        return CanonicalDecision(
            CanonicalStatus.UNKNOWN,
            width,
            None,
            None,
            False,
            f"syntactic degree exceeds {max_degree}",
        )
    try:
        certificate = _certificate(
            left, right, names, degrees, width, term_budget, deadline
        )
    except _BudgetExceeded as exc:
        return CanonicalDecision(CanonicalStatus.UNKNOWN, width, None, None, False, str(exc))
    except _TimedOut:
        return CanonicalDecision(CanonicalStatus.TIMEOUT, width, None, None, False, "timeout")
    except Exception as exc:  # noqa: BLE001 — fail closed, never as EQUIVALENT
        return CanonicalDecision(
            CanonicalStatus.ERROR, width, None, None, False, exc.__class__.__name__
        )

    checked = check_certificate(
        left, right, certificate, grid_budget=grid_budget, deadline=deadline
    )
    if checked.reason == "timeout":
        confirmed = _confirm_if_nonzero(original, candidate, config, certificate)
        if confirmed is not None:
            return confirmed
        return CanonicalDecision(
            CanonicalStatus.TIMEOUT, width, certificate, None, False, "checker timeout"
        )
    if checked.reason == "grid_budget":
        confirmed = _confirm_if_nonzero(original, candidate, config, certificate)
        if confirmed is not None:
            return confirmed
        return CanonicalDecision(
            CanonicalStatus.UNKNOWN,
            width,
            certificate,
            None,
            False,
            "certificate grid exceeds budget and no confirmed counterexample",
        )
    if not checked.accepted or checked.all_residues_zero is None:
        return CanonicalDecision(
            CanonicalStatus.ERROR,
            width,
            certificate,
            None,
            False,
            f"certificate checker rejected the reduction: {checked.reason}",
        )
    if checked.all_residues_zero:
        return CanonicalDecision(
            CanonicalStatus.EQUIVALENT,
            width,
            certificate,
            None,
            True,
            "canonical residues are zero and the certificate checker accepted them",
        )
    confirmed = _confirm_if_nonzero(original, candidate, config, certificate)
    if confirmed is None:
        return CanonicalDecision(
            CanonicalStatus.ERROR,
            width,
            certificate,
            None,
            True,
            "nonzero canonical residue did not confirm under the reference evaluator",
        )
    return confirmed


def _confirm_if_nonzero(
    original: str,
    candidate: str,
    config: SemanticConfiguration,
    certificate: CanonicalCertificate,
) -> CanonicalDecision | None:
    nonzero = [term for term in certificate.terms if term[3] != 0]
    if not nonzero:
        return None
    alpha = min(nonzero, key=lambda term: (sum(term[0]), term[0]))[0]
    modulus = 1 << certificate.width
    witness = {
        name: exponent % modulus
        for name, exponent in zip(certificate.variables, alpha)
    }
    for name in certificate.variables:
        witness.setdefault(name, 0)
    if _reference_differs(original, candidate, witness, config):
        return CanonicalDecision(
            CanonicalStatus.NOT_EQUIVALENT,
            certificate.width,
            certificate,
            witness,
            True,
            "reference evaluator confirmed a wraparound counterexample",
        )
    return None


def _reference_differs(
    original: str,
    candidate: str,
    witness: dict[str, int],
    config: SemanticConfiguration,
) -> bool:
    from veriforge.parser_engine import parse_expression
    from veriforge.reference_evaluator import evaluate

    left = parse_expression(original, config)
    right = parse_expression(candidate, config)
    return evaluate(left, witness, config) != evaluate(right, witness, config)


def _certificate(
    left: IExpr,
    right: IExpr,
    names: tuple[str, ...],
    degrees: tuple[int, ...],
    width: int,
    term_budget: int,
    deadline: float,
) -> CanonicalCertificate:
    difference = _subtract(
        _expand(left, names, term_budget, deadline),
        _expand(right, names, term_budget, deadline),
        term_budget,
    )
    raw_by_alpha = _to_falling(difference, term_budget, deadline)
    for alpha in raw_by_alpha:
        if any(exponent > degree for exponent, degree in zip(alpha, degrees)):
            raise RuntimeError("falling factorial degree exceeded the syntactic bound")
    from veriforge.canonical_certificate import canonical_modulus

    terms = []
    for alpha in iter_box(degrees):
        if time.perf_counter() >= deadline:
            raise _TimedOut
        raw = raw_by_alpha.get(alpha, 0)
        modulus = canonical_modulus(alpha, width)
        terms.append((alpha, raw, modulus, raw % modulus))
    return CanonicalCertificate(
        width=width,
        variables=names,
        degrees=degrees,
        terms=tuple(terms),
    )


def _names(node: IExpr) -> set[str]:
    found: set[str] = set()
    stack = [node]
    while stack:
        current = stack.pop()
        if isinstance(current, IVar):
            found.add(current.name)
        elif isinstance(current, IUnary):
            stack.append(current.operand)
        elif isinstance(current, IBinary):
            stack.append(current.left)
            stack.append(current.right)
    return found


def _syntactic_degrees(
    left: IExpr, right: IExpr, names: tuple[str, ...]
) -> tuple[int, ...]:
    return tuple(
        max(a, b)
        for a, b in zip(_degree_vector(left, names), _degree_vector(right, names))
    )


def _degree_vector(node: IExpr, names: tuple[str, ...]) -> tuple[int, ...]:
    if isinstance(node, ILit):
        return tuple(0 for _ in names)
    if isinstance(node, IVar):
        return tuple(1 if node.name == name else 0 for name in names)
    if isinstance(node, IUnary):
        return _degree_vector(node.operand, names)
    if isinstance(node, IBinary):
        left = _degree_vector(node.left, names)
        right = _degree_vector(node.right, names)
        if node.op == "*":
            return tuple(a + b for a, b in zip(left, right))
        return tuple(max(a, b) for a, b in zip(left, right))
    raise RuntimeError(f"unexpected node {type(node).__name__}")


def _expand(
    node: IExpr,
    names: tuple[str, ...],
    budget: int,
    deadline: float,
) -> dict[tuple[int, ...], int]:
    if time.perf_counter() >= deadline:
        raise _TimedOut
    if isinstance(node, ILit):
        return {_zeros(names): node.value} if node.value != 0 else {}
    if isinstance(node, IVar):
        exponents = tuple(1 if node.name == name else 0 for name in names)
        return {exponents: 1}
    if isinstance(node, IUnary):
        inner = _expand(node.operand, names, budget, deadline)
        if node.op == "+":
            return inner
        if node.op == "-":
            return {key: -value for key, value in inner.items()}
        raise RuntimeError(f"unexpected unary {node.op}")
    if isinstance(node, IBinary):
        left = _expand(node.left, names, budget, deadline)
        right = _expand(node.right, names, budget, deadline)
        if node.op == "+":
            return _add(left, right, budget)
        if node.op == "-":
            return _subtract(left, right, budget)
        if node.op == "*":
            return _multiply(left, right, budget, deadline)
    raise RuntimeError(f"unexpected node {type(node).__name__}")


def _zeros(names: tuple[str, ...]) -> tuple[int, ...]:
    return tuple(0 for _ in names)


def _add(
    left: dict[tuple[int, ...], int],
    right: dict[tuple[int, ...], int],
    budget: int,
) -> dict[tuple[int, ...], int]:
    out = dict(left)
    for key, value in right.items():
        out[key] = out.get(key, 0) + value
    out = {key: value for key, value in out.items() if value != 0}
    if len(out) > budget:
        raise _BudgetExceeded(f"term count {len(out)} exceeds {budget}")
    return out


def _subtract(
    left: dict[tuple[int, ...], int],
    right: dict[tuple[int, ...], int],
    budget: int,
) -> dict[tuple[int, ...], int]:
    return _add(left, {key: -value for key, value in right.items()}, budget)


def _multiply(
    left: dict[tuple[int, ...], int],
    right: dict[tuple[int, ...], int],
    budget: int,
    deadline: float,
) -> dict[tuple[int, ...], int]:
    out: dict[tuple[int, ...], int] = {}
    for left_key, left_value in left.items():
        for right_key, right_value in right.items():
            if time.perf_counter() >= deadline:
                raise _TimedOut
            key = tuple(a + b for a, b in zip(left_key, right_key))
            out[key] = out.get(key, 0) + left_value * right_value
    out = {key: value for key, value in out.items() if value != 0}
    if len(out) > budget:
        raise _BudgetExceeded(f"term count {len(out)} exceeds {budget}")
    return out


def _to_falling(
    monomials: dict[tuple[int, ...], int],
    budget: int,
    deadline: float,
) -> dict[tuple[int, ...], int]:
    converted: dict[tuple[int, ...], int] = {}
    for exponents, coefficient in monomials.items():
        if time.perf_counter() >= deadline:
            raise _TimedOut
        partial: dict[tuple[int, ...], int] = {tuple(): 1}
        for position, power in enumerate(exponents):
            nxt: dict[tuple[int, ...], int] = {}
            for alpha, alpha_coeff in partial.items():
                for degree in range(power + 1):
                    stirling = _stirling_second(power, degree)
                    if stirling == 0:
                        continue
                    grown = alpha + (degree,)
                    nxt[grown] = nxt.get(grown, 0) + alpha_coeff * stirling
            partial = nxt
        for alpha, alpha_coeff in partial.items():
            converted[alpha] = converted.get(alpha, 0) + coefficient * alpha_coeff
        if len(converted) > budget:
            raise _BudgetExceeded(f"falling-factorial term count exceeds {budget}")
    return {key: value for key, value in converted.items() if value != 0}


@lru_cache(maxsize=None)
def _stirling_second(n: int, k: int) -> int:
    if k < 0 or n < 0 or k > n:
        return 0
    if n == 0 or k == n or k == 1:
        return 1 if n == k or (k == 1 and n >= 1) or n == 0 else 0
    return k * _stirling_second(n - 1, k) + _stirling_second(n - 1, k - 1)
