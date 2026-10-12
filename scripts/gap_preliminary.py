#!/usr/bin/env python3
"""Bounded probes of the existing decision procedures.

Writes only experiments/reports/gap-preliminary/probe.json.
Does not modify production modules or historical result files.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "experiments" / "reports" / "gap-preliminary" / "probe.json"


def main() -> int:
    from veriforge.config import SemanticConfiguration
    from veriforge.falling_factorial import (
        GRID_BUDGET,
        MAX_VARIABLES,
        TERM_BUDGET,
        decide_mode_b,
    )
    from veriforge.independent_parser import parse_independent
    from veriforge.models import SemanticMode
    from veriforge.polynomial_oracle import polynomial_compare
    from veriforge.verifier_engine import verify_equivalence_timed

    names = ["a", "b", "c", "d", "e", "f", "g"]
    factor = "(" + "+".join(names[:6]) + ")"
    # Six factors: syntactic degree 6 on six variables.
    power = "*".join([factor] * 6)
    null_product = "(a*(a-1))*(b*(b-1))*(c*(c-1))"
    seven = "(" + "+".join(names) + ")"

    probes = [
        ("add_self_zero", "(a+a)", "0", (1, 2, 4, 8, 32)),
        ("falling_pair", "(a*(a-1))", "0", (1, 4)),
        ("three_falling", null_product, "0", (1, 4)),
        ("seven_variables", seven, "0", (1,)),
        ("degree_six_vs_self", power, power, (4,)),
        ("degree_six_vs_zero", power, "0", (4,)),
    ]

    rows = []
    for family, left, right, widths in probes:
        for width in widths:
            config = SemanticConfiguration(mode=SemanticMode.MODE_B, bit_width=width)
            poly_config = SemanticConfiguration(mode=SemanticMode.MODE_A, bit_width=width)
            started = time.perf_counter()
            decision = decide_mode_b(left, right, config)
            canonical_seconds = time.perf_counter() - started
            polynomial_verdict = None
            polynomial_detail = None
            try:
                original = parse_independent(left, poly_config).root
                candidate = parse_independent(right, poly_config).root
                compared = polynomial_compare(original, candidate, term_budget=4096)
                polynomial_verdict = compared.verdict
                polynomial_detail = compared.detail
            except Exception as exc:  # noqa: BLE001
                polynomial_verdict = f"error:{exc.__class__.__name__}"
                polynomial_detail = str(exc)
            z3_status = None
            z3_seconds = None
            try:
                z3_start = time.perf_counter()
                timed = verify_equivalence_timed(left, right, config)
                z3_seconds = time.perf_counter() - z3_start
                z3_status = timed.result.status.value
            except Exception as exc:  # noqa: BLE001
                z3_status = f"error:{exc.__class__.__name__}"
            row = {
                "family": family,
                "width": width,
                "original": left,
                "candidate": right,
                "canonical_status": decision.status.value,
                "canonical_detail": decision.detail,
                "canonical_seconds": canonical_seconds,
                "polynomial_verdict": polynomial_verdict,
                "polynomial_detail": polynomial_detail,
                "z3_status": z3_status,
                "z3_seconds": z3_seconds,
            }
            rows.append(row)
            print(
                family,
                width,
                decision.status.value,
                polynomial_verdict,
                z3_status,
                flush=True,
            )

    payload = {
        "note": "preliminary probes of existing code; not a preregistered confirmatory set",
        "term_budget": TERM_BUDGET,
        "grid_budget": GRID_BUDGET,
        "max_variables": MAX_VARIABLES,
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
