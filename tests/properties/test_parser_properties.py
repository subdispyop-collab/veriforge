"""Hypothesis properties for the parser under the locked grammar contract."""

from __future__ import annotations

from hypothesis import given, settings, seed

from veriforge.models import Expression
from veriforge.optimizer_engine import expression_from_root, render_expr
from veriforge.parser_engine import parse_expression

from tests.properties.strategies import (
    collect_variables,
    mode_a_config,
    mode_a_expr_trees,
    mode_b_config,
    mode_b_expr_trees,
)

# Fixed Hypothesis seed for reproducible Phase 4 property runs.
HYPOTHESIS_SEED = 20261009


@seed(HYPOTHESIS_SEED)
@settings(max_examples=80, deadline=None)
@given(mode_a_expr_trees(max_leaves=5))
def test_mode_a_render_parse_roundtrip_preserves_ir(tree) -> None:
    cfg = mode_a_config()
    source = render_expr(tree)
    parsed = parse_expression(source, cfg)
    assert isinstance(parsed, Expression)
    assert parsed.variables == collect_variables(tree)
    # Re-render of parsed IR must parse again to the same structure.
    again = parse_expression(render_expr(parsed.root), cfg)
    assert again.root == parsed.root


@seed(HYPOTHESIS_SEED)
@settings(max_examples=80, deadline=None)
@given(mode_b_expr_trees(width=8, max_leaves=5))
def test_mode_b_render_parse_roundtrip_preserves_ir(tree) -> None:
    cfg = mode_b_config(width=8)
    source = render_expr(tree)
    parsed = parse_expression(source, cfg)
    assert parsed.variables == collect_variables(tree)
    again = parse_expression(render_expr(parsed.root), cfg)
    assert again.root == parsed.root


@seed(HYPOTHESIS_SEED)
@settings(max_examples=40, deadline=None)
@given(mode_a_expr_trees(max_leaves=4))
def test_expression_from_root_source_is_reparsable(tree) -> None:
    cfg = mode_a_config()
    expr = expression_from_root(tree)
    parsed = parse_expression(expr.source, cfg)
    assert parsed.root == expr.root
