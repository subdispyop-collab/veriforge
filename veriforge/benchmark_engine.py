"""Benchmark engine: separate timing of verification stages and expression execution.

Phase 6 implements specification §10. It measures parsing, optimization,
candidate generation, AST-to-Z3 translation, solver time, end-to-end
verification, and original vs optimized execution as independent quantities.
It does not run held-out final evaluation as a research conclusion and does
not claim execution speedup from shorter expressions or faster solver returns.
"""

from __future__ import annotations

import json
import math
import os
import platform
import statistics
import uuid
from dataclasses import asdict
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable, Mapping, Sequence

import z3

from veriforge.config import ResourceLimits, SemanticConfiguration
from veriforge.dataset_engine import load_bundle
from veriforge.exceptions import BenchmarkError
from veriforge.experiment_engine import (
    configuration_fingerprint,
    create_experiment_run,
    make_observation,
    new_run_id,
    persist_run_with_observations,
    utc_now_iso,
)
from veriforge.models import (
    BaselineId,
    BenchmarkConfiguration,
    BenchmarkMeasurement,
    BenchmarkRateSummary,
    BenchmarkReport,
    CandidateDecision,
    DatasetCase,
    DatasetPartition,
    EnvironmentRecord,
    ExpectedOutcome,
    ObservationKind,
    SemanticMode,
    TimeoutPolicy,
    TimingStatistic,
    TransformationCategory,
    VerificationStatus,
    WarmupPolicy,
)
from veriforge.optimizer_engine import (
    expression_from_root,
    find_applicable_matches,
    optimize,
    replace_at_path,
)
from veriforge.parser_engine import parse_expression
from veriforge.reference_evaluator import evaluate
from veriforge.storage.database import ExperimentStore
from veriforge.verifier_engine import verify_equivalence_timed
from veriforge.version import __version__ as SOFTWARE_VERSION

BENCHMARK_PROTOCOL_VERSION = "0.6.0"
BENCHMARK_PROTOCOL_ID = "veriforge-phase6-benchmark-protocol"

# Named timing quantities stored separately (§10).
TIMING_QUANTITIES: tuple[str, ...] = (
    "parsing_seconds",
    "optimization_seconds",
    "candidate_generation_seconds",
    "translation_seconds",
    "solver_seconds",
    "end_to_end_verification_seconds",
    "original_execution_seconds",
    "optimized_execution_seconds",
)

DEFAULT_TRIALS_PER_CASE = 3
DEFAULT_WARMUP_TRIALS = 1
DEFAULT_EXECUTION_ITERATIONS = 50
DEFAULT_BENCHMARK_SEED = 20261009


def new_measurement_id() -> str:
    return str(uuid.uuid4())


def new_configuration_id() -> str:
    return str(uuid.uuid4())


def collect_environment(
    *,
    extra: Mapping[str, str] | None = None,
) -> EnvironmentRecord:
    """Record software and hardware environment for a benchmark run."""

    z3_version: str | None
    try:
        z3_version = z3.get_version_string()
    except Exception:  # noqa: BLE001
        raw = getattr(z3, "__version__", None)
        z3_version = None if raw is None else str(raw)

    try:
        cpu_count = os.cpu_count()
    except Exception:  # noqa: BLE001
        cpu_count = None

    return EnvironmentRecord(
        python_version=platform.python_version(),
        platform=platform.platform(),
        machine=platform.machine(),
        processor=platform.processor() or "",
        system=platform.system(),
        z3_version=z3_version,
        veriforge_version=SOFTWARE_VERSION,
        cpu_count=cpu_count,
        extra=dict(extra or {}),
    )


def make_benchmark_configuration(
    *,
    trials_per_case: int = DEFAULT_TRIALS_PER_CASE,
    warmup_trials: int = DEFAULT_WARMUP_TRIALS,
    warmup_policy: WarmupPolicy = WarmupPolicy.DISCARD_FROM_SUMMARY,
    random_seed: int = DEFAULT_BENCHMARK_SEED,
    timeout_policy: TimeoutPolicy = TimeoutPolicy.FIXED_SOLVER_TIMEOUT,
    solver_timeout_seconds: float = 5.0,
    execution_iterations: int = DEFAULT_EXECUTION_ITERATIONS,
    dataset_version: str | None = "0.5.0",
    dataset_partition: DatasetPartition | None = DatasetPartition.DEVELOPMENT,
    case_ids: Sequence[str] | None = None,
    baseline_id: BaselineId | None = BaselineId.VERIFICATION_ENABLED,
    semantic_mode: SemanticMode | None = None,
    bit_width: int | None = None,
    environment: EnvironmentRecord | None = None,
    notes: str | None = None,
    configuration_id: str | None = None,
    protocol_version: str = BENCHMARK_PROTOCOL_VERSION,
    collect_env: bool = True,
) -> BenchmarkConfiguration:
    """Build a controlled benchmark configuration (§10.1)."""

    env = environment
    if env is None and collect_env:
        env = collect_environment()
    return BenchmarkConfiguration(
        configuration_id=configuration_id or new_configuration_id(),
        protocol_version=protocol_version,
        trials_per_case=trials_per_case,
        warmup_trials=warmup_trials,
        warmup_policy=warmup_policy,
        random_seed=random_seed,
        timeout_policy=timeout_policy,
        solver_timeout_seconds=solver_timeout_seconds,
        execution_iterations=execution_iterations,
        dataset_version=dataset_version,
        dataset_partition=dataset_partition,
        case_ids=None if case_ids is None else tuple(case_ids),
        baseline_id=baseline_id,
        semantic_mode=semantic_mode,
        bit_width=bit_width,
        environment=env,
        notes=notes,
    )


def configuration_to_mapping(config: BenchmarkConfiguration) -> dict[str, Any]:
    """Serialize a benchmark configuration to a JSON-friendly mapping."""

    env = config.environment
    return {
        "benchmark_protocol_id": BENCHMARK_PROTOCOL_ID,
        "benchmark_protocol_version": config.protocol_version,
        "configuration_id": config.configuration_id,
        "trials_per_case": config.trials_per_case,
        "warmup_trials": config.warmup_trials,
        "warmup_policy": config.warmup_policy.value,
        "random_seed": config.random_seed,
        "timeout_policy": config.timeout_policy.value,
        "solver_timeout_seconds": config.solver_timeout_seconds,
        "execution_iterations": config.execution_iterations,
        "dataset_version": config.dataset_version,
        "dataset_partition": (
            None
            if config.dataset_partition is None
            else config.dataset_partition.value
        ),
        "case_ids": None if config.case_ids is None else list(config.case_ids),
        "baseline_id": None if config.baseline_id is None else config.baseline_id.value,
        "semantic_mode": (
            None if config.semantic_mode is None else config.semantic_mode.value
        ),
        "bit_width": config.bit_width,
        "environment": None if env is None else _environment_to_mapping(env),
        "notes": config.notes,
        "nondeterminism_disclosure": config.nondeterminism_disclosure,
        "is_research_conclusion": False,
        "execute_held_out_evaluation": False,
    }


def configuration_from_mapping(data: Mapping[str, Any]) -> BenchmarkConfiguration:
    """Rebuild a BenchmarkConfiguration from a saved mapping."""

    case_ids = data.get("case_ids")
    env_data = data.get("environment")
    partition = data.get("dataset_partition")
    baseline = data.get("baseline_id")
    mode = data.get("semantic_mode")
    default_disclosure = BenchmarkConfiguration.__dataclass_fields__[
        "nondeterminism_disclosure"
    ].default
    return BenchmarkConfiguration(
        configuration_id=str(data["configuration_id"]),
        protocol_version=str(
            data.get("protocol_version")
            or data.get("benchmark_protocol_version")
            or BENCHMARK_PROTOCOL_VERSION
        ),
        trials_per_case=int(data["trials_per_case"]),
        warmup_trials=int(data["warmup_trials"]),
        warmup_policy=WarmupPolicy(str(data["warmup_policy"])),
        random_seed=int(data["random_seed"]),
        timeout_policy=TimeoutPolicy(str(data["timeout_policy"])),
        solver_timeout_seconds=float(data["solver_timeout_seconds"]),
        execution_iterations=int(data["execution_iterations"]),
        dataset_version=(
            None if data.get("dataset_version") is None else str(data["dataset_version"])
        ),
        dataset_partition=(
            None if partition is None else DatasetPartition(str(partition))
        ),
        case_ids=None if case_ids is None else tuple(str(x) for x in case_ids),
        baseline_id=None if baseline is None else BaselineId(str(baseline)),
        semantic_mode=None if mode is None else SemanticMode(str(mode)),
        bit_width=None if data.get("bit_width") is None else int(data["bit_width"]),
        environment=(
            None if env_data is None else _environment_from_mapping(env_data)
        ),
        notes=None if data.get("notes") is None else str(data["notes"]),
        nondeterminism_disclosure=str(
            data.get("nondeterminism_disclosure") or default_disclosure
        ),
    )


def _environment_to_mapping(env: EnvironmentRecord) -> dict[str, Any]:
    return {
        "python_version": env.python_version,
        "platform": env.platform,
        "machine": env.machine,
        "processor": env.processor,
        "system": env.system,
        "z3_version": env.z3_version,
        "veriforge_version": env.veriforge_version,
        "cpu_count": env.cpu_count,
        "extra": dict(env.extra),
    }


def _environment_from_mapping(data: Mapping[str, Any]) -> EnvironmentRecord:
    return EnvironmentRecord(
        python_version=str(data["python_version"]),
        platform=str(data["platform"]),
        machine=str(data["machine"]),
        processor=str(data.get("processor") or ""),
        system=str(data["system"]),
        z3_version=(
            None if data.get("z3_version") is None else str(data["z3_version"])
        ),
        veriforge_version=str(data["veriforge_version"]),
        cpu_count=(
            None if data.get("cpu_count") is None else int(data["cpu_count"])
        ),
        extra={str(k): str(v) for k, v in dict(data.get("extra") or {}).items()},
    )


def _semantic_config_for_case(
    case: DatasetCase,
    *,
    solver_timeout_seconds: float,
) -> SemanticConfiguration:
    return SemanticConfiguration(
        mode=case.semantic_mode,
        bit_width=case.bit_width or 32,
        limits=ResourceLimits(solver_timeout_seconds=solver_timeout_seconds),
    )


def _default_assignment(
    variables: Iterable[str], config: SemanticConfiguration
) -> dict[str, int]:
    """Deterministic assignment for execution timing (not a research workload)."""

    assignment: dict[str, int] = {}
    for index, name in enumerate(sorted(variables)):
        if config.mode is SemanticMode.MODE_B:
            assignment[name] = index % max(1, config.max_unsigned)
        else:
            assignment[name] = index + 1
    return assignment


def _time_call(fn: Any) -> tuple[float, Any]:
    start = perf_counter()
    result = fn()
    return perf_counter() - start, result


def measure_verification_stages(
    original_source: str,
    candidate_source: str,
    config: SemanticConfiguration,
) -> dict[str, Any]:
    """Measure translation, solver, and end-to-end verification separately."""

    timed = verify_equivalence_timed(original_source, candidate_source, config)
    result = timed.result
    counterexample_recorded = (
        result.status is VerificationStatus.COUNTEREXAMPLE_FOUND
        and result.counterexample is not None
    )
    return {
        "parsing_seconds": timed.parsing_seconds,
        "translation_seconds": timed.translation_seconds,
        "solver_seconds": timed.solver_seconds,
        "end_to_end_verification_seconds": timed.end_to_end_seconds,
        "verification_status": result.status,
        "counterexample_recorded": counterexample_recorded,
        "error": result.reason
        if result.status
        in {
            VerificationStatus.TRANSLATION_ERROR,
            VerificationStatus.VERIFICATION_ERROR,
            VerificationStatus.INVALID_INPUT,
            VerificationStatus.UNSUPPORTED,
        }
        else None,
        "verification_result": result,
    }


def measure_candidate_generation(
    original_source: str,
    config: SemanticConfiguration,
) -> dict[str, Any]:
    """Time rule selection and candidate rewrite without calling the solver."""

    parse_t, original = _time_call(lambda: parse_expression(original_source, config))
    gen_start = perf_counter()
    matches = find_applicable_matches(original, config)
    candidate_source: str | None = None
    if matches:
        match = matches[0]
        candidate_root = replace_at_path(original.root, match.path, match.after)
        candidate = expression_from_root(candidate_root)
        candidate_source = candidate.source
    generation_seconds = perf_counter() - gen_start
    return {
        "parsing_seconds": parse_t,
        "candidate_generation_seconds": generation_seconds,
        "candidate_source": candidate_source,
        "original_expr": original,
        "match_found": bool(matches),
    }


def measure_optimization(
    original_source: str,
    config: SemanticConfiguration,
) -> dict[str, Any]:
    """Time the production optimizer wall clock.

    Includes internal verification. Solver and translation remain separately
    measured via ``measure_verification_stages``. Do not treat this field as
    execution-speedup evidence (§10.2).
    """

    t, result = _time_call(lambda: optimize(original_source, config))
    accepted = result.accepted
    rejected = any(
        step.decision is CandidateDecision.REJECTED for step in result.trace
    )
    any_accepted = any(
        step.decision is CandidateDecision.ACCEPTED for step in result.trace
    )
    return {
        "optimization_seconds": t,
        "optimized_source": accepted.source,
        "candidate_accepted": any_accepted
        or accepted.source != result.original.source,
        "rejection_recorded": rejected,
        "trace_len": len(result.trace),
        "optimization_result": result,
    }


def measure_execution(
    expression_source: str,
    config: SemanticConfiguration,
    *,
    iterations: int,
) -> float:
    """Measure reference-evaluator execution time for one expression.

    Uses a deterministic assignment. This is execution performance, not solver
    latency, and must be reported separately (§10 / §10.2).
    """

    expr = parse_expression(expression_source, config)
    assignment = _default_assignment(expr.variables, config)
    evaluate(expr, assignment, config)
    start = perf_counter()
    for _ in range(iterations):
        evaluate(expr, assignment, config)
    return perf_counter() - start


def run_case_trial(
    case: DatasetCase,
    *,
    run_id: str,
    trial_index: int,
    is_warmup: bool,
    seed: int,
    config: BenchmarkConfiguration,
) -> BenchmarkMeasurement:
    """Run one timed trial for a dataset case with separated measurements."""

    semantic = _semantic_config_for_case(
        case, solver_timeout_seconds=config.solver_timeout_seconds
    )
    original_source = case.original_source
    candidate_source = case.candidate_source
    error: str | None = None

    parsing_seconds: float | None = None
    optimization_seconds: float | None = None
    candidate_generation_seconds: float | None = None
    translation_seconds: float | None = None
    solver_seconds: float | None = None
    e2e_seconds: float | None = None
    original_exec: float | None = None
    optimized_exec: float | None = None
    status: VerificationStatus | None = None
    candidate_accepted: bool | None = None
    rejection_recorded = False
    counterexample_recorded = False
    optimized_source: str | None = None
    measured_candidate = candidate_source

    try:
        gen = measure_candidate_generation(original_source, semantic)
        parsing_seconds = gen["parsing_seconds"]
        candidate_generation_seconds = gen["candidate_generation_seconds"]
        if measured_candidate is None:
            measured_candidate = gen["candidate_source"]

        if case.expected_outcome is not ExpectedOutcome.PARSE_REJECT:
            opt = measure_optimization(original_source, semantic)
            optimization_seconds = opt["optimization_seconds"]
            optimized_source = opt["optimized_source"]
            candidate_accepted = opt["candidate_accepted"]
            rejection_recorded = opt["rejection_recorded"]

        verify_target = measured_candidate or optimized_source
        if verify_target is not None:
            stages = measure_verification_stages(
                original_source, verify_target, semantic
            )
            if stages["parsing_seconds"] is not None and parsing_seconds is not None:
                parsing_seconds = (
                    parsing_seconds + float(stages["parsing_seconds"])
                ) / 2.0
            elif stages["parsing_seconds"] is not None:
                parsing_seconds = float(stages["parsing_seconds"])
            translation_seconds = stages["translation_seconds"]
            solver_seconds = stages["solver_seconds"]
            e2e_seconds = stages["end_to_end_verification_seconds"]
            status = stages["verification_status"]
            counterexample_recorded = bool(stages["counterexample_recorded"])
            if stages["error"]:
                error = stages["error"]
            if status is VerificationStatus.COUNTEREXAMPLE_FOUND:
                rejection_recorded = True
                candidate_accepted = False

        try:
            original_exec = measure_execution(
                original_source,
                semantic,
                iterations=config.execution_iterations,
            )
            exec_target = optimized_source or verify_target
            if exec_target is not None:
                optimized_exec = measure_execution(
                    exec_target,
                    semantic,
                    iterations=config.execution_iterations,
                )
        except Exception as exc:  # noqa: BLE001
            if error is None:
                error = f"execution timing failed: {exc}"
    except Exception as exc:  # noqa: BLE001
        error = str(exc)

    return BenchmarkMeasurement(
        measurement_id=new_measurement_id(),
        run_id=run_id,
        case_id=case.case_id,
        trial_index=trial_index,
        is_warmup=is_warmup,
        seed=seed,
        parsing_seconds=parsing_seconds,
        optimization_seconds=optimization_seconds,
        candidate_generation_seconds=candidate_generation_seconds,
        translation_seconds=translation_seconds,
        solver_seconds=solver_seconds,
        end_to_end_verification_seconds=e2e_seconds,
        original_execution_seconds=original_exec,
        optimized_execution_seconds=optimized_exec,
        verification_status=status,
        candidate_accepted=candidate_accepted,
        rejection_recorded=rejection_recorded,
        counterexample_recorded=counterexample_recorded,
        original_source=original_source,
        candidate_source=measured_candidate,
        optimized_source=optimized_source,
        transformation_category=case.transformation_category,
        error=error,
        recorded_at_utc=utc_now_iso(),
    )


def select_cases(
    cases: Sequence[DatasetCase],
    config: BenchmarkConfiguration,
) -> tuple[DatasetCase, ...]:
    """Select cases for a benchmark run."""

    selected = list(cases)
    if config.case_ids is not None:
        wanted = set(config.case_ids)
        selected = [c for c in selected if c.case_id in wanted]
        missing = wanted - {c.case_id for c in selected}
        if missing:
            raise BenchmarkError(f"unknown case_ids: {sorted(missing)}")
    if config.semantic_mode is not None:
        selected = [c for c in selected if c.semantic_mode is config.semantic_mode]
    if config.bit_width is not None:
        selected = [
            c
            for c in selected
            if c.bit_width == config.bit_width
            or (c.bit_width is None and c.semantic_mode is SemanticMode.MODE_A)
        ]
    return tuple(selected)


def run_benchmark(
    config: BenchmarkConfiguration,
    cases: Sequence[DatasetCase],
    *,
    run_id: str | None = None,
    store: ExperimentStore | None = None,
    persist: bool = True,
) -> tuple[str, tuple[BenchmarkMeasurement, ...], BenchmarkReport]:
    """Execute a benchmark with warmups, repeated trials, and raw saves.

    Development datasets validate the engine. Results are labeled
    ``is_research_conclusion=False`` and must not be treated as final findings.
    Held-out evaluation as a research conclusion is out of scope for Phase 6.
    """

    if config.dataset_partition is DatasetPartition.HELD_OUT:
        raise BenchmarkError(
            "Phase 6 forbids held-out final evaluation as a research conclusion; "
            "use the development partition for engine validation"
        )

    selected = select_cases(cases, config)
    if not selected:
        raise BenchmarkError("no cases selected for benchmark")

    rid = run_id or new_run_id()
    cfg_map = configuration_to_mapping(config)
    experiment_run = create_experiment_run(
        configuration=cfg_map,
        baseline_id=config.baseline_id,
        dataset_version=config.dataset_version,
        dataset_partition=config.dataset_partition,
        random_seed=config.random_seed,
        semantic_mode=config.semantic_mode,
        bit_width=config.bit_width,
        notes=config.notes
        or "Phase 6 benchmark engine validation — not a research conclusion",
        run_id=rid,
        protocol_version=config.protocol_version,
    )

    measurements: list[BenchmarkMeasurement] = []
    trial_seed = config.random_seed
    for case in selected:
        for w in range(config.warmup_trials):
            measurements.append(
                run_case_trial(
                    case,
                    run_id=rid,
                    trial_index=-(w + 1),
                    is_warmup=True,
                    seed=trial_seed + w,
                    config=config,
                )
            )
        for t in range(config.trials_per_case):
            measurements.append(
                run_case_trial(
                    case,
                    run_id=rid,
                    trial_index=t,
                    is_warmup=False,
                    seed=trial_seed + config.warmup_trials + t,
                    config=config,
                )
            )
        trial_seed += 1000

    report = summarize_measurements(
        rid,
        config,
        measurements,
        fingerprint=experiment_run.configuration_fingerprint,
    )

    if persist:
        owns_store = store is None
        active_store = store or ExperimentStore()
        try:
            observations = [measurement_to_observation(m) for m in measurements]
            persist_run_with_observations(
                experiment_run, observations, store=active_store
            )
            _write_configuration_snapshot(active_store.root, rid, config, report)
        finally:
            if owns_store:
                active_store.close()

    return rid, tuple(measurements), report


def _write_configuration_snapshot(
    root: Path,
    run_id: str,
    config: BenchmarkConfiguration,
    report: BenchmarkReport,
) -> Path:
    run_dir = Path(root) / "raw" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "benchmark_configuration.json"
    payload = {
        "configuration": configuration_to_mapping(config),
        "report_summary": {
            "run_id": report.run_id,
            "configuration_id": report.configuration_id,
            "configuration_fingerprint": report.configuration_fingerprint,
            "measurement_count": report.measurement_count,
            "summarized_trial_count": report.summarized_trial_count,
            "rates": asdict(report.rates),
            "nondeterminism_disclosure": report.nondeterminism_disclosure,
            "speedup_claim_policy": report.speedup_claim_policy,
            "is_research_conclusion": report.is_research_conclusion,
        },
    }
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def measurement_to_observation(measurement: BenchmarkMeasurement) -> Any:
    """Convert a BenchmarkMeasurement into a RawObservation for persistence."""

    payload = {
        "measurement_id": measurement.measurement_id,
        "case_id": measurement.case_id,
        "trial_index": measurement.trial_index,
        "is_warmup": measurement.is_warmup,
        "seed": measurement.seed,
        "parsing_seconds": measurement.parsing_seconds,
        "optimization_seconds": measurement.optimization_seconds,
        "candidate_generation_seconds": measurement.candidate_generation_seconds,
        "translation_seconds": measurement.translation_seconds,
        "solver_seconds": measurement.solver_seconds,
        "end_to_end_verification_seconds": measurement.end_to_end_verification_seconds,
        "original_execution_seconds": measurement.original_execution_seconds,
        "optimized_execution_seconds": measurement.optimized_execution_seconds,
        "candidate_accepted": measurement.candidate_accepted,
        "rejection_recorded": measurement.rejection_recorded,
        "counterexample_recorded": measurement.counterexample_recorded,
        "original_source": measurement.original_source,
        "candidate_source": measurement.candidate_source,
        "optimized_source": measurement.optimized_source,
        "error": measurement.error,
        "timings_stored_separately": True,
        "is_research_conclusion": False,
    }
    return make_observation(
        run_id=measurement.run_id,
        kind=ObservationKind.BENCHMARK_TIMING,
        case_id=measurement.case_id,
        transformation_category=measurement.transformation_category,
        verification_status=measurement.verification_status,
        detected_as_non_equivalent=(
            True if measurement.counterexample_recorded else None
        ),
        payload=payload,
        observation_id=measurement.measurement_id,
        recorded_at_utc=measurement.recorded_at_utc or utc_now_iso(),
    )


def measurement_from_observation_payload(
    *,
    run_id: str,
    observation_id: str,
    case_id: str | None,
    verification_status: VerificationStatus | None,
    transformation_category: TransformationCategory | None,
    payload: Mapping[str, Any],
    recorded_at_utc: str,
) -> BenchmarkMeasurement:
    """Rebuild a BenchmarkMeasurement from a stored observation payload."""

    return BenchmarkMeasurement(
        measurement_id=str(payload.get("measurement_id") or observation_id),
        run_id=run_id,
        case_id=str(case_id or payload.get("case_id") or ""),
        trial_index=int(payload["trial_index"]),
        is_warmup=bool(payload["is_warmup"]),
        seed=int(payload["seed"]),
        parsing_seconds=_opt_float(payload.get("parsing_seconds")),
        optimization_seconds=_opt_float(payload.get("optimization_seconds")),
        candidate_generation_seconds=_opt_float(
            payload.get("candidate_generation_seconds")
        ),
        translation_seconds=_opt_float(payload.get("translation_seconds")),
        solver_seconds=_opt_float(payload.get("solver_seconds")),
        end_to_end_verification_seconds=_opt_float(
            payload.get("end_to_end_verification_seconds")
        ),
        original_execution_seconds=_opt_float(
            payload.get("original_execution_seconds")
        ),
        optimized_execution_seconds=_opt_float(
            payload.get("optimized_execution_seconds")
        ),
        verification_status=verification_status,
        candidate_accepted=(
            None
            if payload.get("candidate_accepted") is None
            else bool(payload["candidate_accepted"])
        ),
        rejection_recorded=bool(payload.get("rejection_recorded")),
        counterexample_recorded=bool(payload.get("counterexample_recorded")),
        original_source=str(payload.get("original_source") or ""),
        candidate_source=(
            None
            if payload.get("candidate_source") is None
            else str(payload["candidate_source"])
        ),
        optimized_source=(
            None
            if payload.get("optimized_source") is None
            else str(payload["optimized_source"])
        ),
        transformation_category=transformation_category,
        error=None if payload.get("error") is None else str(payload["error"]),
        recorded_at_utc=recorded_at_utc,
    )


def _opt_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _summarizable(
    measurements: Sequence[BenchmarkMeasurement],
    policy: WarmupPolicy,
) -> tuple[BenchmarkMeasurement, ...]:
    if policy is WarmupPolicy.INCLUDE_IN_SUMMARY:
        return tuple(measurements)
    return tuple(m for m in measurements if not m.is_warmup)


def compute_timing_statistic(
    quantity: str,
    values: Sequence[float],
) -> TimingStatistic:
    """Median and variability for one timing quantity."""

    if not values:
        return TimingStatistic(
            quantity=quantity,
            sample_count=0,
            median_seconds=None,
            mean_seconds=None,
            min_seconds=None,
            max_seconds=None,
            stdev_seconds=None,
            iqr_seconds=None,
            values_seconds=(),
        )
    ordered = tuple(sorted(values))
    median = statistics.median(ordered)
    mean = statistics.fmean(ordered)
    stdev = statistics.stdev(ordered) if len(ordered) >= 2 else 0.0
    lower_half = ordered[: len(ordered) // 2]
    upper_half = ordered[(len(ordered) + 1) // 2 :]
    q1 = statistics.median(lower_half) if lower_half else ordered[0]
    q3 = statistics.median(upper_half) if upper_half else ordered[-1]
    iqr = float(q3) - float(q1) if len(ordered) >= 2 else 0.0
    return TimingStatistic(
        quantity=quantity,
        sample_count=len(ordered),
        median_seconds=float(median),
        mean_seconds=float(mean),
        min_seconds=float(ordered[0]),
        max_seconds=float(ordered[-1]),
        stdev_seconds=float(stdev),
        iqr_seconds=float(iqr),
        values_seconds=ordered,
    )


def compute_rate_summary(
    measurements: Sequence[BenchmarkMeasurement],
) -> BenchmarkRateSummary:
    """Timeout, UNKNOWN, completion, rejection, and counterexample rates."""

    sample = len(measurements)
    timeout_count = 0
    unknown_count = 0
    completion_count = 0
    rejection_count = 0
    counterexample_count = 0

    terminal_complete = {
        VerificationStatus.EQUIVALENT_WITHIN_MODEL,
        VerificationStatus.COUNTEREXAMPLE_FOUND,
    }

    for m in measurements:
        if m.verification_status is VerificationStatus.TIMEOUT:
            timeout_count += 1
        elif m.verification_status is VerificationStatus.UNKNOWN:
            unknown_count += 1
        if m.verification_status in terminal_complete:
            completion_count += 1
        if m.rejection_recorded:
            rejection_count += 1
        if m.counterexample_recorded:
            counterexample_count += 1

    def rate(n: int) -> float | None:
        if sample == 0:
            return None
        return n / sample

    return BenchmarkRateSummary(
        sample_count=sample,
        timeout_count=timeout_count,
        unknown_count=unknown_count,
        completion_count=completion_count,
        rejection_count=rejection_count,
        counterexample_count=counterexample_count,
        timeout_rate=rate(timeout_count),
        unknown_rate=rate(unknown_count),
        completion_rate=rate(completion_count),
        rejection_rate=rate(rejection_count),
        counterexample_rate=rate(counterexample_count),
    )


def summarize_measurements(
    run_id: str,
    config: BenchmarkConfiguration,
    measurements: Sequence[BenchmarkMeasurement],
    *,
    fingerprint: str | None = None,
) -> BenchmarkReport:
    """Build a report with medians/variability; never a research conclusion."""

    subset = _summarizable(measurements, config.warmup_policy)
    timing_rows: list[TimingStatistic] = []
    for quantity in TIMING_QUANTITIES:
        values: list[float] = []
        for m in subset:
            raw = getattr(m, quantity)
            if raw is None:
                continue
            value = float(raw)
            if math.isnan(value):
                continue
            values.append(value)
        timing_rows.append(compute_timing_statistic(quantity, values))

    fp = fingerprint or configuration_fingerprint_from_config(config)
    return BenchmarkReport(
        run_id=run_id,
        configuration_id=config.configuration_id,
        configuration_fingerprint=fp,
        measurement_count=len(measurements),
        summarized_trial_count=len(subset),
        rates=compute_rate_summary(subset),
        timing=tuple(timing_rows),
        nondeterminism_disclosure=config.nondeterminism_disclosure,
        is_research_conclusion=False,
    )


def configuration_fingerprint_from_config(config: BenchmarkConfiguration) -> str:
    return configuration_fingerprint(configuration_to_mapping(config))


def assert_no_spurious_execution_speedup_claim(
    report: BenchmarkReport,
    *,
    claim_text: str,
) -> None:
    """Reject claims that infer execution speedup from solver or AST alone."""

    lowered = claim_text.lower()
    forbidden_patterns = (
        "shorter expression",
        "fewer nodes",
        "faster solver",
        "solver returned more quickly",
        "dashboard looks",
    )
    if any(p in lowered for p in forbidden_patterns):
        if "execution" in lowered and (
            "speedup" in lowered or "faster" in lowered or "improved" in lowered
        ):
            raise BenchmarkError(
                "Invalid performance claim under §10.2: execution speedup must "
                "not be inferred from shorter expressions, fewer AST nodes, "
                "faster solver returns, or dashboard appearance. "
                f"Policy: {report.speedup_claim_policy}"
            )


def load_benchmark_configuration(path: Path | str) -> BenchmarkConfiguration:
    """Load a saved benchmark configuration JSON (possibly wrapped)."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if "configuration" in data:
        data = data["configuration"]
    return configuration_from_mapping(data)


def save_benchmark_configuration(
    config: BenchmarkConfiguration,
    path: Path | str,
    *,
    controlled_root: Path | str | None = None,
) -> Path:
    """Save a benchmark configuration for later reproduction.

    When ``controlled_root`` is set, the target path must resolve under that
    root (§15 controlled export / config write paths).
    """

    target = Path(path)
    if controlled_root is not None:
        from veriforge.security import resolve_under_root

        target = resolve_under_root(Path(controlled_root), target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(configuration_to_mapping(config), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def rerun_benchmark_from_saved_configuration(
    path: Path | str,
    cases: Sequence[DatasetCase],
    *,
    store: ExperimentStore | None = None,
    persist: bool = True,
    refresh_environment: bool = True,
) -> tuple[str, tuple[BenchmarkMeasurement, ...], BenchmarkReport]:
    """Rerun a benchmark from a recorded configuration.

    Discloses nondeterminism: durations may differ across runs/platforms.
    """

    config = load_benchmark_configuration(path)
    if refresh_environment:
        env = collect_environment(
            extra={"reproduced_from": str(path), "reproduction": "true"}
        )
        config = BenchmarkConfiguration(
            configuration_id=config.configuration_id,
            protocol_version=config.protocol_version,
            trials_per_case=config.trials_per_case,
            warmup_trials=config.warmup_trials,
            warmup_policy=config.warmup_policy,
            random_seed=config.random_seed,
            timeout_policy=config.timeout_policy,
            solver_timeout_seconds=config.solver_timeout_seconds,
            execution_iterations=config.execution_iterations,
            dataset_version=config.dataset_version,
            dataset_partition=config.dataset_partition,
            case_ids=config.case_ids,
            baseline_id=config.baseline_id,
            semantic_mode=config.semantic_mode,
            bit_width=config.bit_width,
            environment=env,
            notes=(config.notes or "") + " [reproduction rerun]",
            nondeterminism_disclosure=config.nondeterminism_disclosure,
        )
    return run_benchmark(config, cases, store=store, persist=persist)


def load_development_cases_for_engine_validation(
    *,
    datasets_root: Path | None = None,
) -> tuple[DatasetCase, ...]:
    """Load development partition cases for benchmark-engine validation only."""

    bundle = load_bundle(DatasetPartition.DEVELOPMENT, root=datasets_root)
    return bundle.cases
