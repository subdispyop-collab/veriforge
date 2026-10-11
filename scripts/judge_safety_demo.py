#!/usr/bin/env python3
"""Real executions for the judge safety demonstration.

Prints outcomes from the independent oracles and the status contract.
It does not print a canned solver transcript. Z3 is not required.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from veriforge.assurance import GateResult, audit_equivalence, combine_gates
from veriforge.config import SemanticConfiguration
from veriforge.models import SemanticMode, VerificationStatus


def show(title: str, report) -> None:
    print(f"== {title}")
    print(f"status={report.status.value}")
    print(f"establishing_method={report.establishing_method}")
    print(f"reason={report.reason}")
    if report.witness is not None:
        print(f"witness={report.witness}")
    for gate in report.gates:
        if gate.verdict in {"not_applicable", "unavailable"}:
            continue
        print(f"  gate {gate.name}: {gate.verdict} ({gate.detail})")
    print()


def main() -> None:
    mode_a = SemanticConfiguration(mode=SemanticMode.MODE_A)
    mode_b = SemanticConfiguration(mode=SemanticMode.MODE_B, bit_width=8)
    show(
        "correct rewrite x + 0 versus x, Mode A",
        audit_equivalence("(x + 0)", "x", mode_a, run_smt=True),
    )
    show(
        "incorrect rewrite x + 1 versus x + 2, Mode B width 8",
        audit_equivalence("(x + 1)", "(x + 2)", mode_b, run_smt=True),
    )
    show(
        "malformed decimal literal 01, Mode A",
        audit_equivalence("01", "1", mode_a, run_smt=True),
    )
    show(
        "domain over exhaustive budget, Mode B width 8, three variables, budget 16",
        audit_equivalence(
            "(x * (y + z))",
            "((x * y) + (x * z))",
            mode_b,
            exhaustive_budget=16,
            run_smt=True,
        ),
    )
    status, method, reason = combine_gates(
        [GateResult(name="production_smt", verdict="timeout", detail="synthetic timeout gate")]
    )
    print("== status-contract timeout fixture (not a live Z3 timeout)")
    print(f"status={status.value}")
    print(f"establishing_method={method}")
    print(f"reason={reason}")
    print(f"labeled_equivalent={status is VerificationStatus.EQUIVALENT_WITHIN_MODEL}")


if __name__ == "__main__":
    main()
