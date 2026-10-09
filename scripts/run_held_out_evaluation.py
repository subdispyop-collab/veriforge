#!/usr/bin/env python3
"""Run Phase 10 held-out evaluation for implemented baselines.

Uses datasets/held_out/ only. Does not tune against development.
If z3-solver is unavailable, records dependency blocker and writes an
unavailable report without fabricating measurements.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_unavailable_report(
    *,
    blocker: str,
    seed: int,
    timeout: float,
    execution_iterations: int,
    trials: int,
    config_out: Path,
    report_json: Path,
    report_md: Path,
    software_version: str = "0.10.0",
) -> dict:
    """Write honest unavailable artifacts when the evaluation package cannot load."""

    config = {
        "protocol_id": "veriforge-phase10-held-out-evaluation",
        "protocol_version": "1.0.0",
        "dataset_version": "0.5.0",
        "dataset_partition": "held_out",
        "random_seed": seed,
        "solver_timeout_seconds": timeout,
        "execution_iterations": execution_iterations,
        "trials_per_case": trials,
        "baseline_ids": [
            "baseline.original_no_optimization",
            "baseline.rule_based_without_smt",
            "baseline.verification_enabled",
            "baseline.testing_only_validation",
        ],
        "software_version": software_version,
        "execute_held_out_evaluation": True,
        "notes": (
            "scripts/run_held_out_evaluation.py — unavailable path "
            "(dependencies could not be imported)"
        ),
        "host_platform_summary": platform.platform(),
        "dependency_blocker": blocker,
    }
    fingerprint = hashlib.sha256(
        json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    payload = {
        "protocol_id": config["protocol_id"],
        "protocol_version": config["protocol_version"],
        "software_version": software_version,
        "dataset_version": "0.5.0",
        "random_seed": seed,
        "configuration_fingerprint": fingerprint,
        "created_at_utc": _utc_now(),
        "dependency_available": False,
        "dependency_blocker": blocker,
        "baseline_runs": [],
        "unavailable_baselines": [
            f"{bid}: dependency blocker — {blocker}"
            for bid in config["baseline_ids"]
        ],
        "hypothesis_status": {
            "H1_verification_detects_incorrect": (
                "unavailable — no held-out SMT runs"
            ),
            "H2_verification_introduces_overhead": (
                "unavailable — no held-out SMT runs"
            ),
            "H3_varies_by_complexity_and_category": (
                "unavailable — no held-out SMT runs"
            ),
        },
        "limitations": [
            f"Runtime dependency blocker on this host: {blocker}",
            "Held-out sample size is small (seed partition); do not treat "
            "rates as population estimates.",
            "Exact bit-for-bit reproduction of solver timings is not guaranteed.",
            "Baseline external_tool remains not_selected.",
            "No measurements were fabricated.",
        ],
        "latency_separation": {"by_baseline": []},
        "is_research_conclusion_attempt": True,
        "novelty_claim": (
            "No novelty claim. Literature review situates VERIFORGE among "
            "established translation-validation / equivalence-checking methods; "
            "confirmed novel research findings are not established."
        ),
        "attempt_id": str(uuid.uuid4()),
    }

    config_out.parent.mkdir(parents=True, exist_ok=True)
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_md.parent.mkdir(parents=True, exist_ok=True)
    config_out.write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    md_lines = [
        "# Phase 10 held-out evaluation report",
        "",
        f"- Protocol: `{payload['protocol_id']}` v`{payload['protocol_version']}`",
        f"- Software: `{payload['software_version']}`",
        f"- Seed: `{payload['random_seed']}`",
        f"- Created (UTC): `{payload['created_at_utc']}`",
        f"- Dependency available: `False`",
        "",
        "## Dependency blocker",
        "",
        blocker,
        "",
        "## Unavailable baselines",
        "",
    ]
    for item in payload["unavailable_baselines"]:
        md_lines.append(f"- {item}")
    md_lines.extend(
        [
            "",
            "## Baseline runs",
            "",
            "No baseline runs completed. Results: **unavailable**.",
            "",
            "## Hypothesis status (not advance findings)",
            "",
        ]
    )
    for key, value in payload["hypothesis_status"].items():
        md_lines.append(f"- **{key}**: {value}")
    md_lines.extend(["", "## Limitations", ""])
    for item in payload["limitations"]:
        md_lines.append(f"- {item}")
    md_lines.extend(
        ["", "## Novelty", "", payload["novelty_claim"], ""]
    )
    report_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="VERIFORGE Phase 10 held-out baseline evaluation"
    )
    parser.add_argument("--seed", type=int, default=20261009)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--execution-iterations", type=int, default=50)
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument(
        "--experiments-root",
        type=Path,
        default=None,
        help="Filesystem root for experiment persistence",
    )
    parser.add_argument(
        "--config-out",
        type=Path,
        default=Path("experiments/configurations/phase10-held-out-config.json"),
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=Path("experiments/reports/phase10-held-out-evaluation.json"),
    )
    parser.add_argument(
        "--report-md",
        type=Path,
        default=Path("experiments/reports/phase10-held-out-evaluation.md"),
    )
    parser.add_argument(
        "--skip-persist",
        action="store_true",
        help="Do not write raw observations to the experiment store",
    )
    args = parser.parse_args(argv)

    try:
        import z3  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        payload = _write_unavailable_report(
            blocker=f"z3 import failed: {exc}",
            seed=args.seed,
            timeout=args.timeout,
            execution_iterations=args.execution_iterations,
            trials=args.trials,
            config_out=args.config_out,
            report_json=args.report_json,
            report_md=args.report_md,
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        print(f"DEPENDENCY_BLOCKER: {payload['dependency_blocker']}", file=sys.stderr)
        return 0

    from veriforge.evaluation_engine import (
        make_evaluation_configuration,
        report_to_mapping,
        run_held_out_evaluation,
        save_evaluation_configuration,
        write_evaluation_report,
    )
    from veriforge.storage.database import ExperimentStore

    config = make_evaluation_configuration(
        random_seed=args.seed,
        solver_timeout_seconds=args.timeout,
        execution_iterations=args.execution_iterations,
        trials_per_case=args.trials,
        notes=(
            "scripts/run_held_out_evaluation.py — Phase 10 held-out evaluation"
        ),
    )
    save_evaluation_configuration(config, args.config_out)

    store = None
    if not args.skip_persist:
        store = ExperimentStore(root=args.experiments_root)
    try:
        report = run_held_out_evaluation(
            config,
            store=store,
            persist=not args.skip_persist,
        )
    finally:
        if store is not None:
            store.close()

    write_evaluation_report(
        report, json_path=args.report_json, markdown_path=args.report_md
    )
    summary = report_to_mapping(report)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if report.dependency_blocker:
        print(f"DEPENDENCY_BLOCKER: {report.dependency_blocker}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
