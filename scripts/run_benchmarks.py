#!/usr/bin/env python3
"""Run a Phase 6 development-partition benchmark for engine validation.

This is not held-out evaluation and not a research conclusion.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from veriforge.benchmark_engine import (
    BENCHMARK_PROTOCOL_VERSION,
    load_development_cases_for_engine_validation,
    make_benchmark_configuration,
    rerun_benchmark_from_saved_configuration,
    run_benchmark,
    save_benchmark_configuration,
)
from veriforge.models import DatasetPartition
from veriforge.storage.database import ExperimentStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run VERIFORGE Phase 6 benchmark engine validation on the "
            "development dataset. Not a research conclusion."
        )
    )
    parser.add_argument(
        "--case-id",
        action="append",
        dest="case_ids",
        help="Restrict to one or more development case ids (repeatable)",
    )
    parser.add_argument("--trials", type=int, default=2)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--seed", type=int, default=20261009)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--execution-iterations", type=int, default=25)
    parser.add_argument(
        "--experiments-root",
        type=Path,
        default=None,
        help="Filesystem root for experiment persistence",
    )
    parser.add_argument(
        "--save-config",
        type=Path,
        default=None,
        help="Write the benchmark configuration JSON to this path",
    )
    parser.add_argument(
        "--rerun-from",
        type=Path,
        default=None,
        help="Rerun from a previously saved configuration JSON",
    )
    parser.add_argument(
        "--json-summary",
        type=Path,
        default=None,
        help="Write a non-research summary JSON (medians/rates only)",
    )
    args = parser.parse_args(argv)

    cases = load_development_cases_for_engine_validation()
    store = ExperimentStore(root=args.experiments_root)

    try:
        if args.rerun_from is not None:
            run_id, measurements, report = rerun_benchmark_from_saved_configuration(
                args.rerun_from,
                cases,
                store=store,
                persist=True,
            )
            config_path = args.rerun_from
        else:
            config = make_benchmark_configuration(
                trials_per_case=args.trials,
                warmup_trials=args.warmup,
                random_seed=args.seed,
                solver_timeout_seconds=args.timeout,
                execution_iterations=args.execution_iterations,
                dataset_partition=DatasetPartition.DEVELOPMENT,
                case_ids=args.case_ids,
                notes=(
                    "scripts/run_benchmarks.py engine validation — "
                    "not a research conclusion"
                ),
            )
            if args.save_config is not None:
                config_path = save_benchmark_configuration(config, args.save_config)
            else:
                config_path = None
            run_id, measurements, report = run_benchmark(
                config, cases, store=store, persist=True
            )
    finally:
        store.close()

    summary = {
        "run_id": run_id,
        "protocol_version": BENCHMARK_PROTOCOL_VERSION,
        "measurement_count": report.measurement_count,
        "summarized_trial_count": report.summarized_trial_count,
        "is_research_conclusion": report.is_research_conclusion,
        "nondeterminism_disclosure": report.nondeterminism_disclosure,
        "speedup_claim_policy": report.speedup_claim_policy,
        "rates": {
            "timeout_rate": report.rates.timeout_rate,
            "unknown_rate": report.rates.unknown_rate,
            "completion_rate": report.rates.completion_rate,
            "rejection_rate": report.rates.rejection_rate,
            "counterexample_rate": report.rates.counterexample_rate,
            "sample_count": report.rates.sample_count,
        },
        "timing_medians_seconds": {
            row.quantity: row.median_seconds for row in report.timing
        },
        "config_path": None if config_path is None else str(config_path),
        "label": "engine_validation_only",
    }
    text = json.dumps(summary, indent=2, sort_keys=True)
    print(text)
    if args.json_summary is not None:
        args.json_summary.parent.mkdir(parents=True, exist_ok=True)
        args.json_summary.write_text(text + "\n", encoding="utf-8")

    # Sanity: ensure separated timing keys exist in at least one measurement.
    if measurements:
        m0 = next(m for m in measurements if not m.is_warmup)
        required = (
            "parsing_seconds",
            "optimization_seconds",
            "candidate_generation_seconds",
            "translation_seconds",
            "solver_seconds",
            "end_to_end_verification_seconds",
            "original_execution_seconds",
            "optimized_execution_seconds",
        )
        for name in required:
            if not hasattr(m0, name):
                print(f"missing timing field: {name}", file=sys.stderr)
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
