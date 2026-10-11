"""Interface honesty tests for Phase 8 presentation helpers.

These tests do not require Streamlit, plotly, or pandas. They encode the
§14 rules: UNKNOWN/timeout ≠ equivalent; unavailable features stay unavailable;
research charts require completed-run measurements.
"""

from __future__ import annotations

import pytest

from veriforge.config import SemanticConfiguration
from veriforge.models import (
    ClassMetricRow,
    Counterexample,
    CounterexampleValidationStatus,
    MetricSummary,
    SemanticMode,
    VerificationResult,
    VerificationStatus,
)
from veriforge.ui.presentation import (
    UNEQUIVALENT_STATUSES,
    assert_honest_equivalence_label,
    assumptions_text,
    chart_series_or_unavailable,
    counterexample_display_rows,
    feature_availability,
    format_verification_status,
    is_labeled_equivalent,
    mutation_outcome_label,
    research_dashboard_state,
    semantic_mode_display,
    status_badge_kind,
)


@pytest.mark.parametrize("status", list(VerificationStatus))
def test_format_covers_every_status(status: VerificationStatus) -> None:
    label = format_verification_status(status)
    assert isinstance(label, str) and label
    assert_honest_equivalence_label(status, label)


@pytest.mark.parametrize(
    "status",
    [
        VerificationStatus.UNKNOWN,
        VerificationStatus.TIMEOUT,
        VerificationStatus.COUNTEREXAMPLE_FOUND,
        VerificationStatus.UNSUPPORTED,
        VerificationStatus.INVALID_INPUT,
        VerificationStatus.TRANSLATION_ERROR,
        VerificationStatus.VERIFICATION_ERROR,
        VerificationStatus.COUNTEREXAMPLE_VALIDATION_FAILED,
        VerificationStatus.SEMANTIC_DISAGREEMENT,
    ],
)
def test_unknown_and_timeout_never_labeled_equivalent(
    status: VerificationStatus,
) -> None:
    assert status in UNEQUIVALENT_STATUSES
    assert is_labeled_equivalent(status) is False
    label = format_verification_status(status).lower()
    assert "undetermined" in label or "incomplete" in label or "counterexample" in label or "no verification" in label or "error" in label or "unsupported" in label or "invalid" in label or "translation" in label
    assert "equivalent within" not in label
    assert label.strip() != "equivalent"


def test_only_equivalent_within_model_is_labeled_equivalent() -> None:
    assert is_labeled_equivalent(VerificationStatus.EQUIVALENT_WITHIN_MODEL) is True
    label = format_verification_status(VerificationStatus.EQUIVALENT_WITHIN_MODEL)
    assert "within the encoded model" in label.lower()


def test_assert_honest_label_rejects_mislabeling() -> None:
    with pytest.raises(ValueError, match="must not be labeled equivalent"):
        assert_honest_equivalence_label(
            VerificationStatus.UNKNOWN, "Equivalent within the encoded model"
        )
    with pytest.raises(ValueError, match="must not be labeled equivalent"):
        assert_honest_equivalence_label(
            VerificationStatus.TIMEOUT, "proven equivalent"
        )


def test_semantic_banner_mode_a_and_mode_b() -> None:
    mode_a = semantic_mode_display(SemanticConfiguration(mode=SemanticMode.MODE_A))
    assert mode_a.bit_width is None
    assert "Mode A" in mode_a.mode_label
    assert any("unbounded" in a.lower() for a in mode_a.assumptions)

    mode_b = semantic_mode_display(
        SemanticConfiguration(mode=SemanticMode.MODE_B, bit_width=32)
    )
    assert mode_b.bit_width == 32
    assert "unsigned" in mode_b.signedness.lower()
    assert any("32" in a for a in mode_b.assumptions)


def test_assumptions_mention_unknown_not_equivalence() -> None:
    text = " ".join(assumptions_text(SemanticConfiguration(mode=SemanticMode.MODE_A)))
    assert "UNKNOWN" in text
    assert "never equivalence" in text.lower() or "never equivalence" in text


def test_feature_unavailable_state() -> None:
    avail = feature_availability(
        "research_charts",
        available=False,
        reason_if_unavailable="No completed runs",
    )
    assert avail.available is False
    assert "No completed runs" in avail.reason


def test_research_dashboard_unavailable_without_runs() -> None:
    state = research_dashboard_state(completed_run_ids=(), metrics=None)
    assert state.has_completed_runs is False
    assert state.sample_size == 0
    assert state.metrics is None
    assert state.unavailable_reason is not None
    assert "fabricated" in state.unavailable_reason.lower() or "unavailable" in state.unavailable_reason.lower()


def test_research_dashboard_uses_completed_metrics_only() -> None:
    overall = ClassMetricRow(
        class_key="overall",
        sample_count=4,
        detected_count=2,
        undetected_count=1,
        equivalent_count=1,
        counterexample_count=2,
        timeout_count=0,
        unknown_count=1,
        other_count=0,
        detection_rate=0.5,
        timeout_rate=0.0,
        unknown_rate=0.25,
    )
    metrics = MetricSummary(
        run_id="run-1",
        observation_count=4,
        by_class=(overall,),
        overall=overall,
    )
    state = research_dashboard_state(
        completed_run_ids=["run-1"],
        metrics=metrics,
        dataset_versions=["0.5.0"],
    )
    assert state.has_completed_runs is True
    assert state.sample_size == 4
    assert state.dataset_versions == ("0.5.0",)
    assert state.unavailable_reason is None


def test_chart_series_refuses_empty() -> None:
    missing = chart_series_or_unavailable([], feature_id="solver_hist")
    assert getattr(missing, "available") is False
    present = chart_series_or_unavailable([0.1, 0.2], feature_id="solver_hist")
    assert present == (0.1, 0.2)


def test_counterexample_rows_mark_confirmation() -> None:
    result = VerificationResult(
        status=VerificationStatus.COUNTEREXAMPLE_FOUND,
        mode=SemanticMode.MODE_A,
        bit_width=None,
        timeout_seconds=5.0,
        counterexample=Counterexample(
            assignment={"x": 1},
            original_value=2,
            candidate_value=3,
            validation_status=CounterexampleValidationStatus.CONFIRMED,
        ),
    )
    rows = counterexample_display_rows(result)
    assert rows is not None
    assert rows[0]["confirmed"] is True

    empty = VerificationResult(
        status=VerificationStatus.UNKNOWN,
        mode=SemanticMode.MODE_A,
        bit_width=None,
        timeout_seconds=5.0,
    )
    assert counterexample_display_rows(empty) is None


def test_mutation_labels_distinguish_synthetic_and_timeout() -> None:
    timeout_label = mutation_outcome_label(
        detected_as_non_equivalent=False,
        status=VerificationStatus.TIMEOUT,
        artificial=True,
    )
    assert "TIMEOUT" in timeout_label
    assert "synthetic" in timeout_label.lower()
    assert "equivalent within" not in timeout_label.lower()

    unknown_label = mutation_outcome_label(
        detected_as_non_equivalent=False,
        status=VerificationStatus.UNKNOWN,
        artificial=True,
    )
    assert "UNKNOWN" in unknown_label


def test_status_badge_kinds_distinct() -> None:
    assert status_badge_kind(VerificationStatus.EQUIVALENT_WITHIN_MODEL) == (
        "equivalent_within_model"
    )
    assert status_badge_kind(VerificationStatus.UNKNOWN) == "unknown"
    assert status_badge_kind(VerificationStatus.TIMEOUT) == "timeout"


def test_page_names_cover_six_specified_pages() -> None:
    from veriforge.ui.catalog import PAGE_NAMES

    assert len(PAGE_NAMES) == 6
    assert "Expression Workbench" in PAGE_NAMES
    assert "Verification Explorer" in PAGE_NAMES
    assert "Fuzzing and Mutation Lab" in PAGE_NAMES
    assert "Benchmark Lab" in PAGE_NAMES
    assert "Research Dashboard" in PAGE_NAMES
    assert "Audit and Reproducibility" in PAGE_NAMES
