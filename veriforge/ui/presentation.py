"""Presentation helpers with no Streamlit dependency (Phase 8).

These functions encode research-honest labeling rules used by every page:

* UNKNOWN and TIMEOUT are never labeled equivalent.
* Scientific charts and metrics require completed-run measurements.
* Missing features surface an explicit unavailable state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from veriforge.config import SemanticConfiguration
from veriforge.models import (
    CounterexampleValidationStatus,
    MetricSummary,
    SemanticMode,
    VerificationResult,
    VerificationStatus,
)


# Statuses that must never be presented as equivalence (§6 / §14).
UNEQUIVALENT_STATUSES: frozenset[VerificationStatus] = frozenset(
    {
        VerificationStatus.UNKNOWN,
        VerificationStatus.TIMEOUT,
        VerificationStatus.COUNTEREXAMPLE_FOUND,
        VerificationStatus.UNSUPPORTED,
        VerificationStatus.INVALID_INPUT,
        VerificationStatus.TRANSLATION_ERROR,
        VerificationStatus.VERIFICATION_ERROR,
        VerificationStatus.COUNTEREXAMPLE_VALIDATION_FAILED,
        VerificationStatus.SEMANTIC_DISAGREEMENT,
    }
)

_STATUS_LABELS: dict[VerificationStatus, str] = {
    VerificationStatus.EQUIVALENT_WITHIN_MODEL: (
        "Equivalent within the encoded model and assumptions"
    ),
    VerificationStatus.COUNTEREXAMPLE_FOUND: "Counterexample found",
    VerificationStatus.UNKNOWN: "UNKNOWN — equivalence undetermined",
    VerificationStatus.TIMEOUT: "Timeout — verification incomplete",
    VerificationStatus.UNSUPPORTED: "Unsupported — no verification claim",
    VerificationStatus.INVALID_INPUT: "Invalid input — no verification claim",
    VerificationStatus.TRANSLATION_ERROR: "Translation error — verification not performed",
    VerificationStatus.VERIFICATION_ERROR: "Verification error",
    VerificationStatus.COUNTEREXAMPLE_VALIDATION_FAILED: (
        "Counterexample validation failed — no equivalence claim"
    ),
    VerificationStatus.SEMANTIC_DISAGREEMENT: (
        "Semantic disagreement — no verification claim"
    ),
}


@dataclass(frozen=True, slots=True)
class FeatureAvailability:
    """Whether a UI capability can show real data or must show unavailable."""

    available: bool
    reason: str
    feature_id: str


@dataclass(frozen=True, slots=True)
class SemanticModeDisplay:
    """Active semantic mode fields that every page must surface (§5.1 / §14)."""

    mode_label: str
    mode_value: str
    bit_width: int | None
    signedness: str
    assumptions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ResearchDashboardState:
    """Research dashboard payload derived only from completed-run measurements."""

    has_completed_runs: bool
    run_ids: tuple[str, ...]
    sample_size: int
    metrics: MetricSummary | None
    dataset_versions: tuple[str, ...]
    limitations: tuple[str, ...]
    unavailable_reason: str | None


def format_verification_status(status: VerificationStatus) -> str:
    """Return the human-readable label for a verification status.

    UNKNOWN and TIMEOUT are never mapped to an equivalence label.
    """

    if status not in _STATUS_LABELS:
        raise ValueError(f"unrecognized verification status: {status!r}")
    return _STATUS_LABELS[status]


def is_labeled_equivalent(status: VerificationStatus) -> bool:
    """Return True only for ``EQUIVALENT_WITHIN_MODEL``.

    UNKNOWN and TIMEOUT are never treated as equivalent.
    """

    return status is VerificationStatus.EQUIVALENT_WITHIN_MODEL


def assert_honest_equivalence_label(status: VerificationStatus, label: str) -> None:
    """Raise if a label incorrectly presents non-equivalence as equivalence."""

    lowered = label.lower()
    claims_equivalent = (
        "equivalent within" in lowered
        or lowered.strip() == "equivalent"
        or "proven equivalent" in lowered
    )
    if status in UNEQUIVALENT_STATUSES and claims_equivalent:
        raise ValueError(
            f"status {status.value} must not be labeled equivalent; got {label!r}"
        )
    if status is VerificationStatus.EQUIVALENT_WITHIN_MODEL and not claims_equivalent:
        # Soft check: the canonical label must include the within-model caveat.
        if "within" not in lowered:
            raise ValueError(
                "EQUIVALENT_WITHIN_MODEL label must state within-model scope"
            )


def semantic_mode_display(config: SemanticConfiguration) -> SemanticModeDisplay:
    """Build the always-visible semantic mode banner fields."""

    if config.mode is SemanticMode.MODE_A:
        return SemanticModeDisplay(
            mode_label="Mode A — mathematical integers",
            mode_value=config.mode.value,
            bit_width=None,
            signedness="not applicable (unbounded integers)",
            assumptions=assumptions_text(config),
        )
    return SemanticModeDisplay(
        mode_label="Mode B — unsigned fixed-width bit-vectors",
        mode_value=config.mode.value,
        bit_width=config.bit_width,
        signedness="unsigned (signed interpretation not used)",
        assumptions=assumptions_text(config),
    )


def assumptions_text(config: SemanticConfiguration) -> tuple[str, ...]:
    """Return explicit assumptions for the active semantic configuration."""

    shared = (
        "Supported grammar: integer literals, variables, parentheses, "
        "+, -, *, unary +/- only.",
        "Unsupported syntax fails closed; it is not silently rewritten.",
        "A solver result is a statement about the encoded formula, not a "
        "proof that the application implementation is correct.",
        "UNKNOWN and timeout are never equivalence.",
        f"Solver timeout: {config.limits.solver_timeout_seconds:g}s.",
    )
    if config.mode is SemanticMode.MODE_A:
        return (
            "Mode A: unbounded mathematical integers (Z3 Int sorts).",
            "No fixed-width overflow is implied.",
            *shared,
        )
    return (
        f"Mode B: unsigned {config.bit_width}-bit bit-vectors "
        f"(range [0, {config.max_unsigned}]).",
        "Arithmetic wraps modulo 2^w.",
        "Integer literals outside the width range are rejected (fail closed).",
        "Signed interpretation is not used for Mode B under the locked contract.",
        *shared,
    )


def feature_availability(
    feature_id: str,
    *,
    available: bool,
    reason_if_unavailable: str,
) -> FeatureAvailability:
    """Construct an availability record for a UI capability."""

    if available:
        return FeatureAvailability(
            available=True,
            reason="available",
            feature_id=feature_id,
        )
    return FeatureAvailability(
        available=False,
        reason=reason_if_unavailable,
        feature_id=feature_id,
    )


def research_dashboard_state(
    *,
    completed_run_ids: Sequence[str],
    metrics: MetricSummary | None,
    dataset_versions: Sequence[str] | None = None,
) -> ResearchDashboardState:
    """Build research-dashboard state from completed runs only.

    When no completed runs exist, charts and metrics are unavailable — never
    fabricated.
    """

    run_ids = tuple(completed_run_ids)
    limitations = (
        "Display shows only measurements from completed runs.",
        "Hypotheses in the research plan are not findings.",
        "An artificial 90/10 mix, if present, is a controlled configuration — "
        "not real-world prevalence.",
        "Held-out final evaluation as a research conclusion is not claimed here.",
    )
    if not run_ids or metrics is None:
        return ResearchDashboardState(
            has_completed_runs=False,
            run_ids=(),
            sample_size=0,
            metrics=None,
            dataset_versions=tuple(dataset_versions or ()),
            limitations=limitations,
            unavailable_reason=(
                "No completed experiment runs with stored observations are "
                "available. Scientific charts remain unavailable until real "
                "measurements exist."
            ),
        )
    return ResearchDashboardState(
        has_completed_runs=True,
        run_ids=run_ids,
        sample_size=metrics.observation_count,
        metrics=metrics,
        dataset_versions=tuple(dataset_versions or ()),
        limitations=limitations,
        unavailable_reason=None,
    )


def counterexample_display_rows(
    result: VerificationResult,
) -> tuple[Mapping[str, Any], ...] | None:
    """Return counterexample rows only when a confirmed or recorded CXE exists.

    Unconfirmed discrepancies are surfaced with their validation status; they
    are never labeled as confirmed counterexamples.
    """

    cxe = result.counterexample
    if cxe is None:
        return None
    return (
        {
            "assignment": dict(cxe.assignment),
            "original_value": cxe.original_value,
            "candidate_value": cxe.candidate_value,
            "validation_status": cxe.validation_status.value,
            "confirmed": cxe.validation_status
            is CounterexampleValidationStatus.CONFIRMED,
            "detail": cxe.detail,
        },
    )


def mutation_outcome_label(
    *,
    detected_as_non_equivalent: bool,
    status: VerificationStatus,
    artificial: bool,
) -> str:
    """Label a fuzz/mutation outcome without conflating synthetic and real defects."""

    origin = "synthetic artificial mutation" if artificial else "non-synthetic case"
    if status is VerificationStatus.TIMEOUT:
        return f"TIMEOUT — verification incomplete ({origin})"
    if status is VerificationStatus.UNKNOWN:
        return f"UNKNOWN — equivalence undetermined ({origin})"
    if detected_as_non_equivalent:
        return f"Correctly classified as non-equivalent ({origin})"
    if status is VerificationStatus.EQUIVALENT_WITHIN_MODEL:
        return (
            f"Verifier reported equivalent within model ({origin}); "
            "detection miss if the mutation was expected to differ"
        )
    return f"Outcome {status.value} ({origin})"


def chart_series_or_unavailable(
    values: Sequence[float] | None,
    *,
    feature_id: str,
) -> FeatureAvailability | tuple[float, ...]:
    """Return chart data only when real measurements exist; else unavailable."""

    if values is None or len(values) == 0:
        return feature_availability(
            feature_id,
            available=False,
            reason_if_unavailable=(
                "No completed-run measurements are available for this chart. "
                "Fabricated data is not shown."
            ),
        )
    return tuple(float(v) for v in values)


def status_badge_kind(status: VerificationStatus) -> str:
    """Map a status to a coarse UI badge kind (not a Boolean success flag)."""

    if status is VerificationStatus.EQUIVALENT_WITHIN_MODEL:
        return "equivalent_within_model"
    if status is VerificationStatus.COUNTEREXAMPLE_FOUND:
        return "counterexample"
    if status is VerificationStatus.UNKNOWN:
        return "unknown"
    if status is VerificationStatus.TIMEOUT:
        return "timeout"
    return "error_or_unsupported"
