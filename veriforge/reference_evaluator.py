"""Reference evaluator implementing the documented Mode A / Mode B contract.

Independent of Z3. Never uses ``eval`` or ``exec``.
"""

from __future__ import annotations

from veriforge.config import SemanticConfiguration
from veriforge.exceptions import MissingVariableError
from veriforge.models import (
    Assignment,
    BinaryOp,
    BinaryOperator,
    Expression,
    Expr,
    IntLiteral,
    SemanticMode,
    UnaryOp,
    UnaryOperator,
    Variable,
)
from veriforge.semantics import bv_negate, validate_assignment_value, wrap_unsigned


def evaluate(
    expression: Expression,
    assignment: Assignment,
    config: SemanticConfiguration,
) -> int:
    """Evaluate ``expression`` under ``assignment`` in the selected mode.

    Mode A returns an unbounded mathematical integer.
    Mode B returns an unsigned integer in ``[0, 2^w - 1]``.
    """

    checked: dict[str, int] = {}
    for name in expression.variables:
        if name not in assignment:
            raise MissingVariableError(f"missing assignment for variable {name!r}")
        checked[name] = validate_assignment_value(name, assignment[name], config)

    return _eval_node(expression.root, checked, config)


def _eval_node(
    node: Expr,
    assignment: dict[str, int],
    config: SemanticConfiguration,
) -> int:
    if isinstance(node, IntLiteral):
        # Literals were validated at parse time against the same contract.
        if config.mode is SemanticMode.MODE_B:
            return wrap_unsigned(node.value, config)
        return node.value

    if isinstance(node, Variable):
        return assignment[node.name]

    if isinstance(node, UnaryOp):
        operand = _eval_node(node.operand, assignment, config)
        if node.op is UnaryOperator.PLUS:
            return operand
        if node.op is UnaryOperator.MINUS:
            if config.mode is SemanticMode.MODE_A:
                return -operand
            return bv_negate(operand, config)
        raise AssertionError(f"unexpected unary operator: {node.op}")

    if isinstance(node, BinaryOp):
        left = _eval_node(node.left, assignment, config)
        right = _eval_node(node.right, assignment, config)
        if config.mode is SemanticMode.MODE_A:
            return _mode_a_binary(node.op, left, right)
        return _mode_b_binary(node.op, left, right, config)

    raise AssertionError(f"unexpected expression node: {type(node)!r}")


def _mode_a_binary(op: BinaryOperator, left: int, right: int) -> int:
    if op is BinaryOperator.ADD:
        return left + right
    if op is BinaryOperator.SUB:
        return left - right
    if op is BinaryOperator.MUL:
        return left * right
    raise AssertionError(f"unexpected binary operator: {op}")


def _mode_b_binary(
    op: BinaryOperator,
    left: int,
    right: int,
    config: SemanticConfiguration,
) -> int:
    if op is BinaryOperator.ADD:
        return wrap_unsigned(left + right, config)
    if op is BinaryOperator.SUB:
        return wrap_unsigned(left - right, config)
    if op is BinaryOperator.MUL:
        return wrap_unsigned(left * right, config)
    raise AssertionError(f"unexpected binary operator: {op}")
