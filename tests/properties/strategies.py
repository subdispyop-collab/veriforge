"""Shared Hypothesis strategies for Phase 4 property and differential tests."""

from __future__ import annotations

from hypothesis import strategies as st

from veriforge.config import SemanticConfiguration
from veriforge.models import (
    BinaryOp,
    BinaryOperator,
    Expr,
    IntLiteral,
    SemanticMode,
    UnaryOp,
    UnaryOperator,
    Variable,
)
from veriforge.optimizer_engine import render_expr

VAR_NAMES = ("x", "y", "z")


def mode_a_config() -> SemanticConfiguration:
    return SemanticConfiguration(mode=SemanticMode.MODE_A)


def mode_b_config(width: int = 8) -> SemanticConfiguration:
    # Narrow width keeps Mode B domains small for property tests.
    return SemanticConfiguration(mode=SemanticMode.MODE_B, bit_width=width)


@st.composite
def mode_a_literals(draw: st.DrawFn) -> IntLiteral:
    value = draw(st.integers(min_value=0, max_value=64))
    return IntLiteral(value=value)


@st.composite
def mode_b_literals(draw: st.DrawFn, width: int = 8) -> IntLiteral:
    maximum = (1 << width) - 1
    value = draw(st.integers(min_value=0, max_value=maximum))
    return IntLiteral(value=value)


@st.composite
def variables(draw: st.DrawFn) -> Variable:
    return Variable(name=draw(st.sampled_from(VAR_NAMES)))


def _binary(left: Expr, right: Expr, op: BinaryOperator) -> BinaryOp:
    return BinaryOp(op=op, left=left, right=right)


@st.composite
def mode_a_expr_trees(draw: st.DrawFn, max_leaves: int = 5) -> Expr:
    leaves = max(1, min(max_leaves, draw(st.integers(min_value=1, max_value=max_leaves))))

    def leaf() -> Expr:
        if draw(st.booleans()):
            return draw(variables())
        return draw(mode_a_literals())

    nodes: list[Expr] = [leaf() for _ in range(leaves)]
    while len(nodes) > 1:
        i = draw(st.integers(min_value=0, max_value=len(nodes) - 1))
        left = nodes.pop(i)
        j = draw(st.integers(min_value=0, max_value=len(nodes) - 1))
        right = nodes.pop(j)
        op = draw(
            st.sampled_from(
                [BinaryOperator.ADD, BinaryOperator.SUB, BinaryOperator.MUL]
            )
        )
        node: Expr = _binary(left, right, op)
        if draw(st.booleans()):
            node = UnaryOp(op=UnaryOperator.MINUS, operand=node)
        nodes.append(node)
    root = nodes[0]
    if draw(st.booleans()):
        root = UnaryOp(op=UnaryOperator.PLUS, operand=root)
    return root


@st.composite
def mode_b_expr_trees(draw: st.DrawFn, width: int = 8, max_leaves: int = 5) -> Expr:
    leaves = max(1, min(max_leaves, draw(st.integers(min_value=1, max_value=max_leaves))))

    def leaf() -> Expr:
        if draw(st.booleans()):
            return draw(variables())
        return draw(mode_b_literals(width=width))

    nodes: list[Expr] = [leaf() for _ in range(leaves)]
    while len(nodes) > 1:
        i = draw(st.integers(min_value=0, max_value=len(nodes) - 1))
        left = nodes.pop(i)
        j = draw(st.integers(min_value=0, max_value=len(nodes) - 1))
        right = nodes.pop(j)
        op = draw(
            st.sampled_from(
                [BinaryOperator.ADD, BinaryOperator.SUB, BinaryOperator.MUL]
            )
        )
        node: Expr = _binary(left, right, op)
        if draw(st.booleans()):
            node = UnaryOp(op=UnaryOperator.MINUS, operand=node)
        nodes.append(node)
    return nodes[0]


def collect_variables(node: Expr) -> frozenset[str]:
    if isinstance(node, Variable):
        return frozenset({node.name})
    if isinstance(node, IntLiteral):
        return frozenset()
    if isinstance(node, UnaryOp):
        return collect_variables(node.operand)
    if isinstance(node, BinaryOp):
        return collect_variables(node.left) | collect_variables(node.right)
    raise AssertionError(f"unexpected node: {type(node)!r}")


def render_source(node: Expr) -> str:
    return render_expr(node)


@st.composite
def mode_a_assignments(draw: st.DrawFn, names: frozenset[str]) -> dict[str, int]:
    return {
        name: draw(st.integers(min_value=-32, max_value=32)) for name in sorted(names)
    }


@st.composite
def mode_b_assignments(
    draw: st.DrawFn,
    names: frozenset[str],
    width: int = 8,
) -> dict[str, int]:
    maximum = (1 << width) - 1
    return {
        name: draw(st.integers(min_value=0, max_value=maximum))
        for name in sorted(names)
    }
