#!/usr/bin/env python3
"""Degree-6 and degree-7 canonical evaluation.

Refuses to run if the protocol hash moved, and refuses to rewrite the
57-pair or 105-row result files.
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
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PROTOCOL = ROOT / "research" / "PROTOCOL_CANONICAL_DEGREE7.md"
META = ROOT / "research" / "protocol_canonical_degree7.json"
OUT_DIR = ROOT / "datasets" / "canonical_degree7_v1"
REPORT = ROOT / "experiments" / "reports" / "canonical-degree7-v1"
HELD_OUT = ROOT / "datasets" / "held_out" / "cases.jsonl"
FROZEN_57 = ROOT / "datasets" / "canonical_form_v1" / "cases.jsonl"
FROZEN_105 = ROOT / "datasets" / "canonical_wide_v1" / "cases.jsonl"
FROZEN_57_SUMMARY = ROOT / "experiments" / "reports" / "canonical-form-v1" / "summary.json"
FROZEN_105_SUMMARY = ROOT / "experiments" / "reports" / "canonical-wide-v1" / "summary.json"
WIDTHS = (1, 2, 4, 8, 32)
DEGREES = (6, 7)
EXHAUSTIVE_BUDGET = 65536
SAMPLE_BUDGET = 4096
FROZEN_SHA256 = {
    HELD_OUT: "36e4218e8026320a8d7988721a8051c286a980e7876a1ad226d10ef1ba866063",
    FROZEN_57: "e7de7560c6fa46f23038d6f2ea3701d867d3114fdd7d1b323cf672c6f4a5f37a",
    FROZEN_105: "4ca42c4ddfa73e26e74fa10077e56b237f18921662d26b8e0ea6eb1f9c941c82",
    FROZEN_57_SUMMARY: "5f6fc25c5f25aed9836fa10edaab114b609b79a3cc65024e5465cf1ea93a3cde",
    FROZEN_105_SUMMARY: "9ac5cf6ae42d16c3875fa05cc5056f71ad50ac7c623246df6f30caef97891196",
}


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
    if len(templates) != 4:
        raise SystemExit(f"expected 4 templates, found {len(templates)}")
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
                    "case_id": f"cd-{len(rows) + 1:04d}",
                    "construction_intent": template["intent"],
                    "degree": template["degree"],
                    "family": template["family"],
                    "original_source": template["original"],
                    "partition": "canonical_degree7_v1",
                    "semantic_mode": "mode_b",
                }
            )
    if len(rows) != 20:
        raise SystemExit(f"expected 20 pairs, found {len(rows)}")
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


def _slices(rows: list[dict]) -> dict[str, list[dict]]:
    groups = {"all": rows}
    for degree in DEGREES:
        groups[f"degree_{degree}"] = [row for row in rows if row["degree"] == degree]
    for width in WIDTHS:
        groups[f"width_{width}"] = [row for row in rows if row["bit_width"] == width]
        for degree in DEGREES:
            groups[f"degree_{degree}_width_{width}"] = [
                row for row in rows if row["degree"] == degree and row["bit_width"] == width
            ]
    return groups


def _pack(rows: list[dict], status_key: str, positive: str, truth: str) -> dict:
    chosen = [row for row in rows if row["ground_truth"] == truth]
    return _proportion(sum(1 for row in chosen if row[status_key] == positive), len(chosen))


def _by_slice(rows: list[dict], status_key: str, positive: str, truth: str) -> dict:
    return {
        name: _pack(chosen, status_key, positive, truth)
        for name, chosen in _slices(rows).items()
    }


def _decisive(rows: list[dict], key: str, accepted: set[str]) -> dict:
    return {
        name: _proportion(sum(1 for row in chosen if row[key] in accepted), len(chosen))
        for name, chosen in _slices(rows).items()
    }


def _times(rows: list[dict], key: str) -> dict:
    return {
        name: _time_summary([float(row[key]) for row in chosen if row[key] is not None])
        for name, chosen in _slices(rows).items()
    }


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


def _measured_terms() -> dict:
    from veriforge.config import SemanticConfiguration
    from veriforge.falling_factorial import _expand, _names, _to_falling
    from veriforge.independent_parser import parse_independent
    from veriforge.models import SemanticMode

    config = SemanticConfiguration(mode=SemanticMode.MODE_B, bit_width=4)
    counted = {}
    for template in _templates():
        if template["intent"] != "separating":
            continue
        root = parse_independent(template["original"], config).root
        names = tuple(sorted(_names(root)))
        monomials = _expand(root, names, 100000, time.perf_counter() + 60)
        falling = _to_falling(monomials, 100000, time.perf_counter() + 60)
        counted[str(template["degree"])] = {
            "monomials": len(monomials),
            "falling_factorial": len(falling),
        }
    return counted


def _frozen_ok() -> None:
    for path, expected in FROZEN_SHA256.items():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected:
            raise SystemExit(f"frozen file changed: {path} {digest}")


def main() -> int:
    digest = _require_hash()
    _frozen_ok()
    from veriforge.version import __version__

    if __version__ != "1.0.0":
        raise SystemExit(f"version changed: {__version__}")
    held_lines = [line for line in HELD_OUT.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(held_lines) != 8:
        raise SystemExit(f"held-out file has {len(held_lines)} lines")
    frozen_57 = [line for line in FROZEN_57.read_text(encoding="utf-8").splitlines() if line.strip()]
    frozen_105 = [line for line in FROZEN_105.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(frozen_57) != 57 or len(frozen_105) != 105:
        raise SystemExit(f"historical pair counts changed: {len(frozen_57)} {len(frozen_105)}")

    from veriforge.falling_factorial import GRID_BUDGET, TERM_BUDGET, decide_mode_b

    if TERM_BUDGET != 1715 or GRID_BUDGET != 262144:
        raise SystemExit(f"budgets moved: term {TERM_BUDGET} grid {GRID_BUDGET}")

    rows = _cases()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dataset_path = OUT_DIR / "cases.jsonl"
    with dataset_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    dataset_sha = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    term_counts = _measured_terms()

    from veriforge.config import SemanticConfiguration
    from veriforge.independent_parser import parse_independent
    from veriforge.models import SemanticMode
    from veriforge.parser_engine import parse_expression
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
            "grid_budget": GRID_BUDGET,
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

    nondecisive = [
        row for row in scored if row["canonical_status"] not in {"EQUIVALENT", "NOT_EQUIVALENT"}
    ]
    summary = {
        "record_id": "veriforge-canonical-degree7-v1",
        "protocol_sha256": digest,
        "dataset_sha256": dataset_sha,
        "pair_count": len(scored),
        "held_out_lines": len(held_lines),
        "frozen_57_pair_lines": len(frozen_57),
        "frozen_105_row_lines": len(frozen_105),
        "software_version": __version__,
        "python": platform.python_version(),
        "z3_version": z3.get_version_string(),
        "cvc5_version_line": cvc5_version_line,
        "z3_init_seconds": z3_init,
        "cvc5_init_seconds": cvc5_init,
        "term_budget": TERM_BUDGET,
        "grid_budget": GRID_BUDGET,
        "measured_term_counts": term_counts,
        "unknown_is_equivalence": False,
        "timeout_is_equivalence": False,
        "canonical_nondecisive": {
            "count": len(nondecisive),
            "rows": [
                {
                    "case_id": row["case_id"],
                    "degree": row["degree"],
                    "bit_width": row["bit_width"],
                    "status": row["canonical_status"],
                    "detail": row["canonical_detail"],
                }
                for row in nondecisive
            ],
        },
        "false_equivalence": {
            "canonical": _by_slice(scored, "canonical_status", "EQUIVALENT", "non_equivalent"),
            "z3": _by_slice(scored, "z3_status", "equivalent_within_model", "non_equivalent"),
            "cvc5": _by_slice(scored, "cvc5_status", "equivalent_within_model", "non_equivalent"),
        },
        "false_rejection": {
            "canonical": _by_slice(scored, "canonical_status", "NOT_EQUIVALENT", "equivalent"),
            "z3": _by_slice(scored, "z3_status", "counterexample_found", "equivalent"),
            "cvc5": _by_slice(scored, "cvc5_status", "counterexample_found", "equivalent"),
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
        counts[f"degree_{row['degree']}:width_{row['bit_width']}:{row['ground_truth']}"] += 1
    summary["ground_truth_counts"] = dict(sorted(counts.items()))
    REPORT.mkdir(parents=True, exist_ok=True)
    with (REPORT / "cases.jsonl").open("w", encoding="utf-8") as handle:
        for row in scored:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    (REPORT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "pair_count": summary["pair_count"],
        "measured_term_counts": term_counts,
        "canonical_nondecisive": summary["canonical_nondecisive"],
        "false_equivalence": summary["false_equivalence"]["canonical"],
        "decisive": summary["decisive"]["canonical"],
        "time_seconds": summary["time_seconds"]["canonical_wall"],
        "ground_truth_counts": summary["ground_truth_counts"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
