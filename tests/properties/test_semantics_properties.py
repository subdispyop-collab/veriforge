"""Hypothesis properties for Mode A / Mode B reference semantics."""

from __future__ import annotations

from hypothesis import given, settings, seed
from hypothesis import strategies as st

from veriforge.models import Expression
from veriforge.optimizer_engine import render_expr
from veriforge.parser_engine import parse_expression
from veriforge.reference_evaluator import evaluate
from veriforge.semantics import bv_negate, wrap_unsigned

from tests.properties.strategies import (
    collect_variables,
    mode_a_config,
    mode_a_expr_trees,
    mode_b_config,
    mode_b_expr_trees,
)

HYPOTHESIS_SEED = 20261009


@st.composite
def mode_a_expr_and_assignment(draw: st.DrawFn):
    tree = draw(mode_a_expr_trees(max_leaves=5))
    names = collect_variables(tree)
    assignment = {
        name: draw(st.integers(min_value=-48, max_value=48)) for name in sorted(names)
    }
    return tree, assignment


@st.composite
def mode_b_expr_and_assignment(draw: st.DrawFn, width: int = 8):
    tree = draw(mode_b_expr_trees(width=width, max_leaves=5))
    names = collect_variables(tree)
    maximum = (1 << width) - 1
    assignment = {
        name: draw(st.integers(min_value=0, max_value=maximum))
        for name in sorted(names)
    }
    return tree, assignment, width


@seed(HYPOTHESIS_SEED)
@settings(max_examples=100, deadline=None)
@given(mode_a_expr_and_assignment())
def test_mode_a_evaluation_is_deterministic(pair) -> None:
    tree, assignment = pair
    cfg = mode_a_config()
    expr = parse_expression(render_expr(tree), cfg)
    assert isinstance(expr, Expression)
    first = evaluate(expr, assignment, cfg)
    second = evaluate(expr, assignment, cfg)
    assert first == second
    assert isinstance(first, int)
    assert not isinstance(first, bool)


@seed(HYPOTHESIS_SEED)
@settings(max_examples=100, deadline=None)
@given(mode_b_expr_and_assignment(width=8))
def test_mode_b_results_stay_in_unsigned_domain(triple) -> None:
    tree, assignment, width = triple
    cfg = mode_b_config(width=width)
    expr = parse_expression(render_expr(tree), cfg)
    value = evaluate(expr, assignment, cfg)
    assert 0 <= value <= cfg.max_unsigned


@seed(HYPOTHESIS_SEED)
@settings(max_examples=80, deadline=None)
@given(st.integers(min_value=0, max_value=255))
def test_mode_b_wrap_and_negate_contract(value: int) -> None:
    cfg = mode_b_config(width=8)
    wrapped = wrap_unsigned(value + cfg.modulus, cfg)
    assert wrapped == value % cfg.modulus
    assert bv_negate(value, cfg) == (-value) % cfg.modulus
