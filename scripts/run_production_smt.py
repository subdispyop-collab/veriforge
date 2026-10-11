#!/usr/bin/env python3
"""Production Z3 census for dataset 1.1.0.

Refuses to score unless research/PROTOCOL_AMENDMENT_SMT.md matches the
recorded SHA-256. Does not call the polynomial or exhaustive oracles.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

AMENDMENT = ROOT / "research" / "PROTOCOL_AMENDMENT_SMT.md"
AMENDMENT_META = ROOT / "research" / "protocol_amendment_smt.json"
CASES = ROOT / "datasets" / "assurance_v1" / "cases.jsonl"
OUT_DIR = ROOT / "experiments" / "reports" / "assurance-v1-smt"

RULES = (
    ("distributivity", "(x * (y + z))", "((x * y) + (x * z))", 4),
    ("factoring", "((x * y) + (x * z))", "(x * (y + z))", 4),
    ("const_fold", "(2 + 3)", "5", 4),
    ("sub_self", "(x - x)", "0", 4),
    ("add_self", "(x + x)", "(x * 2)", 8),
    ("double_neg", "(-(-x))", "x", 4),
    ("neg_sub", "(-(x - y))", "(y - x)", 4),
    ("const_reassoc", "((x + 2) + 3)", "(x + 5)", 8),
)
BAD_CANDIDATES = (
    ("add_self_width1", "(x + x)", "(x * 2)", 1),
    ("const_reassoc_width2", "((x + 2) + 3)", "(x + 5)", 2),
)


def _require_amendment() -> str:
    digest = hashlib.sha256(AMENDMENT.read_bytes()).hexdigest()
    meta = json.loads(AMENDMENT_META.read_text(encoding="utf-8"))
    recorded = meta.get("amendment_sha256")
    if digest != recorded:
        raise SystemExit(
            f"amendment hash mismatch: file {digest} recorded {recorded}"
        )
    return digest


def _count(rows: list[dict], key: str) -> dict[str, int]:
    counter: Counter[str] = Counter(row[key] for row in rows)
    return dict(sorted(counter.items()))


def main() -> int:
    digest = _require_amendment()
    import z3

    from veriforge.config import SemanticConfiguration
    from veriforge.models import (
        CounterexampleValidationStatus,
        SemanticMode,
        VerificationStatus,
    )
    from veriforge.verifier_engine import verify_equivalence_timed

    cases = [
        json.loads(line)
        for line in CASES.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(cases) != 463:
        raise SystemExit(f"expected 463 pairs, found {len(cases)}")

    rows: list[dict] = []
    for case in cases:
        mode = (
            SemanticMode.MODE_A
            if case["semantic_mode"] == "mode_a"
            else SemanticMode.MODE_B
        )
        if mode is SemanticMode.MODE_B and case["bit_width"] is None:
            raise SystemExit(f"{case['case_id']} is Mode B without a width")
        config = SemanticConfiguration(
            mode=mode,
            bit_width=case["bit_width"] or 32,
        ).with_limits(solver_timeout_seconds=5.0)
        timed = verify_equivalence_timed(
            case["original_source"],
            case["candidate_source"],
            config,
        )
        result = timed.result
        status = result.status.value
        validation = None
        if result.counterexample is not None:
            validation = result.counterexample.validation_status.value
        if result.status is VerificationStatus.COUNTEREXAMPLE_FOUND:
            if (
                result.counterexample is None
                or result.counterexample.validation_status
                is not CounterexampleValidationStatus.CONFIRMED
            ):
                status = "counterexample_not_confirmed_not_counted"
        rows.append(
            {
                "case_id": case["case_id"],
                "partition": case["partition"],
                "semantic_mode": case["semantic_mode"],
                "bit_width": case["bit_width"],
                "category": case["category"],
                "family": case["family"],
                "status": status,
                "solver_status": result.solver_status,
                "validation_status": validation,
                "solver_seconds": timed.solver_seconds,
                "translation_seconds": timed.translation_seconds,
                "reason": result.reason,
            }
        )

    def subset(mode: str | None = None, partition: str | None = None) -> list[dict]:
        chosen = rows
        if mode is not None:
            chosen = [row for row in chosen if row["semantic_mode"] == mode]
        if partition is not None:
            chosen = [row for row in chosen if row["partition"] == partition]
        return chosen

    def rule_check(rule_id: str, original: str, candidate: str, width: int) -> dict:
        outcomes = {}
        for mode_name, mode, bit_width in (
            ("mode_a", SemanticMode.MODE_A, 32),
            ("mode_b", SemanticMode.MODE_B, width),
        ):
            config = SemanticConfiguration(mode=mode, bit_width=bit_width).with_limits(
                solver_timeout_seconds=5.0
            )
            timed = verify_equivalence_timed(original, candidate, config)
            result = timed.result
            confirmed = (
                result.counterexample is not None
                and result.counterexample.validation_status
                is CounterexampleValidationStatus.CONFIRMED
            )
            outcomes[mode_name] = {
                "status": result.status.value,
                "bit_width": None if mode is SemanticMode.MODE_A else bit_width,
                "reference_confirmed": confirmed,
                "reason": result.reason,
            }
        both = (
            outcomes["mode_a"]["status"] == "equivalent_within_model"
            and outcomes["mode_b"]["status"] == "equivalent_within_model"
        )
        return {
            "rule_id": rule_id,
            "original_source": original,
            "candidate_source": candidate,
            "mode_b_width": width,
            "modes": outcomes,
            "both_modes_equivalent": both,
        }

    rule_rows = [
        rule_check(rule_id, original, candidate, width)
        for rule_id, original, candidate, width in RULES
    ]
    bad_rows = [
        rule_check(rule_id, original, candidate, width)
        for rule_id, original, candidate, width in BAD_CANDIDATES
    ]
    summary = {
        "amendment_sha256": digest,
        "z3_version": z3.get_version_string(),
        "solver_timeout_seconds": 5.0,
        "function": "veriforge.verifier_engine.verify_equivalence_timed",
        "dataset": str(CASES.relative_to(ROOT)),
        "pair_count": len(rows),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "status_counts": _count(rows, "status"),
        "by_mode": {
            "mode_a": {
                "n": len(subset("mode_a")),
                "status_counts": _count(subset("mode_a"), "status"),
            },
            "mode_b": {
                "n": len(subset("mode_b")),
                "status_counts": _count(subset("mode_b"), "status"),
            },
        },
        "by_partition": {
            "development": {
                "n": len(subset(partition="development")),
                "status_counts": _count(subset(partition="development"), "status"),
            },
            "held_out": {
                "n": len(subset(partition="held_out")),
                "status_counts": _count(subset(partition="held_out"), "status"),
            },
        },
        "counterexample_found_all_reference_confirmed": all(
            row["validation_status"] == "confirmed"
            for row in rows
            if row["status"] == "counterexample_found"
        ),
        "rules": rule_rows,
        "bad_candidates": bad_rows,
        "rules_admitted_by_this_script": [],
        "note": (
            "Status counts are production Z3 outcomes. "
            "This file does not compare them to the labeling oracle."
        ),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "production_smt_cases.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    (OUT_DIR / "production_smt.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary["status_counts"], sort_keys=True))
    print("rules", [row["rule_id"] for row in rule_rows if row["both_modes_equivalent"]])
    print("z3", summary["z3_version"], "n", summary["pair_count"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
