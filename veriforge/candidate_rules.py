"""Proposed arithmetic rules that are not in the production optimizer.

Production admission requires ``EQUIVALENT_WITHIN_MODEL`` from the Z3
verifier in both modes. This module records independent polynomial and
exhaustive checks. A pass here does not admit the rule into ``default_rules``.
"""

from __future__ import annotations

from dataclasses import dataclass

from veriforge.config import SemanticConfiguration
from veriforge.exhaustive_oracle import exhaustive_compare
from veriforge.independent_parser import parse_independent
from veriforge.models import SemanticMode
from veriforge.polynomial_oracle import polynomial_compare


@dataclass(frozen=True, slots=True)
class RuleCheck:
    rule_id: str
    description: str
    mode: str
    bit_width: int | None
    original_source: str
    candidate_source: str
    independent_verdict: str
    detail: str
    production_admission: str


def check_proposed_rules() -> tuple[RuleCheck, ...]:
    """Check the eight proposed rules and the mode-restricted failures."""

    specs = (
        ("distributivity", "a*(b+c) → a*b + a*c", "mode_a", None, "(x * (y + z))", "((x * y) + (x * z))"),
        ("factoring", "a*b + a*c → a*(b+c)", "mode_a", None, "((x * y) + (x * z))", "(x * (y + z))"),
        ("const_fold", "(2+3) → 5", "mode_a", None, "(2 + 3)", "5"),
        ("sub_self", "x - x → 0", "mode_a", None, "(x - x)", "0"),
        ("add_self", "x + x → 2*x", "mode_a", None, "(x + x)", "(x * 2)"),
        ("double_neg", "--x → x", "mode_a", None, "(-(-x))", "x"),
        ("neg_sub", "-(a-b) → b-a", "mode_a", None, "(-(x - y))", "(y - x)"),
        ("const_reassoc", "(x+2)+3 → x+5", "mode_a", None, "((x + 2) + 3)", "(x + 5)"),
        ("distributivity", "a*(b+c) → a*b + a*c", "mode_b", 4, "(x * (y + z))", "((x * y) + (x * z))"),
        ("factoring", "a*b + a*c → a*(b+c)", "mode_b", 4, "((x * y) + (x * z))", "(x * (y + z))"),
        ("const_fold", "(2+3) → 5", "mode_b", 4, "(2 + 3)", "5"),
        ("sub_self", "x - x → 0", "mode_b", 4, "(x - x)", "0"),
        ("add_self", "x + x → 2*x", "mode_b", 8, "(x + x)", "(x * 2)"),
        ("double_neg", "--x → x", "mode_b", 4, "(-(-x))", "x"),
        ("neg_sub", "-(a-b) → b-a", "mode_b", 4, "(-(x - y))", "(y - x)"),
        ("const_reassoc", "(x+2)+3 → x+5", "mode_b", 8, "((x + 2) + 3)", "(x + 5)"),
        ("add_self_width1", "x+x → 2*x is illegal at width 1", "mode_b", 1, "(x + x)", "(x * 2)"),
        ("const_reassoc_width2", "(x+2)+3 → x+5 is illegal at width 2", "mode_b", 2, "((x + 2) + 3)", "(x + 5)"),
    )
    results: list[RuleCheck] = []
    for rule_id, description, mode_name, width, original, candidate in specs:
        mode = SemanticMode.MODE_A if mode_name == "mode_a" else SemanticMode.MODE_B
        config = SemanticConfiguration(mode=mode, bit_width=width or 32)
        try:
            left = parse_independent(original, config)
            right = parse_independent(candidate, config)
        except Exception as exc:  # noqa: BLE001
            results.append(
                RuleCheck(
                    rule_id=rule_id,
                    description=description,
                    mode=mode_name,
                    bit_width=width,
                    original_source=original,
                    candidate_source=candidate,
                    independent_verdict="rejected_input",
                    detail=str(exc),
                    production_admission="not_admitted_bad_candidate_or_precondition",
                )
            )
            continue
        if mode is SemanticMode.MODE_A:
            compared = polynomial_compare(left.root, right.root)
            verdict = compared.verdict
            detail = compared.detail
        else:
            compared_b = exhaustive_compare(
                left.root, right.root, config, assignment_budget=65536
            )
            verdict = compared_b.verdict
            detail = compared_b.detail
        if verdict == "equivalent":
            admission = "not_admitted_production_z3_not_run"
        else:
            admission = "not_admitted_independent_check_failed"
        results.append(
            RuleCheck(
                rule_id=rule_id,
                description=description,
                mode=mode_name,
                bit_width=width,
                original_source=original,
                candidate_source=candidate,
                independent_verdict=verdict,
                detail=detail,
                production_admission=admission,
            )
        )
    return tuple(results)
