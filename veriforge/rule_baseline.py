"""Syntactic rule-only baseline using the four production identity rules.

The baseline does not call the SMT verifier. It predicts equivalence only when
both expressions reduce to the same rendered form under those rules. Any
other pair is ``not_handled``. ``not_handled`` is an abstention, not a
claim that the expressions differ.
"""

from __future__ import annotations

from veriforge.config import SemanticConfiguration
from veriforge.exceptions import ParseError
from veriforge.optimizer_engine import (
    expression_from_root,
    find_applicable_matches,
    render_expr,
    replace_at_path,
)
from veriforge.parser_engine import parse_expression


def reduce_identities(source: str, config: SemanticConfiguration, *, limit: int = 64) -> str:
    """Apply production identity rules to a fixed point and render the result."""

    current = parse_expression(source, config).root
    for _ in range(limit):
        expression = expression_from_root(current)
        matches = find_applicable_matches(expression, config)
        if not matches:
            break
        match = matches[0]
        current = replace_at_path(current, match.path, match.after)
    return render_expr(current)


def rule_only_predict(
    original_source: str,
    candidate_source: str,
    config: SemanticConfiguration,
) -> str:
    """Return ``equivalent`` or ``not_handled``.

    Parse failures return ``not_handled`` because the baseline has no
    verdict on inputs it cannot reduce.
    """

    try:
        left = reduce_identities(original_source, config)
        right = reduce_identities(candidate_source, config)
    except ParseError:
        return "not_handled"
    if left == right:
        return "equivalent"
    return "not_handled"
