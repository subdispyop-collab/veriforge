#!/usr/bin/env python3
"""Wider canonical-form evaluation. Refuses to run if the protocol hash moved."""

from __future__ import annotations

import hashlib
import json
import platform
import re
import statistics
import sys
import time
from collections import defaultdict
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PROTOCOL = ROOT / "research" / "PROTOCOL_CANONICAL_WIDE.md"
META = ROOT / "research" / "protocol_canonical_wide.json"
OUT_DIR = ROOT / "datasets" / "canonical_wide_v1"
REPORT = ROOT / "experiments" / "reports" / "canonical-wide-v1"
HELD_OUT = ROOT / "datasets" / "held_out" / "cases.jsonl"
FROZEN = ROOT / "datasets" / "canonical_form_v1" / "cases.jsonl"
WIDTHS = (1, 2, 4, 8, 32)
CONTROL = {1, 2, 4}
EXHAUSTIVE_BUDGET = 65536
SAMPLE_BUDGET = 4096


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
    if len(templates) != 21:
        raise SystemExit(f"expected 21 templates, found {len(templates)}")
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
                    "arm": "control" if width in CONTROL else "wide",
                    "bit_width": width,
                    "candidate_source": template["candidate"],
                    "case_id": f"cw-{len(rows) + 1:04d}",
                    "construction_intent": template["intent"],
                    "family": template["family"],
                    "original_source": template["original"],
                    "partition": "canonical_wide_v1",
                    "semantic_mode": "mode_b",
                }
            )
    if len(rows) != 105:
        raise SystemExit(f"expected 105 pairs, found {len(rows)}")
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
    return {"n": len(values), "sum": float(sum(values)), "median": float(statistics.median(values))}


def _sample_points(names: tuple[str, ...], width: int) -> list[dict[str, int]]:
    if not names:
        return [{}]
    last = (1 << width) - 1
    values: list[int] = []
    for value in (0, 1, min(2, last), last):
        if value not in values:
            values.append(value)
    if len(values) ** len(names) <= SAMPLE_BUDGET:
        return [
            {name: point[index] for index, name in enumerate(names)}
            for point in product(values, repeat=len(names))
        ]
    points = [{name: 0 for name in names}, {name: last for name in names}]
    for name in names:
        point = {other: 0 for other in names}
        point[name] = 1 if last >= 1 else 0
        points.append(point)
    return points


def _ground_truth(row: dict, config, original, candidate) -> dict:
    from veriforge.exhaustive_oracle import exhaustive_compare
    from veriforge.parser_engine import parse_expression
    from veriforge.reference_evaluator import evaluate

    names = tuple(sorted(set(original.variables) | set(candidate.variables)))
    domain = 1 << (row["bit_width"] * len(names))
    if domain <= EXHAUSTIVE_BUDGET:
        exhaustive = exhaustive_compare(
            original.root, candidate.root, config, assignment_budget=EXHAUSTIVE_BUDGET
        )
        label = {
            "equivalent": "equivalent",
            "counterexample": "non_equivalent",
            "not_computed": "not_computed",
            "not_applicable": "not_computed",
        }[exhaustive.verdict]
        return {
            "ground_truth": label,
            "ground_truth_source": "exhaustive" if label != "not_computed" else "not_computed",
            "domain_size": domain,
            "ground_truth_witness": exhaustive.witness,
        }
    left = parse_expression(row["original_source"], config)
    right = parse_expression(row["candidate_source"], config)
    for assignment in _sample_points(names, row["bit_width"]):
        if evaluate(left, assignment, config) != evaluate(right, assignment, config):
            return {
                "ground_truth": "non_equivalent",
                "ground_truth_source": "confirmed_counterexample",
                "domain_size": domain,
                "ground_truth_witness": assignment,
            }
    return {
        "ground_truth": "not_computed",
        "ground_truth_source": "not_computed",
        "domain_size": domain,
        "ground_truth_witness": None,
    }


def _pack(rows: list[dict], status_key: str, positive: str, truth: str) -> dict:
    chosen = [row for row in rows if row["ground_truth"] == truth]
    return _proportion(sum(1 for row in chosen if row[status_key] == positive), len(chosen))


def _by_width(rows: list[dict], status_key: str, positive: str, truth: str) -> dict:
    packed = {}
    for width in WIDTHS:
        packed[str(width)] = _pack(
            [row for row in rows if row["bit_width"] == width], status_key, positive, truth
        )
    packed["control"] = _pack(
        [row for row in rows if row["arm"] == "control"], status_key, positive, truth
    )
    packed["wide"] = _pack(
        [row for row in rows if row["arm"] == "wide"], status_key, positive, truth
    )
    packed["all"] = _pack(rows, status_key, positive, truth)
    return packed


def _decisive(rows: list[dict], key: str, accepted: set[str]) -> dict:
    packed = {}
    groups = {str(width): [row for row in rows if row["bit_width"] == width] for width in WIDTHS}
    groups["control"] = [row for row in rows if row["arm"] == "control"]
    groups["wide"] = [row for row in rows if row["arm"] == "wide"]
    groups["all"] = rows
    for name, chosen in groups.items():
        packed[name] = _proportion(
            sum(1 for row in chosen if row[key] in accepted),
            len(chosen),
        )
    return packed


def _times(rows: list[dict], key: str) -> dict:
    packed = {}
    groups = {str(width): [row for row in rows if row["bit_width"] == width] for width in WIDTHS}
    groups["control"] = [row for row in rows if row["arm"] == "control"]
    groups["wide"] = [row for row in rows if row["arm"] == "wide"]
    groups["all"] = rows
    for name, chosen in groups.items():
        packed[name] = _time_summary(
            [float(row[key]) for row in chosen if row[key] is not None]
        )
    return packed


def main() -> int:
    digest = _require_hash()
    from veriforge.version import __version__

    if __version__ != "1.0.0":
        raise SystemExit(f"version changed: {__version__}")
    held_lines = [line for line in HELD_OUT.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(held_lines) != 8:
        raise SystemExit(f"held-out file has {len(held_lines)} lines")
    frozen_lines = [line for line in FROZEN.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(frozen_lines) != 57:
        raise SystemExit(f"57-pair study changed: {len(frozen_lines)} lines")

    rows = _cases()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dataset_path = OUT_DIR / "cases.jsonl"
    with dataset_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    dataset_sha = hashlib.sha256(dataset_path.read_bytes()).hexdigest()

    from veriforge.config import SemanticConfiguration
    from veriforge.falling_factorial import TERM_BUDGET, decide_mode_b
    from veriforge.independent_parser import parse_independent
    from veriforge.models import SemanticMode
    from veriforge.parser_engine import parse_expression
    from veriforge.reference_evaluator import evaluate
    from veriforge.verifier_engine import verify_equivalence_timed
    from scripts.run_second_solver import SOLVERS, _classify_solver, _parse_model, _run, _script, _version

    import z3

    if TERM_BUDGET != 256:
        raise SystemExit(f"term cap changed: {TERM_BUDGET}")
    init_start = time.perf_counter()
    z3.Solver()
    z3_init = time.perf_counter() - init_start
    cvc5_init_start = time.perf_counter()
    cvc5_version_line = _version(SOLVERS["cvc5"]["binary"])
    cvc5_init = time.perf_counter() - cvc5_init_start

    scored = []
    for row in rows:
        config = SemanticConfiguration(mode=SemanticMode.MODE_B, bit_width=row["bit_width"])
        original = parse_independent(row["original_source"], config)
        candidate = parse_independent(row["candidate_source"], config)
        truth = _ground_truth(row, config, original, candidate)

        canonical_start = time.perf_counter()
        decision = decide_mode_b(row["original_source"], row["candidate_source"], config)
        canonical_seconds = time.perf_counter() - canonical_start

        z3_start = time.perf_counter()
        timed = verify_equivalence_timed(row["original_source"], row["candidate_source"], config)
        z3_seconds = time.perf_counter() - z3_start

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
            **truth,
            "canonical_status": decision.status.value,
            "canonical_detail": decision.detail,
            "canonical_checker_accepted": decision.checker_accepted,
            "canonical_seconds": canonical_seconds,
            "term_budget": TERM_BUDGET,
            "z3_status": timed.result.status.value,
            "z3_seconds": z3_seconds,
            "cvc5_status": cvc5_status,
            "cvc5_seconds": cvc5_seconds,
        }
        scored.append(record)
        print(
            row["case_id"],
            row["family"],
            row["bit_width"],
            truth["ground_truth"],
            decision.status.value,
            timed.result.status.value,
            cvc5_status,
            flush=True,
        )

    unknown = [row for row in scored if row["canonical_status"] == "UNKNOWN"]
    summary = {
        "record_id": "veriforge-canonical-wide-v1",
        "protocol_sha256": digest,
        "dataset_sha256": dataset_sha,
        "pair_count": len(scored),
        "held_out_lines": len(held_lines),
        "frozen_57_pair_lines": len(frozen_lines),
        "software_version": __version__,
        "python": platform.python_version(),
        "z3_version": z3.get_version_string(),
        "cvc5_version_line": cvc5_version_line,
        "z3_init_seconds": z3_init,
        "cvc5_init_seconds": cvc5_init,
        "term_budget": TERM_BUDGET,
        "unknown_is_equivalence": False,
        "canonical_unknown": {
            "count": len(unknown),
            "case_ids": [row["case_id"] for row in unknown],
            "details": sorted({row["canonical_detail"] for row in unknown}),
        },
        "ground_truth_counts": dict(sorted(defaultdict(int, **{
            # filled below
        }).items())),
        "false_equivalence": {
            "canonical": _by_width(scored, "canonical_status", "EQUIVALENT", "non_equivalent"),
            "z3": _by_width(scored, "z3_status", "equivalent_within_model", "non_equivalent"),
            "cvc5": _by_width(scored, "cvc5_status", "equivalent_within_model", "non_equivalent"),
        },
        "false_rejection": {
            "canonical": _by_width(scored, "canonical_status", "NOT_EQUIVALENT", "equivalent"),
            "z3": _by_width(scored, "z3_status", "counterexample_found", "equivalent"),
            "cvc5": _by_width(scored, "cvc5_status", "counterexample_found", "equivalent"),
        },
        "decisive": {
            "canonical": _decisive(scored, "canonical_status", {"EQUIVALENT", "NOT_EQUIVALENT"}),
            "z3": _decisive(scored, "z3_status", {"equivalent_within_model", "counterexample_found"}),
            "cvc5": _decisive(scored, "cvc5_status", {"equivalent_within_model", "counterexample_found"}),
        },
        "time_seconds": {
            "canonical_wall": _times(scored, "canonical_seconds"),
            "z3_wall": _times(scored, "z3_seconds"),
            "cvc5_wall": _times(scored, "cvc5_seconds"),
        },
    }
    counts: dict[str, int] = defaultdict(int)
    for row in scored:
        counts[f"{row['bit_width']}:{row['ground_truth']}"] += 1
    summary["ground_truth_counts"] = dict(sorted(counts.items()))
    REPORT.mkdir(parents=True, exist_ok=True)
    with (REPORT / "cases.jsonl").open("w", encoding="utf-8") as handle:
        for row in scored:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    (REPORT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in (
        "pair_count", "canonical_unknown", "false_equivalence", "false_rejection", "decisive", "time_seconds", "ground_truth_counts"
    )}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
