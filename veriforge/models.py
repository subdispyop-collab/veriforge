"""Typed models used by Phase 1 parsing and evaluation."""

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
