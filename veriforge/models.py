"""Typed models used by Phase 1 parsing/evaluation and Phase 2 verification."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Mapping, Union

if TYPE_CHECKING:
    from veriforge.config import SemanticConfiguration


class SemanticMode(Enum):
    """Explicit semantic mode selection."""

    MODE_A = "mode_a"
    MODE_B = "mode_b"


class UnaryOperator(Enum):
    PLUS = "plus"
    MINUS = "minus"


class BinaryOperator(Enum):
    ADD = "add"
    SUB = "sub"
    MUL = "mul"


class VerificationStatus(Enum):
    """Explicit verifier outcomes. Never collapse these to a Boolean."""

    EQUIVALENT_WITHIN_MODEL = "equivalent_within_model"
    COUNTEREXAMPLE_FOUND = "counterexample_found"
    UNKNOWN = "unknown"
    TIMEOUT = "timeout"
    UNSUPPORTED = "unsupported"
    INVALID_INPUT = "invalid_input"
    TRANSLATION_ERROR = "translation_error"
    VERIFICATION_ERROR = "verification_error"


class CounterexampleValidationStatus(Enum):
    """Independent reference-evaluator check of a solver model."""

    CONFIRMED = "confirmed"
    DISCREPANCY = "discrepancy"
    UNVALIDATABLE = "unvalidatable"


@dataclass(frozen=True, slots=True)
class IntLiteral:
    """A non-Boolean integer constant accepted by the grammar."""

    value: int


@dataclass(frozen=True, slots=True)
class Variable:
    """A symbolic variable name (not a Python object lookup)."""

    name: str


@dataclass(frozen=True, slots=True)
class UnaryOp:
    op: UnaryOperator
    operand: Expr


@dataclass(frozen=True, slots=True)
class BinaryOp:
    op: BinaryOperator
    left: Expr
    right: Expr


Expr = Union[IntLiteral, Variable, UnaryOp, BinaryOp]


@dataclass(frozen=True, slots=True)
class Expression:
    """A successfully parsed expression in the internal representation."""

    source: str
    root: Expr
    variables: frozenset[str]


@dataclass(frozen=True, slots=True)
class ExpressionInput:
    """User-supplied expression text together with its semantic configuration."""

    source: str
    config: SemanticConfiguration


Assignment = Mapping[str, int]


@dataclass(frozen=True, slots=True)
class Counterexample:
    """A candidate counterexample with independent validation status.

    Only ``validation_status == CONFIRMED`` may be treated as a confirmed
    counterexample. Discrepancy and unvalidatable outcomes are defects or
    unresolved cases, not confirmed counterexamples.
    """

    assignment: Mapping[str, int]
    original_value: int | None
    candidate_value: int | None
    validation_status: CounterexampleValidationStatus
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """Outcome of an equivalence query under an encoded semantic model.

    ``status`` is always one of the explicit ``VerificationStatus`` values.
    A Boolean success/failure field is intentionally absent.
    """

    status: VerificationStatus
    mode: SemanticMode
    bit_width: int | None
    timeout_seconds: float
    original_source: str | None = None
    candidate_source: str | None = None
    counterexample: Counterexample | None = None
    solver_status: str | None = None
    reason: str | None = None
