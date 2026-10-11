"""Localize the first differing sub-expression under a concrete assignment.

This is an engineering diagnostic. It is not claimed as a new verification
algorithm. A proposed repair is accepted only when the same oracle that
found the difference says the repaired candidate matches.
"""

from __future__ import annotations

from veriforge.config import SemanticConfiguration
from veriforge.independent_evaluator import evaluate_independent
from veriforge.independent_parser import IBinary, IExpr, ILit, IUnary, IVar, render_independent


def localize_difference(
    original: IExpr,
    candidate: IExpr,
    assignment: dict[str, int],
    config: SemanticConfiguration,
) -> tuple[IExpr, IExpr] | None:
    """Return the leftmost minimal sub-expression pair that differs."""

    left_value = evaluate_independent(original, assignment, config)
    right_value = evaluate_independent(candidate, assignment, config)
    if left_value == right_value:
        return None
    if isinstance(original, IBinary) and isinstance(candidate, IBinary):
        if original.op == candidate.op:
            left = localize_difference(original.left, candidate.left, assignment, config)
            right = localize_difference(original.right, candidate.right, assignment, config)
            if left is not None and _differs(original.left, candidate.left, assignment, config):
                return left
            if right is not None and _differs(original.right, candidate.right, assignment, config):
                return right
    if isinstance(original, IUnary) and isinstance(candidate, IUnary) and original.op == candidate.op:
        nested = localize_difference(original.operand, candidate.operand, assignment, config)
        if nested is not None:
            return nested
    return (original, candidate)


def propose_constant_repair(
    original: IExpr,
    candidate: IExpr,
    assignment: dict[str, int],
    config: SemanticConfiguration,
) -> IExpr | None:
    """If the minimal difference is two literals, use the original literal."""

    found = localize_difference(original, candidate, assignment, config)
    if found is None:
        return None
    left, right = found
    if isinstance(left, ILit) and isinstance(right, ILit):
        return _replace_first(candidate, right, left)
    return None


def _differs(
    left: IExpr,
    right: IExpr,
    assignment: dict[str, int],
    config: SemanticConfiguration,
) -> bool:
    return evaluate_independent(left, assignment, config) != evaluate_independent(
        right, assignment, config
    )


def _replace_first(node: IExpr, target: IExpr, replacement: IExpr) -> IExpr:
    if node is target:
        return replacement
    if isinstance(node, IUnary):
        return IUnary(op=node.op, operand=_replace_first(node.operand, target, replacement))
    if isinstance(node, IBinary):
        return IBinary(
            op=node.op,
            left=_replace_first(node.left, target, replacement),
            right=_replace_first(node.right, target, replacement),
        )
    return node


def describe_pair(left: IExpr, right: IExpr) -> str:
    return f"{render_independent(left)} vs {render_independent(right)}"
