"""Experiment identifiers, configuration fingerprints, and metric calculations.

Phase 5 freezes the research protocol surface and provides persistence hooks.
It does not run held-out evaluation and does not implement the Phase 6
benchmark timing engine.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

from veriforge.exceptions import VeriforgeError
from veriforge.version import __version__ as SOFTWARE_VERSION
from veriforge.models import (
    ARTIFICIAL_90_10_MIX,
    BaselineDefinition,
    BaselineId,
    ClassMetricRow,
    ControlledMixConfiguration,
    DatasetPartition,
    ExpectedOutcome,
    ExperimentRun,
    MetricSummary,
    ObservationKind,
    RawObservation,
    SemanticMode,
    TransformationCategory,
    VerificationStatus,
)
from veriforge.storage.database import ExperimentStore

PROTOCOL_VERSION = "0.5.0"
PROTOCOL_ID = "veriforge-phase5-research-protocol"


class ExperimentError(VeriforgeError):
    """Experiment configuration or metric calculation failure."""


def utc_now_iso() -> str:
    """Return an ISO-8601 UTC timestamp with Z suffix."""

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_run_id() -> str:
    """Allocate a unique experiment run identifier."""

    return str(uuid.uuid4())


def configuration_fingerprint(configuration: Mapping[str, Any]) -> str:
    """Return a stable SHA-256 fingerprint of a configuration mapping.

    Keys are sorted; values are JSON-serialized with sorted keys so that
    equivalent configurations share a fingerprint.
    """

    payload = json.dumps(configuration, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def baseline_catalog() -> tuple[BaselineDefinition, ...]:
    """Documented baselines from §9.3.

    Status strings are catalog defaults. Phase 10 measurement status is
    recorded on evaluation reports and via
    ``veriforge.evaluation_engine.baseline_catalog_phase10``.
    """

    return (
        BaselineDefinition(
            baseline_id=BaselineId.ORIGINAL_NO_OPTIMIZATION,
            name="Original expression without optimization",
            description=(
                "Evaluate the original expression only; no rewrite candidates."
            ),
            uses_smt_verification=False,
            uses_production_optimizer=False,
            status="defined_not_measured",
        ),
        BaselineDefinition(
            baseline_id=BaselineId.RULE_BASED_WITHOUT_SMT,
            name="Rule-based optimizer without SMT verification",
            description=(
                "Apply production identity rules without calling the verifier. "
                "Differences from the verification-enabled baseline must be "
                "documented when measured (semantics and workload must match). "
                "Implemented as an evaluation harness only; production "
                "optimize() remains verification-guided."
            ),
            uses_smt_verification=False,
            uses_production_optimizer=True,
            status="defined_not_measured",
        ),
        BaselineDefinition(
            baseline_id=BaselineId.VERIFICATION_ENABLED,
            name="Verification-enabled optimizer",
            description=(
                "Default CorrectnessPolicy.VERIFICATION_GUIDED path: accept "
                "only on EQUIVALENT_WITHIN_MODEL."
            ),
            uses_smt_verification=True,
            uses_production_optimizer=True,
            status="defined_not_measured",
        ),
        BaselineDefinition(
            baseline_id=BaselineId.TESTING_ONLY_VALIDATION,
            name="Testing-only candidate validation",
            description=(
                "EVALUATION_ONLY harness checks deliberately incorrect "
                "(or dataset-provided) candidates via SMT; never accepts "
                "into production."
            ),
            uses_smt_verification=True,
            uses_production_optimizer=False,
            status="defined_not_measured",
        ),
        BaselineDefinition(
            baseline_id=BaselineId.EXTERNAL_TOOL,
            name="Existing relevant tool or method",
            description=(
                "Optional external comparison when a meaningful, fair "
                "comparison can be implemented. No tool is selected."
            ),
            uses_smt_verification=False,
            uses_production_optimizer=False,
            status="not_selected",
            selection_notes=(
                "No external tool selected as of Phase 10 "
                "(Alive/Alive2/CompCert not integrated as a fair "
                "same-workload baseline)."
            ),
        ),
    )


def baseline_by_id(baseline_id: BaselineId) -> BaselineDefinition:
    for item in baseline_catalog():
        if item.baseline_id is baseline_id:
            return item
    raise ExperimentError(f"unknown baseline_id: {baseline_id}")


def create_experiment_run(
    *,
    configuration: Mapping[str, Any],
    baseline_id: BaselineId | None = None,
    dataset_version: str | None = None,
    dataset_partition: DatasetPartition | None = None,
    random_seed: int | None = None,
    semantic_mode: SemanticMode | None = None,
    bit_width: int | None = None,
    notes: str | None = None,
    run_id: str | None = None,
    protocol_version: str = PROTOCOL_VERSION,
    software_version: str = SOFTWARE_VERSION,
    created_at_utc: str | None = None,
) -> ExperimentRun:
    """Create an ExperimentRun with id and configuration fingerprint.

    Creating a run does not execute evaluation. Held-out evaluation is
    forbidden in Phase 5.
    """

    if dataset_partition is DatasetPartition.HELD_OUT:
        # Phase 5 protocol forbids executing held-out evaluation. Phase 10+
        # evaluation protocols may set execute_held_out_evaluation=True.
        if bool(configuration.get("execute_held_out_evaluation")):
            proto = str(
                configuration.get("protocol_version") or protocol_version
            )
            phase5_frozen = proto == PROTOCOL_VERSION
            if phase5_frozen:
                raise ExperimentError(
                    "Phase 5 forbids executing held-out evaluation "
                    "(execute_held_out_evaluation must not be true)"
                )

    cfg = dict(configuration)
    cfg.setdefault("protocol_id", PROTOCOL_ID)
    cfg.setdefault("protocol_version", protocol_version)
    fingerprint = configuration_fingerprint(cfg)
    return ExperimentRun(
        run_id=run_id or new_run_id(),
        created_at_utc=created_at_utc or utc_now_iso(),
        protocol_version=protocol_version,
        software_version=software_version,
        configuration_fingerprint=fingerprint,
        baseline_id=baseline_id,
        dataset_version=dataset_version,
        dataset_partition=dataset_partition,
        random_seed=random_seed,
        semantic_mode=semantic_mode,
        bit_width=bit_width,
        configuration=cfg,
        notes=notes,
    )


def new_observation_id() -> str:
    return str(uuid.uuid4())


def make_observation(
    *,
    run_id: str,
    kind: ObservationKind,
    payload: Mapping[str, Any],
    case_id: str | None = None,
    transformation_category: TransformationCategory | None = None,
    verification_status: VerificationStatus | None = None,
    detected_as_non_equivalent: bool | None = None,
    expected_outcome: ExpectedOutcome | None = None,
    observation_id: str | None = None,
    recorded_at_utc: str | None = None,
) -> RawObservation:
    """Build one raw observation record (not yet persisted)."""

    return RawObservation(
        observation_id=observation_id or new_observation_id(),
        run_id=run_id,
        case_id=case_id,
        kind=kind,
        transformation_category=transformation_category,
        verification_status=verification_status,
        detected_as_non_equivalent=detected_as_non_equivalent,
        expected_outcome=expected_outcome,
        payload=dict(payload),
        recorded_at_utc=recorded_at_utc or utc_now_iso(),
    )


def persist_run_with_observations(
    run: ExperimentRun,
    observations: Sequence[RawObservation],
    *,
    store: ExperimentStore | None = None,
    root: Any = None,
) -> ExperimentStore:
    """Save a run and its raw observations. Returns the store used."""

    owns = store is None
    store = store or ExperimentStore(root=root)
    store.save_run(run)
    for obs in observations:
        if obs.run_id != run.run_id:
            raise ExperimentError(
                f"observation.run_id={obs.run_id} != run.run_id={run.run_id}"
            )
        store.save_observation(obs)
    if owns:
        # Caller may continue using the returned store; do not auto-close.
        pass
    return store


def _empty_counters() -> dict[str, int]:
    return {
        "sample_count": 0,
        "detected_count": 0,
        "undetected_count": 0,
        "equivalent_count": 0,
        "counterexample_count": 0,
        "timeout_count": 0,
        "unknown_count": 0,
        "other_count": 0,
        "detectable_total": 0,
    }


def _accumulate(counters: dict[str, int], obs: RawObservation) -> None:
    counters["sample_count"] += 1
    status = obs.verification_status
    if status is VerificationStatus.EQUIVALENT_WITHIN_MODEL:
        counters["equivalent_count"] += 1
    elif status is VerificationStatus.COUNTEREXAMPLE_FOUND:
        counters["counterexample_count"] += 1
    elif status is VerificationStatus.TIMEOUT:
        counters["timeout_count"] += 1
    elif status is VerificationStatus.UNKNOWN:
        counters["unknown_count"] += 1
    elif status is not None:
        counters["other_count"] += 1

    # Detection metrics apply when the observation records detection intent
    # (incorrect candidates / mutation detection) or expected non-equivalence.
    is_detection_case = (
        obs.detected_as_non_equivalent is not None
        or obs.expected_outcome is ExpectedOutcome.NON_EQUIVALENT
        or obs.kind is ObservationKind.MUTATION_DETECTION
    )
    if is_detection_case:
        counters["detectable_total"] += 1
        detected = obs.detected_as_non_equivalent
        if detected is None:
            detected = status is VerificationStatus.COUNTEREXAMPLE_FOUND
        if detected:
            counters["detected_count"] += 1
        else:
            counters["undetected_count"] += 1


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _row_from_counters(class_key: str, counters: Mapping[str, int]) -> ClassMetricRow:
    sample = counters["sample_count"]
    detectable = counters["detectable_total"]
    return ClassMetricRow(
        class_key=class_key,
        sample_count=sample,
        detected_count=counters["detected_count"],
        undetected_count=counters["undetected_count"],
        equivalent_count=counters["equivalent_count"],
        counterexample_count=counters["counterexample_count"],
        timeout_count=counters["timeout_count"],
        unknown_count=counters["unknown_count"],
        other_count=counters["other_count"],
        detection_rate=_rate(counters["detected_count"], detectable),
        timeout_rate=_rate(counters["timeout_count"], sample),
        unknown_rate=_rate(counters["unknown_count"], sample),
    )


def compute_metrics_from_observations(
    run_id: str,
    observations: Iterable[RawObservation],
    *,
    class_key_fn: Any = None,
) -> MetricSummary:
    """Compute aggregate and by-class metrics from stored raw observations.

    Default class key is ``transformation_category`` (or ``unclassified``).
    Report by class, not only as one aggregate accuracy number (§9.4).
    """

    if class_key_fn is None:

        def class_key_fn(obs: RawObservation) -> str:
            if obs.transformation_category is not None:
                return obs.transformation_category.value
            return "unclassified"

    overall = _empty_counters()
    by_class: dict[str, dict[str, int]] = {}
    count = 0
    for obs in observations:
        if obs.run_id != run_id:
            raise ExperimentError(
                f"observation.run_id={obs.run_id} does not match run_id={run_id}"
            )
        count += 1
        _accumulate(overall, obs)
        key = str(class_key_fn(obs))
        bucket = by_class.setdefault(key, _empty_counters())
        _accumulate(bucket, obs)

    rows = tuple(
        _row_from_counters(key, by_class[key]) for key in sorted(by_class)
    )
    return MetricSummary(
        run_id=run_id,
        observation_count=count,
        by_class=rows,
        overall=_row_from_counters("overall", overall),
        computed_from="raw_observations",
    )


def compute_metrics_for_stored_run(
    run_id: str, *, store: ExperimentStore
) -> MetricSummary:
    """Load raw observations for a run and compute metrics."""

    observations = store.load_observations(run_id)
    return compute_metrics_from_observations(run_id, observations)


def artificial_90_10_configuration() -> dict[str, Any]:
    """Return the controlled 90/10 mix configuration (§9.4).

    Explicitly labeled as not real-world prevalence.
    """

    mix: ControlledMixConfiguration = ARTIFICIAL_90_10_MIX
    return {
        "controlled_mix": True,
        "correct_fraction": mix.correct_fraction,
        "incorrect_fraction": mix.incorrect_fraction,
        "label": mix.label,
        "not_real_world_prevalence": True,
    }
