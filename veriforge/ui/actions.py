"""Application actions invoked by the Streamlit UI (no Streamlit imports).

Keeps parsing, optimization, verification, fuzzing, benchmarking, and audit
calls outside presentation widgets.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from veriforge.audit_engine import (
    export_audit_records,
    list_run_history,
    record_optimization_run,
    replay_optimization_from_record,
    verify_storage_integrity,
)
from veriforge.benchmark_engine import (
    make_benchmark_configuration,
    run_benchmark,
    save_benchmark_configuration,
)
from veriforge.config import SemanticConfiguration, default_limits
from veriforge.dataset_engine import load_bundle
from veriforge.exceptions import VeriforgeError
from veriforge.experiment_engine import (
    baseline_catalog,
    compute_metrics_for_stored_run,
)
from veriforge.fuzzer_suite import (
    DEFAULT_MUTATION_SEED,
    mutate_and_analyze,
    mutation_categories,
)
from veriforge.models import (
    BaselineId,
    BenchmarkConfiguration,
    BenchmarkMeasurement,
    BenchmarkReport,
    DatasetPartition,
    ExportFormat,
    MutationAnalysisResult,
    MutationCategory,
    OptimizationResult,
    OptimizationRunRecord,
    SemanticMode,
    VerificationResult,
    WarmupPolicy,
)
from veriforge.optimizer_engine import optimize, render_expr
from veriforge.parser_engine import parse_expression
from veriforge.storage import AuditRepository, ExperimentStore
from veriforge.verifier_engine import TimedVerificationResult, verify_equivalence_timed


@dataclass(frozen=True, slots=True)
class ParseOutcome:
    ok: bool
    source: str
    rendered: str | None
    variables: tuple[str, ...]
    error: str | None


@dataclass(frozen=True, slots=True)
class WorkbenchResult:
    parse: ParseOutcome
    optimization: OptimizationResult | None
    error: str | None


@dataclass(frozen=True, slots=True)
class ExplorerResult:
    timed: TimedVerificationResult | None
    error: str | None


@dataclass(frozen=True, slots=True)
class FuzzLabResult:
    analyses: tuple[MutationAnalysisResult, ...]
    seed: int
    categories: tuple[MutationCategory, ...]
    error: str | None


@dataclass(frozen=True, slots=True)
class BenchmarkLabResult:
    run_id: str | None
    measurements: tuple[BenchmarkMeasurement, ...]
    report: BenchmarkReport | None
    config_path: str | None
    error: str | None
    is_research_conclusion: bool = False


def build_semantic_configuration(
    *,
    mode: SemanticMode,
    bit_width: int = 32,
    solver_timeout_seconds: float = 5.0,
) -> SemanticConfiguration:
    """Construct a semantic configuration from UI controls."""

    limits = default_limits()
    if solver_timeout_seconds != limits.solver_timeout_seconds:
        cfg = SemanticConfiguration(mode=mode, bit_width=bit_width)
        return cfg.with_limits(solver_timeout_seconds=solver_timeout_seconds)
    return SemanticConfiguration(mode=mode, bit_width=bit_width)


def parse_for_workbench(
    source: str, config: SemanticConfiguration
) -> ParseOutcome:
    """Parse without optimizing; surface errors for the workbench."""

    try:
        expr = parse_expression(source, config)
    except VeriforgeError as exc:
        return ParseOutcome(
            ok=False,
            source=source,
            rendered=None,
            variables=(),
            error=str(exc),
        )
    return ParseOutcome(
        ok=True,
        source=source,
        rendered=render_expr(expr.root),
        variables=tuple(sorted(expr.variables)),
        error=None,
    )


def run_workbench(
    source: str, config: SemanticConfiguration
) -> WorkbenchResult:
    """Parse and run the verification-guided optimizer."""

    parse = parse_for_workbench(source, config)
    if not parse.ok:
        return WorkbenchResult(parse=parse, optimization=None, error=parse.error)
    try:
        result = optimize(source, config)
    except VeriforgeError as exc:
        return WorkbenchResult(parse=parse, optimization=None, error=str(exc))
    return WorkbenchResult(parse=parse, optimization=result, error=None)


def run_verification_explorer(
    original: str,
    candidate: str,
    config: SemanticConfiguration,
) -> ExplorerResult:
    """Compare original vs candidate with timed verification."""

    try:
        timed = verify_equivalence_timed(original, candidate, config)
    except VeriforgeError as exc:
        return ExplorerResult(timed=None, error=str(exc))
    return ExplorerResult(timed=timed, error=None)


def run_fuzz_lab(
    source: str,
    config: SemanticConfiguration,
    *,
    seed: int = DEFAULT_MUTATION_SEED,
    max_mutations: int | None = 32,
    category_values: Sequence[str] | None = None,
) -> FuzzLabResult:
    """Generate and analyze artificial mutations (EVALUATION_ONLY)."""

    categories: tuple[MutationCategory, ...]
    if category_values is None:
        categories = mutation_categories()
    else:
        selected: list[MutationCategory] = []
        for value in category_values:
            try:
                selected.append(MutationCategory(value))
            except ValueError:
                return FuzzLabResult(
                    analyses=(),
                    seed=seed,
                    categories=(),
                    error=f"unknown mutation category: {value!r}",
                )
        categories = tuple(selected)
    try:
        analyses = mutate_and_analyze(
            source,
            config,
            seed=seed,
            categories=categories,
            max_mutations=max_mutations,
        )
    except VeriforgeError as exc:
        return FuzzLabResult(
            analyses=(),
            seed=seed,
            categories=categories,
            error=str(exc),
        )
    return FuzzLabResult(
        analyses=analyses,
        seed=seed,
        categories=categories,
        error=None,
    )


def list_baseline_options() -> tuple[dict[str, str], ...]:
    """Return baseline catalog rows for UI selectors (defined, not measured)."""

    rows: list[dict[str, str]] = []
    for baseline in baseline_catalog():
        rows.append(
            {
                "id": baseline.baseline_id.value,
                "name": baseline.name,
                "status": baseline.status,
                "description": baseline.description,
            }
        )
    return tuple(rows)


def list_development_case_ids(*, root: Path | None = None) -> tuple[str, ...]:
    """Case ids from the development partition (engine validation only)."""

    bundle = load_bundle(DatasetPartition.DEVELOPMENT, root=root)
    return tuple(case.case_id for case in bundle.cases)


def run_benchmark_lab(
    *,
    case_ids: Sequence[str],
    trials_per_case: int = 2,
    warmup_trials: int = 1,
    random_seed: int = 20261009,
    solver_timeout_seconds: float = 5.0,
    baseline_id: BaselineId | None = BaselineId.VERIFICATION_ENABLED,
    experiments_root: Path | None = None,
    save_config_dir: Path | None = None,
) -> BenchmarkLabResult:
    """Run a development-partition benchmark; never claims research conclusion."""

    if not case_ids:
        return BenchmarkLabResult(
            run_id=None,
            measurements=(),
            report=None,
            config_path=None,
            error="Select at least one development dataset case.",
        )
    try:
        bundle = load_bundle(DatasetPartition.DEVELOPMENT)
        cases = tuple(c for c in bundle.cases if c.case_id in set(case_ids))
        if not cases:
            return BenchmarkLabResult(
                run_id=None,
                measurements=(),
                report=None,
                config_path=None,
                error="No matching development cases for the selected ids.",
            )
        config = make_benchmark_configuration(
            trials_per_case=trials_per_case,
            warmup_trials=warmup_trials,
            warmup_policy=WarmupPolicy.DISCARD_FROM_SUMMARY,
            random_seed=random_seed,
            solver_timeout_seconds=solver_timeout_seconds,
            dataset_version=bundle.metadata.dataset_version,
            dataset_partition=DatasetPartition.DEVELOPMENT,
            case_ids=tuple(case_ids),
            baseline_id=baseline_id,
            notes=(
                "Streamlit Benchmark Lab — development partition engine "
                "validation; not a research conclusion"
            ),
        )
        store = ExperimentStore(root=experiments_root) if experiments_root else None
        try:
            run_id, measurements, report = run_benchmark(
                config, cases, store=store, persist=True
            )
        finally:
            if store is not None:
                store.close()
        config_path: str | None = None
        if save_config_dir is not None:
            save_config_dir = Path(save_config_dir)
            save_config_dir.mkdir(parents=True, exist_ok=True)
            path = save_config_dir / f"{config.configuration_id}.json"
            save_benchmark_configuration(config, path)
            config_path = str(path)
        return BenchmarkLabResult(
            run_id=run_id,
            measurements=measurements,
            report=report,
            config_path=config_path,
            error=None,
            is_research_conclusion=False,
        )
    except VeriforgeError as exc:
        return BenchmarkLabResult(
            run_id=None,
            measurements=(),
            report=None,
            config_path=None,
            error=str(exc),
        )


def load_research_metrics(
    *,
    experiments_root: Path | None = None,
) -> tuple[tuple[str, ...], Any | None, tuple[str, ...]]:
    """Load metrics for the most recent completed experiment run with observations.

    Returns ``(run_ids_with_observations, metrics_or_none, dataset_versions)``.
    Does not invent measurements.
    """

    store = ExperimentStore(root=experiments_root)
    try:
        # Newest first so metrics prefer the most recent completed run.
        runs = tuple(reversed(store.list_runs()))
        with_obs: list[str] = []
        dataset_versions: list[str] = []
        latest_metrics = None
        for run in runs:
            observations = store.load_observations(run.run_id)
            if not observations:
                continue
            with_obs.append(run.run_id)
            if run.dataset_version:
                dataset_versions.append(run.dataset_version)
            if latest_metrics is None:
                latest_metrics = compute_metrics_for_stored_run(
                    run.run_id, store=store
                )
        return tuple(with_obs), latest_metrics, tuple(sorted(set(dataset_versions)))
    finally:
        store.close()


def persist_optimization_result(
    result: OptimizationResult,
    *,
    repository: AuditRepository | None = None,
    root: Path | None = None,
) -> OptimizationRunRecord:
    """Persist an optimization result via the Phase 7 audit engine."""

    record, _event = record_optimization_run(
        result, repository=repository, root=root
    )
    return record


def audit_history(*, root: Path | None = None) -> tuple[dict[str, Any], ...]:
    return list_run_history(root=root)


def audit_export(
    *,
    format: ExportFormat,
    run_ids: Sequence[str] | None = None,
    root: Path | None = None,
) -> Mapping[str, Any]:
    result = export_audit_records(format=format, run_ids=run_ids, root=root)
    return {
        "export_id": result.export_id,
        "format": result.format.value,
        "filesystem_path": result.filesystem_path,
        "record_count": result.record_count,
        "run_ids": list(result.run_ids),
    }


def audit_replay(
    run_id: str, *, root: Path | None = None
) -> OptimizationResult:
    with AuditRepository(root=root) as repo:
        record = repo.get_optimization_run(run_id)
        if record is None:
            raise VeriforgeError(f"no optimization run recorded for {run_id!r}")
        return replay_optimization_from_record(record, repository=repo)


def audit_integrity(*, root: Path | None = None) -> Mapping[str, Any]:
    report = verify_storage_integrity(root=root)
    return {
        "passed": report.passed,
        "status": report.status.value,
        "runs_checked": report.runs_checked,
        "observations_checked": report.observations_checked,
        "audit_events_checked": report.audit_events_checked,
        "issues": [
            {"code": i.code, "path_or_id": i.path_or_id, "detail": i.detail}
            for i in report.issues
        ],
    }


def measurements_to_json_rows(
    measurements: Sequence[BenchmarkMeasurement],
) -> str:
    """Serialize raw benchmark measurements for export (no fabricated fields)."""

    rows = []
    for m in measurements:
        rows.append(
            {
                "measurement_id": m.measurement_id,
                "run_id": m.run_id,
                "case_id": m.case_id,
                "trial_index": m.trial_index,
                "is_warmup": m.is_warmup,
                "parsing_seconds": m.parsing_seconds,
                "optimization_seconds": m.optimization_seconds,
                "translation_seconds": m.translation_seconds,
                "solver_seconds": m.solver_seconds,
                "end_to_end_verification_seconds": m.end_to_end_verification_seconds,
                "original_execution_seconds": m.original_execution_seconds,
                "optimized_execution_seconds": m.optimized_execution_seconds,
                "verification_status": (
                    None
                    if m.verification_status is None
                    else m.verification_status.value
                ),
                "error": m.error,
            }
        )
    return json.dumps(rows, indent=2, sort_keys=True)
