"""Phase 10 held-out research evaluation.

Runs the frozen protocol against ``datasets/held_out/`` for implemented
baselines (§9.3). Stores raw observations, separates solver latency from
expression execution, and reports by transformation category with sample
sizes.

This module does not invent measurements. If runtime dependencies (notably
``z3``) are missing, callers must label results unavailable.
"""

from __future__ import annotations

import json
import platform
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable, Mapping, Sequence

from veriforge.benchmark_engine import (
    collect_environment,
    measure_execution,
)
from veriforge.config import ResourceLimits, SemanticConfiguration
from veriforge.dataset_engine import assert_no_cross_partition_leakage, load_bundle
from veriforge.exceptions import OptimizerError, VeriforgeError
from veriforge.experiment_engine import (
    baseline_by_id,
    baseline_catalog,
    compute_metrics_from_observations,
    configuration_fingerprint,
    create_experiment_run,
    make_observation,
    new_run_id,
    persist_run_with_observations,
    utc_now_iso,
)
from veriforge.models import (
    BaselineDefinition,
    BaselineId,
    CandidateDecision,
    CorrectnessPolicy,
    DatasetCase,
    DatasetPartition,
    EnvironmentRecord,
    ExpectedOutcome,
    ExperimentRun,
    MetricSummary,
    ObservationKind,
    OptimizationResult,
    RawObservation,
    TransformationCategory,
    TransformationStep,
    VerificationStatus,
)
from veriforge.optimizer_engine import (
    DEFAULT_MAX_ACCEPTED_STEPS,
    expression_from_root,
    find_first_applicable,
    optimize,
    replace_at_path,
)
from veriforge.optimizer_engine import (
    _coerce_expression,
    _resolve_rule_impls,
)
from veriforge.parser_engine import parse_expression
from veriforge.storage.database import ExperimentStore
from veriforge.verifier_engine import verify_equivalence_timed
from veriforge.version import __version__ as SOFTWARE_VERSION

EVALUATION_PROTOCOL_VERSION = "1.0.0"
EVALUATION_PROTOCOL_ID = "veriforge-phase10-held-out-evaluation"
DEFAULT_EVALUATION_SEED = 20261009
DEFAULT_DATASET_VERSION = "0.5.0"
DEFAULT_SOLVER_TIMEOUT_SECONDS = 5.0
DEFAULT_EXECUTION_ITERATIONS = 50
DEFAULT_TRIALS_PER_CASE = 1

# Baselines implemented for Phase 10 measurement. External tool remains
# not_selected (§9.3 item 5).
IMPLEMENTED_BASELINES: tuple[BaselineId, ...] = (
    BaselineId.ORIGINAL_NO_OPTIMIZATION,
    BaselineId.RULE_BASED_WITHOUT_SMT,
    BaselineId.VERIFICATION_ENABLED,
    BaselineId.TESTING_ONLY_VALIDATION,
)


class EvaluationEngineError(VeriforgeError):
    """Held-out evaluation configuration or execution failure."""


@dataclass(frozen=True, slots=True)
class EvaluationConfiguration:
    """Frozen held-out evaluation configuration (seeds, timeouts, baselines)."""

    protocol_id: str
    protocol_version: str
    dataset_version: str
    dataset_partition: DatasetPartition
    random_seed: int
    solver_timeout_seconds: float
    execution_iterations: int
    trials_per_case: int
    baseline_ids: tuple[BaselineId, ...]
    software_version: str
    execute_held_out_evaluation: bool
    notes: str | None = None
    environment: EnvironmentRecord | None = None

    def to_mapping(self) -> dict[str, Any]:
        env = self.environment
        return {
            "protocol_id": self.protocol_id,
            "protocol_version": self.protocol_version,
            "dataset_version": self.dataset_version,
            "dataset_partition": self.dataset_partition.value,
            "random_seed": self.random_seed,
            "solver_timeout_seconds": self.solver_timeout_seconds,
            "execution_iterations": self.execution_iterations,
            "trials_per_case": self.trials_per_case,
            "baseline_ids": [b.value for b in self.baseline_ids],
            "software_version": self.software_version,
            "execute_held_out_evaluation": self.execute_held_out_evaluation,
            "notes": self.notes,
            "environment": None if env is None else {
                "python_version": env.python_version,
                "platform": env.platform,
                "machine": env.machine,
                "processor": env.processor,
                "system": env.system,
                "z3_version": env.z3_version,
                "veriforge_version": env.veriforge_version,
                "cpu_count": env.cpu_count,
                "extra": dict(env.extra),
            },
            "host_platform_summary": platform.platform(),
        }


@dataclass(frozen=True, slots=True)
class BaselineCaseResult:
    """One baseline × case observation (pre-persistence)."""

    baseline_id: BaselineId
    case_id: str
    transformation_category: TransformationCategory
    expected_outcome: ExpectedOutcome
    observation: RawObservation
    solver_seconds: float | None
    original_execution_seconds: float | None
    optimized_execution_seconds: float | None
    end_to_end_verification_seconds: float | None


@dataclass(frozen=True, slots=True)
class BaselineRunResult:
    """Persisted run for one baseline on the held-out partition."""

    baseline_id: BaselineId
    run: ExperimentRun
    observations: tuple[RawObservation, ...]
    metrics: MetricSummary
    case_results: tuple[BaselineCaseResult, ...]
    dependency_status: str


@dataclass(frozen=True, slots=True)
class HeldOutEvaluationReport:
    """Aggregate Phase 10 evaluation report (may record unavailable runs)."""

    protocol_id: str
    protocol_version: str
    software_version: str
    dataset_version: str
    random_seed: int
    configuration_fingerprint: str
    created_at_utc: str
    dependency_available: bool
    dependency_blocker: str | None
    baseline_runs: tuple[BaselineRunResult, ...]
    unavailable_baselines: tuple[str, ...]
    hypothesis_status: Mapping[str, str]
    limitations: tuple[str, ...]
    is_research_conclusion_attempt: bool


def runtime_dependencies_available() -> tuple[bool, str | None]:
    """Return whether Z3 (required for SMT baselines) can be imported."""

    try:
        import z3  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        return False, f"z3 import failed: {exc}"
    return True, None


def make_evaluation_configuration(
    *,
    random_seed: int = DEFAULT_EVALUATION_SEED,
    solver_timeout_seconds: float = DEFAULT_SOLVER_TIMEOUT_SECONDS,
    execution_iterations: int = DEFAULT_EXECUTION_ITERATIONS,
    trials_per_case: int = DEFAULT_TRIALS_PER_CASE,
    baseline_ids: Sequence[BaselineId] | None = None,
    dataset_version: str = DEFAULT_DATASET_VERSION,
    notes: str | None = None,
    collect_env: bool = True,
) -> EvaluationConfiguration:
    """Build the frozen Phase 10 held-out evaluation configuration."""

    ids = tuple(baseline_ids) if baseline_ids is not None else IMPLEMENTED_BASELINES
    for baseline_id in ids:
        if baseline_id is BaselineId.EXTERNAL_TOOL:
            raise EvaluationEngineError(
                "baseline.external_tool is not_selected; omit it from evaluation"
            )
        baseline_by_id(baseline_id)
    env = collect_environment() if collect_env else None
    return EvaluationConfiguration(
        protocol_id=EVALUATION_PROTOCOL_ID,
        protocol_version=EVALUATION_PROTOCOL_VERSION,
        dataset_version=dataset_version,
        dataset_partition=DatasetPartition.HELD_OUT,
        random_seed=random_seed,
        solver_timeout_seconds=solver_timeout_seconds,
        execution_iterations=execution_iterations,
        trials_per_case=trials_per_case,
        baseline_ids=ids,
        software_version=SOFTWARE_VERSION,
        execute_held_out_evaluation=True,
        notes=notes
        or "Phase 10 held-out evaluation — development partition unused for scoring",
        environment=env,
    )


def save_evaluation_configuration(
    config: EvaluationConfiguration, path: Path
) -> Path:
    """Persist evaluation configuration JSON for reproduction."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(config.to_mapping(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def load_held_out_cases(
    *,
    root: Path | None = None,
    require_no_leakage: bool = True,
) -> tuple[DatasetCase, ...]:
    """Load held-out cases; optionally assert no cross-partition leakage."""

    held = load_bundle(DatasetPartition.HELD_OUT, root=root)
    if require_no_leakage:
        development = load_bundle(DatasetPartition.DEVELOPMENT, root=root)
        assert_no_cross_partition_leakage(development.cases, held.cases)
    return held.cases


def optimize_rules_without_smt(
    expression: str,
    config: SemanticConfiguration,
    *,
    max_accepted_steps: int = DEFAULT_MAX_ACCEPTED_STEPS,
) -> OptimizationResult:
    """Apply production identity rules without calling the SMT verifier.

    EVALUATION baseline only (``baseline.rule_based_without_smt``).
    Not a production acceptance path — production ``optimize()`` remains
    verification-guided.
    """

    if max_accepted_steps < 0:
        raise OptimizerError("max_accepted_steps must be non-negative")

    original = _coerce_expression(expression, config)
    rule_impls = _resolve_rule_impls(None)
    current = original
    trace: list[TransformationStep] = []
    blocked: set[tuple[tuple[str, ...], str]] = set()
    accepted_count = 0
    step_index = 0

    while accepted_count < max_accepted_steps:
        match = find_first_applicable(
            current.root,
            config.mode,
            rule_impls,
            blocked=blocked,
        )
        if match is None:
            break
        candidate_root = replace_at_path(current.root, match.path, match.after)
        candidate = expression_from_root(candidate_root)
        # No SMT call: accept the rewrite for this baseline's workload.
        step = TransformationStep(
            step_index=step_index,
            rule_id=match.rule.rule_id,
            rule_name=match.rule.name,
            formal_description=match.rule.formal_description,
            preconditions=match.rule.preconditions,
            matched_preconditions=match.matched_preconditions,
            supported_modes=match.rule.supported_modes,
            verification_policy=match.rule.verification_policy,
            before_source=current.source,
            after_source=candidate.source,
            decision=CandidateDecision.ACCEPTED,
            verification_result=None,
            rejection_reason=None,
        )
        trace.append(step)
        step_index += 1
        current = candidate
        accepted_count += 1
        blocked.clear()

    return OptimizationResult(
        original=original,
        accepted=current,
        config=config,
        # Marker policy: production optimize() rejects EVALUATION_ONLY; this
        # result is consumed only by the held-out baseline harness.
        policy=CorrectnessPolicy.EVALUATION_ONLY,
        trace=tuple(trace),
    )


def _semantic_for_case(
    case: DatasetCase, *, solver_timeout_seconds: float
) -> SemanticConfiguration:
    return SemanticConfiguration(
        mode=case.semantic_mode,
        bit_width=case.bit_width or 32,
        limits=ResourceLimits(solver_timeout_seconds=solver_timeout_seconds),
    )


def _time_call(fn: Any) -> tuple[float, Any]:
    start = perf_counter()
    result = fn()
    return perf_counter() - start, result


def _requires_smt(baseline_id: BaselineId) -> bool:
    return baseline_id in {
        BaselineId.VERIFICATION_ENABLED,
        BaselineId.TESTING_ONLY_VALIDATION,
    }


def run_baseline_case(
    baseline_id: BaselineId,
    case: DatasetCase,
    *,
    run_id: str,
    config: EvaluationConfiguration,
    trial_index: int = 0,
) -> BaselineCaseResult:
    """Execute one baseline on one held-out case; return a raw observation."""

    semantic = _semantic_for_case(
        case, solver_timeout_seconds=config.solver_timeout_seconds
    )
    solver_seconds: float | None = None
    e2e_seconds: float | None = None
    original_exec: float | None = None
    optimized_exec: float | None = None
    status: VerificationStatus | None = None
    detected: bool | None = None
    kind = ObservationKind.EQUIVALENCE_CHECK
    payload: dict[str, Any] = {
        "baseline_id": baseline_id.value,
        "trial_index": trial_index,
        "original_source": case.original_source,
        "candidate_source": case.candidate_source,
        "seed": config.random_seed,
        "protocol_id": config.protocol_id,
        "protocol_version": config.protocol_version,
    }
    error: str | None = None

    try:
        if case.expected_outcome is ExpectedOutcome.PARSE_REJECT:
            kind = ObservationKind.PARSE_OUTCOME
            try:
                parse_expression(case.original_source, semantic)
                payload["parse_rejected"] = False
                payload["parse_unexpected_accept"] = True
                status = VerificationStatus.INVALID_INPUT
            except Exception as exc:  # noqa: BLE001
                payload["parse_rejected"] = True
                payload["parse_error_type"] = type(exc).__name__
                payload["parse_error"] = str(exc)
                status = VerificationStatus.INVALID_INPUT
                detected = True
        elif baseline_id is BaselineId.ORIGINAL_NO_OPTIMIZATION:
            kind = ObservationKind.OPTIMIZATION_TRACE
            t_parse, expr = _time_call(
                lambda: parse_expression(case.original_source, semantic)
            )
            payload["parsing_seconds"] = t_parse
            payload["optimized_source"] = expr.source
            original_exec = measure_execution(
                case.original_source,
                semantic,
                iterations=config.execution_iterations,
            )
            optimized_exec = original_exec
            # No rewrite / no SMT — equivalence status not claimed.
            status = None
            payload["smt_invoked"] = False
        elif baseline_id is BaselineId.RULE_BASED_WITHOUT_SMT:
            kind = ObservationKind.OPTIMIZATION_TRACE
            t_opt, opt_result = _time_call(
                lambda: optimize_rules_without_smt(case.original_source, semantic)
            )
            payload["optimization_seconds"] = t_opt
            payload["optimized_source"] = opt_result.accepted.source
            payload["trace_len"] = len(opt_result.trace)
            payload["smt_invoked"] = False
            payload["post_hoc_oracle"] = False
            # No SMT: this baseline does not detect incorrect candidates.
            status = None
            detected = None
            original_exec = measure_execution(
                case.original_source,
                semantic,
                iterations=config.execution_iterations,
            )
            optimized_exec = measure_execution(
                opt_result.accepted.source,
                semantic,
                iterations=config.execution_iterations,
            )
        elif baseline_id is BaselineId.VERIFICATION_ENABLED:
            kind = ObservationKind.OPTIMIZATION_TRACE
            t_opt, opt_result = _time_call(
                lambda: optimize(case.original_source, semantic)
            )
            payload["optimization_seconds"] = t_opt
            payload["optimized_source"] = opt_result.accepted.source
            payload["trace_len"] = len(opt_result.trace)
            payload["smt_invoked"] = True
            # Prefer last verification on the trace; also time a direct check
            # against the dataset candidate when present for detection cases.
            if opt_result.trace:
                last = opt_result.trace[-1]
                if last.verification_result is not None:
                    status = last.verification_result.status
            if case.candidate_source is not None:
                timed = verify_equivalence_timed(
                    case.original_source, case.candidate_source, semantic
                )
                status = timed.result.status
                solver_seconds = timed.solver_seconds
                e2e_seconds = timed.end_to_end_seconds
                if case.expected_outcome is ExpectedOutcome.NON_EQUIVALENT:
                    detected = status is VerificationStatus.COUNTEREXAMPLE_FOUND
            elif opt_result.accepted.source != case.original_source:
                timed = verify_equivalence_timed(
                    case.original_source, opt_result.accepted.source, semantic
                )
                status = timed.result.status
                solver_seconds = timed.solver_seconds
                e2e_seconds = timed.end_to_end_seconds
            original_exec = measure_execution(
                case.original_source,
                semantic,
                iterations=config.execution_iterations,
            )
            optimized_exec = measure_execution(
                opt_result.accepted.source,
                semantic,
                iterations=config.execution_iterations,
            )
        elif baseline_id is BaselineId.TESTING_ONLY_VALIDATION:
            kind = ObservationKind.MUTATION_DETECTION
            payload["smt_invoked"] = True
            target = case.candidate_source
            if target is None:
                raise EvaluationEngineError(
                    f"testing-only baseline requires candidate_source "
                    f"for case {case.case_id}"
                )
            timed = verify_equivalence_timed(
                case.original_source, target, semantic
            )
            status = timed.result.status
            solver_seconds = timed.solver_seconds
            e2e_seconds = timed.end_to_end_seconds
            detected = status is VerificationStatus.COUNTEREXAMPLE_FOUND
            payload["accepted_into_production"] = False
            original_exec = measure_execution(
                case.original_source,
                semantic,
                iterations=config.execution_iterations,
            )
            try:
                optimized_exec = measure_execution(
                    target,
                    semantic,
                    iterations=config.execution_iterations,
                )
            except Exception as exc:  # noqa: BLE001
                payload["optimized_execution_error"] = str(exc)
        else:
            raise EvaluationEngineError(
                f"baseline not implemented for evaluation: {baseline_id}"
            )
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
        payload["error"] = error
        if status is None:
            status = VerificationStatus.VERIFICATION_ERROR

    payload["solver_seconds"] = solver_seconds
    payload["end_to_end_verification_seconds"] = e2e_seconds
    payload["original_execution_seconds"] = original_exec
    payload["optimized_execution_seconds"] = optimized_exec
    # Explicit separation for analysis consumers.
    payload["latency_separation"] = {
        "solver_latency_seconds": solver_seconds,
        "expression_execution_original_seconds": original_exec,
        "expression_execution_optimized_seconds": optimized_exec,
        "end_to_end_verification_seconds": e2e_seconds,
    }

    observation = make_observation(
        run_id=run_id,
        kind=kind,
        payload=payload,
        case_id=case.case_id,
        transformation_category=case.transformation_category,
        verification_status=status,
        detected_as_non_equivalent=detected,
        expected_outcome=case.expected_outcome,
    )
    return BaselineCaseResult(
        baseline_id=baseline_id,
        case_id=case.case_id,
        transformation_category=case.transformation_category,
        expected_outcome=case.expected_outcome,
        observation=observation,
        solver_seconds=solver_seconds,
        original_execution_seconds=original_exec,
        optimized_execution_seconds=optimized_exec,
        end_to_end_verification_seconds=e2e_seconds,
    )


def run_baseline_held_out(
    baseline_id: BaselineId,
    cases: Sequence[DatasetCase],
    config: EvaluationConfiguration,
    *,
    store: ExperimentStore | None = None,
    persist: bool = True,
    run_id: str | None = None,
) -> BaselineRunResult:
    """Run one baseline across held-out cases and persist raw observations."""

    if config.dataset_partition is not DatasetPartition.HELD_OUT:
        raise EvaluationEngineError(
            "held-out evaluation requires dataset_partition=held_out"
        )
    if not config.execute_held_out_evaluation:
        raise EvaluationEngineError(
            "execute_held_out_evaluation must be true for Phase 10"
        )

    dep_ok, dep_err = runtime_dependencies_available()
    if _requires_smt(baseline_id) and not dep_ok:
        raise EvaluationEngineError(
            f"cannot run SMT baseline {baseline_id.value}: {dep_err}"
        )

    rid = run_id or new_run_id()
    cfg_map = config.to_mapping()
    cfg_map["baseline_id"] = baseline_id.value
    run = create_experiment_run(
        configuration=cfg_map,
        baseline_id=baseline_id,
        dataset_version=config.dataset_version,
        dataset_partition=DatasetPartition.HELD_OUT,
        random_seed=config.random_seed,
        notes=config.notes,
        run_id=rid,
        protocol_version=config.protocol_version,
        software_version=config.software_version,
    )

    case_results: list[BaselineCaseResult] = []
    for case in cases:
        for trial in range(config.trials_per_case):
            case_results.append(
                run_baseline_case(
                    baseline_id,
                    case,
                    run_id=rid,
                    config=config,
                    trial_index=trial,
                )
            )

    observations = tuple(cr.observation for cr in case_results)
    metrics = compute_metrics_from_observations(rid, observations)

    if persist:
        owns = store is None
        active = store or ExperimentStore()
        try:
            persist_run_with_observations(run, observations, store=active)
        finally:
            if owns:
                active.close()

    return BaselineRunResult(
        baseline_id=baseline_id,
        run=run,
        observations=observations,
        metrics=metrics,
        case_results=tuple(case_results),
        dependency_status="available" if dep_ok else f"unavailable: {dep_err}",
    )


def _hypothesis_status_from_runs(
    runs: Sequence[BaselineRunResult],
    *,
    dependency_available: bool,
) -> dict[str, str]:
    """Map preregistered hypotheses to evidence labels (not findings)."""

    if not dependency_available or not runs:
        return {
            "H1_verification_detects_incorrect": "unavailable — no held-out SMT runs",
            "H2_verification_introduces_overhead": "unavailable — no held-out SMT runs",
            "H3_varies_by_complexity_and_category": "unavailable — no held-out SMT runs",
        }

    # H1: among NON_EQUIVALENT cases under verification-enabled / testing-only,
    # was COUNTEREXAMPLE_FOUND observed?
    detectable_total = 0
    detectable_hit = 0
    solver_times: list[float] = []
    by_category_detection: dict[str, list[bool]] = {}

    for run in runs:
        if run.baseline_id not in {
            BaselineId.VERIFICATION_ENABLED,
            BaselineId.TESTING_ONLY_VALIDATION,
        }:
            continue
        for cr in run.case_results:
            if cr.solver_seconds is not None:
                solver_times.append(cr.solver_seconds)
            if cr.expected_outcome is ExpectedOutcome.NON_EQUIVALENT:
                detectable_total += 1
                hit = bool(cr.observation.detected_as_non_equivalent)
                detectable_hit += int(hit)
                key = cr.transformation_category.value
                by_category_detection.setdefault(key, []).append(hit)

    if detectable_total == 0:
        h1 = "unresolved — no non-equivalent held-out cases exercised under SMT baselines"
    elif detectable_hit == detectable_total:
        h1 = (
            f"supported_on_this_sample — {detectable_hit}/{detectable_total} "
            "incorrect held-out cases detected (sample is small; not a general proof)"
        )
    elif detectable_hit == 0:
        h1 = (
            f"not_supported_on_this_sample — 0/{detectable_total} incorrect "
            "held-out cases detected"
        )
    else:
        h1 = (
            f"partially_supported_on_this_sample — {detectable_hit}/"
            f"{detectable_total} incorrect held-out cases detected"
        )

    if not solver_times:
        h2 = "unresolved — no solver latency samples recorded"
    elif max(solver_times) > 0.0:
        h2 = (
            "supported_on_this_sample — positive solver_seconds observed "
            f"(n={len(solver_times)}); overhead is measurable but magnitude "
            "is host-specific"
        )
    else:
        h2 = (
            "unresolved — solver_seconds recorded as zero "
            f"(n={len(solver_times)}); may reflect timer resolution"
        )

    if len(by_category_detection) >= 2:
        rates = {
            k: (sum(v) / len(v) if v else None)
            for k, v in by_category_detection.items()
        }
        h3 = (
            "inconclusive_on_this_sample — multiple categories present "
            f"({sorted(rates)}); sample sizes are too small for a stable "
            "category-effect claim"
        )
    elif by_category_detection:
        h3 = (
            "unresolved — fewer than two detectable categories observed "
            "on held-out data"
        )
    else:
        h3 = "unavailable — no stratified detection samples"

    return {
        "H1_verification_detects_incorrect": h1,
        "H2_verification_introduces_overhead": h2,
        "H3_varies_by_complexity_and_category": h3,
    }


def analyze_latency_separation(
    runs: Sequence[BaselineRunResult],
) -> dict[str, Any]:
    """Summarize solver vs expression-execution latencies separately."""

    rows: list[dict[str, Any]] = []
    for run in runs:
        solver_vals = [
            cr.solver_seconds
            for cr in run.case_results
            if cr.solver_seconds is not None
        ]
        orig_vals = [
            cr.original_execution_seconds
            for cr in run.case_results
            if cr.original_execution_seconds is not None
        ]
        opt_vals = [
            cr.optimized_execution_seconds
            for cr in run.case_results
            if cr.optimized_execution_seconds is not None
        ]

        def _median(vals: list[float]) -> float | None:
            if not vals:
                return None
            s = sorted(vals)
            mid = len(s) // 2
            if len(s) % 2:
                return s[mid]
            return (s[mid - 1] + s[mid]) / 2.0

        rows.append(
            {
                "baseline_id": run.baseline_id.value,
                "sample_count": len(run.case_results),
                "solver_latency": {
                    "n": len(solver_vals),
                    "median_seconds": _median(solver_vals),
                    "note": "solver wall time; not expression execution",
                },
                "expression_execution_original": {
                    "n": len(orig_vals),
                    "median_seconds": _median(orig_vals),
                    "note": "reference evaluator; not solver latency",
                },
                "expression_execution_optimized": {
                    "n": len(opt_vals),
                    "median_seconds": _median(opt_vals),
                    "note": "reference evaluator; not solver latency",
                },
            }
        )
    return {"by_baseline": rows}


def run_held_out_evaluation(
    config: EvaluationConfiguration | None = None,
    *,
    cases: Sequence[DatasetCase] | None = None,
    store: ExperimentStore | None = None,
    persist: bool = True,
    datasets_root: Path | None = None,
) -> HeldOutEvaluationReport:
    """Run all configured baselines on the held-out partition.

    If Z3 is unavailable, SMT baselines are recorded as unavailable and no
    fabricated measurements are written for them. Non-SMT baselines may still
    run when the parser/evaluator import path succeeds.
    """

    config = config or make_evaluation_configuration()
    if cases is None:
        cases = load_held_out_cases(root=datasets_root)

    dep_ok, dep_err = runtime_dependencies_available()
    fingerprint = configuration_fingerprint(config.to_mapping())
    limitations = [
        "Held-out sample size is small (seed partition); do not treat rates "
        "as population estimates.",
        "Exact bit-for-bit reproduction of solver timings is not guaranteed "
        "(platform / Z3 nondeterminism).",
        "Baseline external_tool remains not_selected.",
        "Rule-based-without-SMT is an evaluation harness; production optimize() "
        "remains verification-guided.",
        "Post-hoc SMT oracle on the rule-based-without-SMT baseline is used "
        "only for detection metrics, not for rewrite acceptance in that baseline.",
    ]

    baseline_runs: list[BaselineRunResult] = []
    unavailable: list[str] = []

    owns_store = store is None and persist
    active_store = store or (ExperimentStore() if persist else None)
    try:
        for baseline_id in config.baseline_ids:
            needs_smt = _requires_smt(baseline_id)
            # Non-SMT baselines still import modules that pull z3 via package
            # internals (optimizer_engine → verifier_engine). If z3 is missing,
            # mark all baselines unavailable rather than fabricating numbers.
            if not dep_ok:
                unavailable.append(
                    f"{baseline_id.value}: dependency blocker — {dep_err}"
                )
                continue
            if needs_smt and not dep_ok:
                unavailable.append(
                    f"{baseline_id.value}: SMT dependency unavailable — {dep_err}"
                )
                continue
            try:
                result = run_baseline_held_out(
                    baseline_id,
                    cases,
                    config,
                    store=active_store,
                    persist=persist and active_store is not None,
                )
                baseline_runs.append(result)
            except Exception as exc:  # noqa: BLE001
                unavailable.append(f"{baseline_id.value}: {type(exc).__name__}: {exc}")
    finally:
        if owns_store and active_store is not None:
            active_store.close()

    if not dep_ok:
        limitations = (
            f"Runtime dependency blocker on this host: {dep_err}",
            *limitations,
        )

    hyp = _hypothesis_status_from_runs(
        baseline_runs, dependency_available=dep_ok and bool(baseline_runs)
    )

    return HeldOutEvaluationReport(
        protocol_id=config.protocol_id,
        protocol_version=config.protocol_version,
        software_version=config.software_version,
        dataset_version=config.dataset_version,
        random_seed=config.random_seed,
        configuration_fingerprint=fingerprint,
        created_at_utc=utc_now_iso(),
        dependency_available=dep_ok,
        dependency_blocker=dep_err,
        baseline_runs=tuple(baseline_runs),
        unavailable_baselines=tuple(unavailable),
        hypothesis_status=hyp,
        limitations=tuple(limitations),
        is_research_conclusion_attempt=True,
    )


def report_to_mapping(report: HeldOutEvaluationReport) -> dict[str, Any]:
    """Serialize an evaluation report to a JSON-friendly mapping."""

    baseline_payload: list[dict[str, Any]] = []
    for run in report.baseline_runs:
        metrics = run.metrics
        by_class = [
            {
                "class_key": row.class_key,
                "sample_count": row.sample_count,
                "detected_count": row.detected_count,
                "undetected_count": row.undetected_count,
                "equivalent_count": row.equivalent_count,
                "counterexample_count": row.counterexample_count,
                "timeout_count": row.timeout_count,
                "unknown_count": row.unknown_count,
                "other_count": row.other_count,
                "detection_rate": row.detection_rate,
                "timeout_rate": row.timeout_rate,
                "unknown_rate": row.unknown_rate,
            }
            for row in metrics.by_class
        ]
        baseline_payload.append(
            {
                "baseline_id": run.baseline_id.value,
                "run_id": run.run.run_id,
                "configuration_fingerprint": run.run.configuration_fingerprint,
                "dependency_status": run.dependency_status,
                "observation_count": metrics.observation_count,
                "overall": {
                    "sample_count": metrics.overall.sample_count,
                    "detected_count": metrics.overall.detected_count,
                    "undetected_count": metrics.overall.undetected_count,
                    "equivalent_count": metrics.overall.equivalent_count,
                    "counterexample_count": metrics.overall.counterexample_count,
                    "timeout_count": metrics.overall.timeout_count,
                    "unknown_count": metrics.overall.unknown_count,
                    "detection_rate": metrics.overall.detection_rate,
                    "timeout_rate": metrics.overall.timeout_rate,
                    "unknown_rate": metrics.overall.unknown_rate,
                },
                "by_class": by_class,
            }
        )

    return {
        "protocol_id": report.protocol_id,
        "protocol_version": report.protocol_version,
        "software_version": report.software_version,
        "dataset_version": report.dataset_version,
        "random_seed": report.random_seed,
        "configuration_fingerprint": report.configuration_fingerprint,
        "created_at_utc": report.created_at_utc,
        "dependency_available": report.dependency_available,
        "dependency_blocker": report.dependency_blocker,
        "baseline_runs": baseline_payload,
        "unavailable_baselines": list(report.unavailable_baselines),
        "hypothesis_status": dict(report.hypothesis_status),
        "limitations": list(report.limitations),
        "latency_separation": analyze_latency_separation(report.baseline_runs),
        "is_research_conclusion_attempt": report.is_research_conclusion_attempt,
        "novelty_claim": (
            "No novelty claim. Literature review situates VERIFORGE among "
            "established translation-validation / equivalence-checking methods; "
            "confirmed novel research findings are not established."
        ),
    }


def write_evaluation_report(
    report: HeldOutEvaluationReport,
    *,
    json_path: Path,
    markdown_path: Path | None = None,
) -> tuple[Path, Path | None]:
    """Write JSON (and optional Markdown) evaluation artifacts."""

    json_path = Path(json_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    payload = report_to_mapping(report)
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    md_path: Path | None = None
    if markdown_path is not None:
        md_path = Path(markdown_path)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(_markdown_report(payload), encoding="utf-8")
    return json_path, md_path


def _markdown_report(payload: Mapping[str, Any]) -> str:
    lines = [
        "# Phase 10 held-out evaluation report",
        "",
        f"- Protocol: `{payload['protocol_id']}` "
        f"v`{payload['protocol_version']}`",
        f"- Software: `{payload['software_version']}`",
        f"- Dataset version: `{payload['dataset_version']}`",
        f"- Seed: `{payload['random_seed']}`",
        f"- Configuration fingerprint: `{payload['configuration_fingerprint']}`",
        f"- Created (UTC): `{payload['created_at_utc']}`",
        f"- Dependency available: `{payload['dependency_available']}`",
        "",
        "## Dependency blocker",
        "",
        (
            str(payload["dependency_blocker"])
            if payload["dependency_blocker"]
            else "none"
        ),
        "",
        "## Unavailable baselines",
        "",
    ]
    unavailable = payload.get("unavailable_baselines") or []
    if not unavailable:
        lines.append("none")
    else:
        for item in unavailable:
            lines.append(f"- {item}")
    lines.extend(["", "## Baseline runs", ""])
    runs = payload.get("baseline_runs") or []
    if not runs:
        lines.append("No baseline runs completed. Results: **unavailable**.")
    for run in runs:
        lines.append(f"### `{run['baseline_id']}`")
        lines.append("")
        lines.append(f"- run_id: `{run['run_id']}`")
        lines.append(f"- observation_count: {run['observation_count']}")
        overall = run["overall"]
        lines.append(
            f"- overall sample_count: {overall['sample_count']}; "
            f"detection_rate: {overall['detection_rate']}; "
            f"timeout_rate: {overall['timeout_rate']}; "
            f"unknown_rate: {overall['unknown_rate']}"
        )
        lines.append("- by class:")
        for row in run["by_class"]:
            lines.append(
                f"  - `{row['class_key']}`: n={row['sample_count']}, "
                f"detected={row['detected_count']}, "
                f"counterexample={row['counterexample_count']}, "
                f"equivalent={row['equivalent_count']}, "
                f"timeout={row['timeout_count']}, unknown={row['unknown_count']}"
            )
        lines.append("")
    lines.extend(["## Latency separation (solver vs execution)", ""])
    for row in payload.get("latency_separation", {}).get("by_baseline", []):
        lines.append(
            f"- `{row['baseline_id']}`: solver median="
            f"{row['solver_latency']['median_seconds']} "
            f"(n={row['solver_latency']['n']}); "
            f"original exec median="
            f"{row['expression_execution_original']['median_seconds']} "
            f"(n={row['expression_execution_original']['n']}); "
            f"optimized exec median="
            f"{row['expression_execution_optimized']['median_seconds']} "
            f"(n={row['expression_execution_optimized']['n']})"
        )
    lines.extend(["", "## Hypothesis status (not advance findings)", ""])
    for key, value in dict(payload.get("hypothesis_status") or {}).items():
        lines.append(f"- **{key}**: {value}")
    lines.extend(["", "## Limitations", ""])
    for item in payload.get("limitations") or []:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Novelty",
            "",
            str(payload.get("novelty_claim")),
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def baseline_catalog_phase10(
    *,
    measured: Iterable[BaselineId] = (),
) -> tuple[BaselineDefinition, ...]:
    """Return §9.3 baselines with Phase 10 measurement status applied."""

    measured_set = set(measured)
    updated: list[BaselineDefinition] = []
    for item in baseline_catalog():
        if item.baseline_id is BaselineId.EXTERNAL_TOOL:
            updated.append(item)
            continue
        if item.baseline_id in measured_set:
            updated.append(
                BaselineDefinition(
                    baseline_id=item.baseline_id,
                    name=item.name,
                    description=item.description,
                    uses_smt_verification=item.uses_smt_verification,
                    uses_production_optimizer=item.uses_production_optimizer,
                    status="measured_held_out",
                    selection_notes=item.selection_notes,
                )
            )
        else:
            updated.append(
                BaselineDefinition(
                    baseline_id=item.baseline_id,
                    name=item.name,
                    description=item.description,
                    uses_smt_verification=item.uses_smt_verification,
                    uses_production_optimizer=item.uses_production_optimizer,
                    status="defined_not_measured",
                    selection_notes=item.selection_notes,
                )
            )
    return tuple(updated)
