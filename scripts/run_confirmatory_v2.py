#!/usr/bin/env python3
"""Generate and score confirmatory-v2 only after the protocol hash matches."""

from __future__ import annotations

import hashlib
import json
import platform
import random
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PROTOCOL = ROOT / "research" / "PROTOCOL_CONFIRMATORY_V2.md"
META = ROOT / "research" / "protocol_confirmatory_v2.json"
OUT_DIR = ROOT / "datasets" / "confirmatory_v2"
REPORT = ROOT / "experiments" / "reports" / "confirmatory-v2"


def _load_templates() -> list[dict]:
    text = PROTOCOL.read_text(encoding="utf-8")
    start = text.index("```json\n") + len("```json\n")
    end = text.index("```", start)
    return json.loads(text[start:end])


def _require_hash() -> str:
    digest = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    meta = json.loads(META.read_text(encoding="utf-8"))
    if meta.get("protocol_sha256") != digest:
        raise SystemExit(f"protocol hash mismatch: file {digest} recorded {meta.get('protocol_sha256')}")
    if meta.get("dataset_generated_before_hash") is not False:
        raise SystemExit("preregistration does not say the dataset was generated after the hash")
    return digest


def _cases() -> list[dict]:
    templates = _load_templates()
    if len(templates) != 24:
        raise SystemExit(f"expected 24 templates, found {len(templates)}")
    settings = (
        ("mode_a", None),
        ("mode_b", 4),
        ("mode_b", 8),
    )
    rows = []
    for template in templates:
        for mode, width in settings:
            rows.append(
                {
                    "case_id": f"cv2-{len(rows) + 1:04d}",
                    "family": template["family"],
                    "category": template["category"],
                    "construction_intent": template["intent"],
                    "semantic_mode": mode,
                    "bit_width": width,
                    "original_source": template["original"],
                    "candidate_source": template["candidate"],
                    "partition": "confirmatory",
                }
            )
    if len(rows) != 72:
        raise SystemExit(f"expected 72 pairs, found {len(rows)}")
    return rows


def _wilson(successes: int, trials: int):
    from veriforge.stats_util import wilson_interval

    if trials == 0:
        return None
    low, high = wilson_interval(successes, trials)
    return [low, high]


def _false_eq(rows: list[dict], status_key: str) -> dict:
    def pack(chosen: list[dict]) -> dict:
        denom = [row for row in chosen if row["oracle_label"] == "non_equivalent"]
        numer = [row for row in denom if row[status_key] == "equivalent_within_model"]
        families = sorted({row["family"] for row in denom})
        bad_families = sorted({row["family"] for row in numer})
        return {
            "false_equivalence": len(numer),
            "denominator_pairs": len(denom),
            "false_equivalence_families": len(bad_families),
            "denominator_families": len(families),
            "wilson95_pairs": _wilson(len(numer), len(denom)),
            "insufficient_sample": len(families) < 4,
        }

    by_mode = {}
    for mode in ("mode_a", "mode_b"):
        by_mode[mode] = pack([row for row in rows if row["semantic_mode"] == mode])
    return {"all": pack(rows), "by_mode": by_mode}


def _spearman_boot(xs: list[float], ys: list[float]) -> dict:
    from veriforge.stats_util import spearman

    point = spearman(xs, ys)
    resamples = 2000
    rng = random.Random(20261012)
    rhos = []
    undefined = 0
    n = len(xs)
    for _ in range(resamples):
        idx = [rng.randrange(n) for _ in range(n)]
        rho = spearman([xs[i] for i in idx], [ys[i] for i in idx])
        if rho is None:
            undefined += 1
            continue
        rhos.append(rho)
    rhos.sort()
    low_index = int(0.025 * (resamples - 1))
    high_index = int(0.975 * (resamples - 1))
    if point is None or len(rhos) <= high_index:
        return {
            "rho": point,
            "low": None,
            "high": None,
            "undefined_resamples": undefined,
            "n_families": n,
        }
    return {
        "rho": point,
        "low": rhos[low_index],
        "high": rhos[high_index],
        "undefined_resamples": undefined,
        "n_families": n,
        "resamples": resamples,
        "seed": 20261012,
    }


def _h3(rows: list[dict]) -> dict:
    from veriforge.stats_util import bootstrap_median_interval

    usable = [row for row in rows if isinstance(row.get("z3_solver_seconds"), (int, float))]
    by_family: dict[str, list[dict]] = defaultdict(list)
    for row in usable:
        by_family[row["family"]].append(row)
    family_rows = []
    for family, members in sorted(by_family.items()):
        labels = {member["oracle_label"] for member in members}
        label_class = next(iter(labels)) if len(labels) == 1 else "mixed"
        family_rows.append(
            {
                "family": family,
                "median_solver_seconds": statistics.median(member["z3_solver_seconds"] for member in members),
                "median_operator_count": statistics.median(member["operator_count"] for member in members),
                "oracle_class": label_class,
                "n_pairs": len(members),
            }
        )
    rho = _spearman_boot(
        [row["median_operator_count"] for row in family_rows],
        [row["median_solver_seconds"] for row in family_rows],
    )
    complexity = "unresolved"
    if rho["rho"] is not None and rho["low"] is not None and rho["high"] is not None:
        if rho["rho"] > 0 and rho["low"] > 0:
            complexity = "supported"
        elif rho["low"] <= 0 <= rho["high"]:
            complexity = "unresolved"
        else:
            complexity = "not_supported"

    def class_arm(name: str) -> dict:
        chosen = [row for row in family_rows if row["oracle_class"] == name]
        times = [row["median_solver_seconds"] for row in chosen]
        interval = bootstrap_median_interval(times, seed=20261012, resamples=2000) if len(times) >= 4 else None
        pair_rows = [row for row in rows if row["family"] in {item["family"] for item in chosen}]
        rate_rows = [
            row
            for row in pair_rows
            if row["z3_status"] in {"equivalent_within_model", "counterexample_found", "timeout", "unknown"}
        ]
        failures = sum(1 for row in rate_rows if row["z3_status"] in {"timeout", "unknown"})
        return {
            "families": len(chosen),
            "insufficient": len(chosen) < 4,
            "time_interval": interval,
            "timeout_or_unknown": failures,
            "rate_denominator": len(rate_rows),
            "wilson95": _wilson(failures, len(rate_rows)),
        }

    eq_arm = class_arm("equivalent")
    ne_arm = class_arm("non_equivalent")

    def disjoint(a, b) -> bool:
        if not a or not b:
            return False
        return a[1] < b[0] or b[1] < a[0]

    category_varies = (
        not eq_arm["insufficient"]
        and not ne_arm["insufficient"]
        and eq_arm["time_interval"]
        and ne_arm["time_interval"]
        and disjoint(
            [eq_arm["time_interval"]["low"], eq_arm["time_interval"]["high"]],
            [ne_arm["time_interval"]["low"], ne_arm["time_interval"]["high"]],
        )
    )
    success_varies = (
        not eq_arm["insufficient"]
        and not ne_arm["insufficient"]
        and disjoint(eq_arm["wilson95"], ne_arm["wilson95"])
    )
    if complexity == "unresolved" or eq_arm["insufficient"] or ne_arm["insufficient"]:
        verdict = "unresolved"
    elif (complexity == "supported" or category_varies) and not success_varies:
        verdict = "not_supported"
    elif complexity == "supported" and category_varies and success_varies:
        verdict = "supported"
    else:
        verdict = "unresolved"
    return {
        "verdict": verdict,
        "complexity_arm": complexity,
        "spearman": rho,
        "equivalent_class": eq_arm,
        "non_equivalent_class": ne_arm,
        "category_overhead_varies": category_varies,
        "success_rates_vary": success_varies,
        "family_rows": family_rows,
        "init_excluded_from_correlation": True,
    }


def main() -> int:
    digest = _require_hash()
    from types import SimpleNamespace

    from veriforge.assurance import audit_equivalence
    from veriforge.assurance_experiment import label_case
    from veriforge.config import SemanticConfiguration
    from veriforge.independent_encoder import encode_difference
    from veriforge.independent_parser import operator_count, parse_independent
    from veriforge.models import SemanticMode
    from veriforge.reference_evaluator import evaluate
    from veriforge.parser_engine import parse_expression
    from veriforge.verifier_engine import verify_equivalence_timed
    from scripts.run_second_solver import SOLVERS, _classify_solver, _parse_model, _run, _script

    rows = _cases()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dataset_path = OUT_DIR / "cases.jsonl"
    with dataset_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    held_out = (ROOT / "datasets" / "held_out" / "cases.jsonl").read_text(encoding="utf-8").splitlines()
    if len([line for line in held_out if line.strip()]) != 8:
        raise SystemExit("historical held-out file changed")

    import z3
    from scripts.run_second_solver import _version

    init_start = time.perf_counter()
    z3.Solver()
    z3_init = time.perf_counter() - init_start
    cvc5_init_start = time.perf_counter()
    cvc5_version_line = _version(SOLVERS["cvc5"]["binary"])
    cvc5_init = time.perf_counter() - cvc5_init_start

    scored = []
    ablation = []
    for row in rows:
        case = SimpleNamespace(**row)
        labeled = label_case(case)
        mode = SemanticMode.MODE_A if row["semantic_mode"] == "mode_a" else SemanticMode.MODE_B
        config = SemanticConfiguration(mode=mode, bit_width=row["bit_width"] or 32)
        ops = None
        try:
            ops = operator_count(parse_independent(row["original_source"], config).root)
        except Exception:
            ops = None

        t0 = time.perf_counter()
        timed = verify_equivalence_timed(row["original_source"], row["candidate_source"], config)
        verifier_wall = time.perf_counter() - t0
        z3_status = timed.result.status.value

        concrete_status = z3_status
        concrete_wall_start = time.perf_counter()
        if z3_status == "equivalent_within_model":
            try:
                names = set()
                left = parse_expression(row["original_source"], config)
                right = parse_expression(row["candidate_source"], config)
                names = set(left.variables) | set(right.variables)
                assignment = {name: 0 for name in names}
                if evaluate(left, assignment, config) != evaluate(right, assignment, config):
                    concrete_status = "concrete_counterexample"
            except Exception:
                pass
        concrete_wall = verifier_wall + (time.perf_counter() - concrete_wall_start)

        t1 = time.perf_counter()
        try:
            original = parse_independent(row["original_source"], config)
            candidate = parse_independent(row["candidate_source"], config)
            encoded = encode_difference(original.root, candidate.root, config)
            encoder_verdict = encoded.verdict
        except Exception as exc:  # noqa: BLE001
            encoder_verdict = f"error:{exc.__class__.__name__}"
        encoder_wall = time.perf_counter() - t1

        t2 = time.perf_counter()
        report = audit_equivalence(row["original_source"], row["candidate_source"], config, run_smt=True)
        pipeline_wall = time.perf_counter() - t2
        pipeline_status = report.status.value

        cvc5_status = None
        cvc5_seconds = None
        if labeled["oracle_label"] in {"unsupported", "invalid_input"}:
            cvc5_status = labeled["oracle_label"]
            cvc5_seconds = 0.0
        else:
            try:
                left = parse_expression(row["original_source"], config)
                right = parse_expression(row["candidate_source"], config)
                script = _script(left, right, mode is SemanticMode.MODE_B, row["bit_width"] or 32)
                started = time.perf_counter()
                completed = _run(SOLVERS["cvc5"]["binary"], SOLVERS["cvc5"]["args"], script)
                cvc5_seconds = time.perf_counter() - started
                kind, _detail = _classify_solver(completed.stdout, completed.stderr, completed.returncode)
                if kind == "unsat":
                    cvc5_status = "equivalent_within_model"
                elif kind == "sat":
                    assignment = _parse_model(completed.stdout, mode is SemanticMode.MODE_B, row["bit_width"] or 32)
                    from veriforge.reference_evaluator import evaluate as eval_ref

                    if eval_ref(left, assignment, config) != eval_ref(right, assignment, config):
                        cvc5_status = "counterexample_found"
                    else:
                        cvc5_status = "counterexample_validation_failed"
                elif kind == "timeout":
                    cvc5_status = "timeout"
                elif kind == "solver_error":
                    cvc5_status = "solver_error"
                else:
                    cvc5_status = "unknown"
            except Exception:
                cvc5_status = "solver_error"

        encoder_status = (
            "equivalent_within_model" if encoder_verdict == "equivalent" else encoder_verdict
        )
        scored.append(
            {
                **labeled,
                "operator_count": ops,
                "z3_status": z3_status,
                "z3_solver_seconds": timed.solver_seconds,
                "cvc5_status": cvc5_status,
                "cvc5_process_seconds": cvc5_seconds,
                "concrete_status": concrete_status,
                "encoder_status": encoder_status,
                "pipeline_status": pipeline_status,
            }
        )
        ablation.append(
            {
                "case_id": row["case_id"],
                "verifier_seconds": verifier_wall,
                "concrete_seconds": concrete_wall,
                "encoder_seconds": encoder_wall,
                "pipeline_seconds": pipeline_wall,
            }
        )
        print(row["case_id"], z3_status, cvc5_status, labeled["oracle_label"], flush=True)

    def arm_false(status_key: str, equivalent_token: str = "equivalent_within_model") -> dict:
        copied = []
        for row in scored:
            status = row[status_key]
            if status == equivalent_token:
                status = "equivalent_within_model"
            copied.append({**row, "arm_status": status})
        return _false_eq(copied, "arm_status")

    z3_false = _false_eq(scored, "z3_status")
    cvc5_false = _false_eq(scored, "cvc5_status")
    walls = {
        "verifier": sum(item["verifier_seconds"] for item in ablation),
        "verifier_plus_concrete": sum(item["concrete_seconds"] for item in ablation),
        "verifier_plus_independent_encoder": sum(item["encoder_seconds"] for item in ablation),
        "full_pipeline": sum(item["pipeline_seconds"] for item in ablation),
    }
    arm_counts = {
        "verifier": z3_false,
        "verifier_plus_concrete": arm_false("concrete_status"),
        "verifier_plus_independent_encoder": arm_false("encoder_status"),
        "full_pipeline": arm_false("pipeline_status"),
    }
    notes = []
    base = arm_counts["verifier"]["all"]["false_equivalence"]
    for name, counts in arm_counts.items():
        if name == "verifier":
            continue
        if counts["all"]["false_equivalence"] == base and walls[name] > walls["verifier"]:
            notes.append(f"{name} did not reduce false equivalence and took more wall time")
    h3 = _h3(scored)
    summary = {
        "protocol_sha256": digest,
        "protocol_created_at_utc": json.loads(META.read_text(encoding="utf-8"))["created_at_utc"],
        "pair_count": len(scored),
        "family_count": len({row["family"] for row in scored}),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "z3_version": z3.get_version_string(),
        "cvc5_version_line": cvc5_version_line,
        "z3_init_seconds": z3_init,
        "cvc5_init_seconds": cvc5_init,
        "historical_held_out_lines": 8,
        "false_equivalence_z3": z3_false,
        "false_equivalence_cvc5": cvc5_false,
        "ablation_wall_seconds": walls,
        "ablation_false_equivalence": arm_counts,
        "ablation_notes": notes,
        "h3": h3,
        "oracle_label_counts": dict(sorted(
            (label, sum(1 for row in scored if row["oracle_label"] == label))
            for label in {row["oracle_label"] for row in scored}
        )),
    }
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    with (REPORT / "cases.jsonl").open("w", encoding="utf-8") as handle:
        for row in scored:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps({k: summary[k] for k in (
        "false_equivalence_z3", "false_equivalence_cvc5", "ablation_wall_seconds", "ablation_notes", "h3"
    ) if k != "h3"}, indent=2))
    print("H3", summary["h3"]["verdict"], summary["h3"]["complexity_arm"], summary["h3"]["spearman"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
