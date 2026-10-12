#!/usr/bin/env python3
"""Run the preregistered unsigned canonical-form study.

The protocol hash is checked before any pair is written. Generation is the
template list in that protocol. Solvers run only after the file exists.
"""

from __future__ import annotations

import hashlib
import json
import platform
import re
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PROTOCOL = ROOT / "research" / "PROTOCOL_CANONICAL_FORM.md"
META = ROOT / "research" / "protocol_canonical_form.json"
OUT_DIR = ROOT / "datasets" / "canonical_form_v1"
REPORT = ROOT / "experiments" / "reports" / "canonical-form-v1"
HELD_OUT = ROOT / "datasets" / "held_out" / "cases.jsonl"
WIDTHS = (1, 2, 4)


def _require_hash() -> str:
    digest = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    meta = json.loads(META.read_text(encoding="utf-8"))
    if meta.get("protocol_sha256") != digest:
        raise SystemExit(
            f"protocol hash mismatch file={digest} recorded={meta.get('protocol_sha256')}"
        )
    if meta.get("dataset_generated_before_hash") is not False:
        raise SystemExit("refusing to generate because the lock says pairs existed before the hash")
    if meta.get("solver_results_inspected_before_hash") is not False:
        raise SystemExit("refusing to run because solver results were inspected before the hash")
    return digest


def _templates() -> list[dict]:
    text = PROTOCOL.read_text(encoding="utf-8")
    start = text.index("```json\n") + len("```json\n")
    end = text.index("```", start)
    return json.loads(text[start:end])


def _literals(source: str) -> list[int]:
    return [int(token) for token in re.findall(r"\d+", source)]


def _cases() -> list[dict]:
    templates = _templates()
    if len(templates) != 19:
        raise SystemExit(f"expected 19 templates, found {len(templates)}")
    rows = []
    for template in templates:
        for width in WIDTHS:
            for source in (template["original"], template["candidate"]):
                for literal in _literals(source):
                    if literal < 0 or literal > (1 << width) - 1:
                        raise SystemExit(
                            f"literal {literal} is illegal at width {width} in {template['family']}"
                        )
            rows.append(
                {
                    "bit_width": width,
                    "candidate_source": template["candidate"],
                    "case_id": f"cf-{len(rows) + 1:04d}",
                    "construction_intent": template["intent"],
                    "family": template["family"],
                    "original_source": template["original"],
                    "partition": "canonical_form_v1",
                    "semantic_mode": "mode_b",
                }
            )
    if len(rows) != 57:
        raise SystemExit(f"expected 57 pairs, found {len(rows)}")
    return rows


def _wilson(successes: int, trials: int):
    from veriforge.stats_util import wilson_interval

    if trials == 0:
        return None
    low, high = wilson_interval(successes, trials)
    return [low, high]


def _proportion(numerator: int, denominator: int) -> dict:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "wilson95": _wilson(numerator, denominator),
    }


def _time_summary(values: list[float]) -> dict:
    if not values:
        return {"n": 0, "sum": None, "median": None}
    return {
        "n": len(values),
        "sum": float(sum(values)),
        "median": float(statistics.median(values)),
    }


def _pack_false(rows: list[dict], status_key: str, positive: str) -> dict:
    by_width = {}
    for width in WIDTHS:
        chosen = [row for row in rows if row["bit_width"] == width]
        by_width[str(width)] = _proportion(
            sum(1 for row in chosen if row[status_key] == positive),
            len(chosen),
        )
    return {
        "all": _proportion(
            sum(1 for row in rows if row[status_key] == positive),
            len(rows),
        ),
        "by_width": by_width,
    }


def main() -> int:
    digest = _require_hash()
    from veriforge.version import __version__

    if __version__ != "1.0.0":
        raise SystemExit(f"version changed: {__version__}")
    held_lines = [line for line in HELD_OUT.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(held_lines) != 8:
        raise SystemExit(f"held-out file has {len(held_lines)} lines")

    rows = _cases()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dataset_path = OUT_DIR / "cases.jsonl"
    with dataset_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    dataset_sha = hashlib.sha256(dataset_path.read_bytes()).hexdigest()

    from veriforge.config import SemanticConfiguration
    from veriforge.exhaustive_oracle import exhaustive_compare
    from veriforge.falling_factorial import decide_mode_b
    from veriforge.independent_parser import parse_independent
    from veriforge.models import SemanticMode
    from veriforge.parser_engine import parse_expression
    from veriforge.polynomial_oracle import polynomial_compare
    from veriforge.reference_evaluator import evaluate
    from veriforge.verifier_engine import verify_equivalence_timed
    from scripts.run_second_solver import SOLVERS, _classify_solver, _parse_model, _run, _script, _version

    import z3

    init_start = time.perf_counter()
    z3.Solver()
    z3_init = time.perf_counter() - init_start
    cvc5_init_start = time.perf_counter()
    cvc5_version_line = _version(SOLVERS["cvc5"]["binary"])
    cvc5_init = time.perf_counter() - cvc5_init_start
    z3_version = z3.get_version_string()

    scored = []
    for row in rows:
        config = SemanticConfiguration(mode=SemanticMode.MODE_B, bit_width=row["bit_width"])
        original = parse_independent(row["original_source"], config)
        candidate = parse_independent(row["candidate_source"], config)
        exhaustive = exhaustive_compare(
            original.root, candidate.root, config, assignment_budget=65536
        )
        exhaustive_label = {
            "equivalent": "equivalent",
            "counterexample": "non_equivalent",
            "not_computed": "not_computed",
            "not_applicable": "not_computed",
        }[exhaustive.verdict]
        polynomial = polynomial_compare(original.root, candidate.root, term_budget=4096)

        canonical_start = time.perf_counter()
        decision = decide_mode_b(row["original_source"], row["candidate_source"], config)
        canonical_seconds = time.perf_counter() - canonical_start

        z3_start = time.perf_counter()
        timed = verify_equivalence_timed(row["original_source"], row["candidate_source"], config)
        z3_seconds = time.perf_counter() - z3_start
        z3_status = timed.result.status.value

        cvc5_status = "solver_error"
        cvc5_seconds = None
        try:
            left = parse_expression(row["original_source"], config)
            right = parse_expression(row["candidate_source"], config)
            script = _script(left, right, True, row["bit_width"])
            started = time.perf_counter()
            completed = _run(SOLVERS["cvc5"]["binary"], SOLVERS["cvc5"]["args"], script)
            cvc5_seconds = time.perf_counter() - started
            kind, _detail = _classify_solver(completed.stdout, completed.stderr, completed.returncode)
            if kind == "unsat":
                cvc5_status = "equivalent_within_model"
            elif kind == "sat":
                assignment = _parse_model(completed.stdout, True, row["bit_width"])
                for name in set(left.variables) | set(right.variables):
                    assignment.setdefault(name, 0)
                if evaluate(left, assignment, config) != evaluate(right, assignment, config):
                    cvc5_status = "counterexample_found"
                else:
                    cvc5_status = "counterexample_validation_failed"
            elif kind == "timeout":
                cvc5_status = "timeout"
            elif kind == "solver_error":
                cvc5_status = "solver_error"
            else:
                cvc5_status = "unknown"
        except Exception as exc:  # noqa: BLE001
            cvc5_status = f"solver_error:{exc.__class__.__name__}"

        record = {
            **row,
            "exhaustive_label": exhaustive_label,
            "exhaustive_domain_size": exhaustive.domain_size,
            "polynomial_verdict": polynomial.verdict,
            "canonical_status": decision.status.value,
            "canonical_checker_accepted": decision.checker_accepted,
            "canonical_witness": decision.witness,
            "canonical_detail": decision.detail,
            "canonical_seconds": canonical_seconds,
            "z3_status": z3_status,
            "z3_solver_seconds": timed.solver_seconds,
            "z3_seconds": z3_seconds,
            "cvc5_status": cvc5_status,
            "cvc5_seconds": cvc5_seconds,
            "wrong_semantics": (
                polynomial.verdict == "counterexample" and exhaustive_label == "equivalent"
            ),
        }
        scored.append(record)
        print(
            row["case_id"],
            row["family"],
            row["bit_width"],
            exhaustive_label,
            polynomial.verdict,
            decision.status.value,
            z3_status,
            cvc5_status,
            flush=True,
        )

    wrong = [row for row in scored if row["wrong_semantics"]]
    by_family: dict[str, list[dict]] = defaultdict(list)
    for row in wrong:
        by_family[row["family"]].append(row)
    family_numerator = sum(
        1
        for items in by_family.values()
        if all(item["canonical_status"] == "EQUIVALENT" for item in items)
    )
    non_equivalent = [row for row in scored if row["exhaustive_label"] == "non_equivalent"]
    equivalent = [row for row in scored if row["exhaustive_label"] == "equivalent"]

    def counts(key: str) -> dict[str, int]:
        found: dict[str, int] = defaultdict(int)
        for row in scored:
            found[str(row[key])] += 1
        return dict(sorted(found.items()))

    summary = {
        "record_id": "veriforge-canonical-form-v1",
        "protocol_sha256": digest,
        "dataset_sha256": dataset_sha,
        "pair_count": len(scored),
        "held_out_lines": len(held_lines),
        "software_version": __version__,
        "python": platform.python_version(),
        "z3_version": z3_version,
        "cvc5_version_line": cvc5_version_line,
        "z3_init_seconds": z3_init,
        "cvc5_init_seconds": cvc5_init,
        "exhaustive_not_computed": sum(
            1 for row in scored if row["exhaustive_label"] == "not_computed"
        ),
        "primary_pairs": _proportion(
            sum(1 for row in wrong if row["canonical_status"] == "EQUIVALENT"),
            len(wrong),
        ),
        "primary_families": {
            "numerator": family_numerator,
            "denominator": len(by_family),
            "wilson95": _wilson(family_numerator, len(by_family)),
            "families": {
                family: [item["case_id"] for item in items]
                for family, items in sorted(by_family.items())
            },
        },
        "wrong_semantics_case_ids": [row["case_id"] for row in wrong],
        "false_equivalence": {
            "canonical": _pack_false(non_equivalent, "canonical_status", "EQUIVALENT"),
            "z3": _pack_false(non_equivalent, "z3_status", "equivalent_within_model"),
            "cvc5": _pack_false(non_equivalent, "cvc5_status", "equivalent_within_model"),
        },
        "false_rejection": {
            "canonical": _pack_false(equivalent, "canonical_status", "NOT_EQUIVALENT"),
            "z3": _pack_false(equivalent, "z3_status", "counterexample_found"),
            "cvc5": _pack_false(equivalent, "cvc5_status", "counterexample_found"),
        },
        "decisive": {
            "canonical": _proportion(
                sum(
                    1
                    for row in scored
                    if row["canonical_status"] in {"EQUIVALENT", "NOT_EQUIVALENT"}
                ),
                len(scored),
            ),
            "z3": _proportion(
                sum(
                    1
                    for row in scored
                    if row["z3_status"] in {"equivalent_within_model", "counterexample_found"}
                ),
                len(scored),
            ),
            "cvc5": _proportion(
                sum(
                    1
                    for row in scored
                    if row["cvc5_status"] in {"equivalent_within_model", "counterexample_found"}
                ),
                len(scored),
            ),
        },
        "time_seconds": {
            "canonical_wall": _time_summary([row["canonical_seconds"] for row in scored]),
            "z3_wall": _time_summary([row["z3_seconds"] for row in scored]),
            "z3_solver": _time_summary(
                [float(row["z3_solver_seconds"]) for row in scored if row["z3_solver_seconds"] is not None]
            ),
            "cvc5_wall": _time_summary(
                [float(row["cvc5_seconds"]) for row in scored if row["cvc5_seconds"] is not None]
            ),
        },
        "other_mismatches": {
            "polynomial_equivalent_exhaustive_non_equivalent": sum(
                1
                for row in scored
                if row["polynomial_verdict"] == "equivalent"
                and row["exhaustive_label"] == "non_equivalent"
            ),
            "polynomial_not_computed": sum(
                1 for row in scored if row["polynomial_verdict"] == "not_computed"
            ),
        },
        "status_counts": {
            "canonical": counts("canonical_status"),
            "z3": counts("z3_status"),
            "cvc5": counts("cvc5_status"),
            "exhaustive": counts("exhaustive_label"),
            "polynomial": counts("polynomial_verdict"),
        },
    }
    REPORT.mkdir(parents=True, exist_ok=True)
    with (REPORT / "cases.jsonl").open("w", encoding="utf-8") as handle:
        for row in scored:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    (REPORT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
