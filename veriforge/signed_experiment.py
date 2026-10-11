"""Experimental signed fixed-width evaluation. Not a production mode.

Mode B remains unsigned. This module is a separate semantics used only to
record what a signed interpretation would do. It is not selected by
``SemanticMode`` and it is not accepted by the production optimizer.
"""

from __future__ import annotations

from veriforge.independent_parser import IBinary, IExpr, ILit, IUnary, IVar


def signed_domain(width: int) -> tuple[int, int]:
    half = 1 << (width - 1)
    return -half, half - 1


def signed_wrap(value: int, width: int) -> int:
    """Two's-complement wrap into ``[-2**(w-1), 2**(w-1) - 1]``."""

    modulus = 1 << width
    reduced = value % modulus
    half = 1 << (width - 1)
    if reduced >= half:
        return reduced - modulus
    return reduced


def evaluate_signed(node: IExpr, assignment: dict[str, int], width: int) -> int:
    """Evaluate under signed wrap. Literals must already lie in the signed domain."""

    low, high = signed_domain(width)
    if isinstance(node, ILit):
        if node.value < low or node.value > high:
            raise ValueError(
                f"signed literal {node.value} outside [{low}, {high}] for width {width}"
            )
        return node.value
    if isinstance(node, IVar):
        value = assignment[node.name]
        if value < low or value > high:
            raise ValueError(f"signed assignment {value} outside [{low}, {high}]")
        return value
    if isinstance(node, IUnary):
        operand = evaluate_signed(node.operand, assignment, width)
        if node.op == "+":
            return operand
        if node.op == "-":
            return signed_wrap(-operand, width)
        raise ValueError(node.op)
    if isinstance(node, IBinary):
        left = evaluate_signed(node.left, assignment, width)
        right = evaluate_signed(node.right, assignment, width)
        if node.op == "+":
            return signed_wrap(left + right, width)
        if node.op == "-":
            return signed_wrap(left - right, width)
        if node.op == "*":
            return signed_wrap(left * right, width)
        raise ValueError(node.op)
    raise ValueError(type(node).__name__)
