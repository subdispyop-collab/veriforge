"""Scientific visualizations for completed-run measurements only.

Never fabricates chart data. Empty series yield an unavailable state.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from veriforge.models import BenchmarkReport, ClassMetricRow, MetricSummary
from veriforge.ui.components import render_unavailable
from veriforge.ui.presentation import (
    FeatureAvailability,
    chart_series_or_unavailable,
    feature_availability,
)


def _st():
    import streamlit as st

    return st


def _plotly_available() -> bool:
    try:
        import plotly.express as px  # noqa: F401

        return True
    except ImportError:
        return False


def render_timing_distribution(
    values: Sequence[float] | None,
    *,
    title: str,
    feature_id: str,
    y_label: str = "seconds",
) -> None:
    """Histogram of real timing samples, or an unavailable notice."""

    st = _st()
    series = chart_series_or_unavailable(values, feature_id=feature_id)
    if isinstance(series, FeatureAvailability):
        render_unavailable(series)
        return
    data = list(series)
    if not _plotly_available():
        avail = feature_availability(
            feature_id,
            available=False,
            reason_if_unavailable=(
                "plotly is not installed in this environment. "
                f"{len(data)} real sample(s) exist but cannot be charted here."
            ),
        )
        render_unavailable(avail)
        st.dataframe({"seconds": data}, use_container_width=True)
        return
    import pandas as pd
    import plotly.express as px

    frame = pd.DataFrame({y_label: data})
    fig = px.histogram(frame, x=y_label, title=title)
    fig.update_layout(margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)


def render_benchmark_report_charts(report: BenchmarkReport | None) -> None:
    """Plot timing statistics from a completed benchmark report only."""

    st = _st()
    if report is None or report.measurement_count == 0:
        render_unavailable(
            feature_availability(
                "benchmark_distribution_plots",
                available=False,
                reason_if_unavailable=(
                    "No completed benchmark measurements are available. "
                    "Charts are not fabricated."
                ),
            )
        )
        return
    st.subheader("Timing medians (completed run)")
    st.caption(report.nondeterminism_disclosure)
    st.caption(report.speedup_claim_policy)
    rows = []
    for stat in report.timing:
        if stat.sample_count == 0 or stat.median_seconds is None:
            continue
        rows.append(
            {
                "quantity": stat.quantity,
                "median_seconds": stat.median_seconds,
                "stdev_seconds": stat.stdev_seconds,
                "sample_count": stat.sample_count,
            }
        )
    if not rows:
        render_unavailable(
            feature_availability(
                "benchmark_timing_medians",
                available=False,
                reason_if_unavailable=(
                    "The completed run recorded no numeric timing samples "
                    "eligible for summary charts."
                ),
            )
        )
        return
    if not _plotly_available():
        st.dataframe(rows, use_container_width=True)
        return
    import pandas as pd
    import plotly.express as px

    frame = pd.DataFrame(rows)
    fig = px.bar(
        frame,
        x="quantity",
        y="median_seconds",
        title="Median stage timings (separate quantities)",
        error_y="stdev_seconds",
    )
    fig.update_layout(xaxis_tickangle=-35, margin=dict(l=20, r=20, t=40, b=80))
    st.plotly_chart(fig, use_container_width=True)


def render_metric_category_chart(metrics: MetricSummary | None) -> None:
    """Category breakdown from stored observations only."""

    st = _st()
    if metrics is None or metrics.observation_count == 0:
        render_unavailable(
            feature_availability(
                "research_category_chart",
                available=False,
                reason_if_unavailable=(
                    "No completed-run observations are available for category "
                    "charts. Fabricated research plots are not shown."
                ),
            )
        )
        return
    rows = [_class_row_dict(row) for row in metrics.by_class]
    if not rows:
        render_unavailable(
            feature_availability(
                "research_category_chart",
                available=False,
                reason_if_unavailable="Metrics exist but have no by-class rows.",
            )
        )
        return
    st.dataframe(rows, use_container_width=True)
    if not _plotly_available():
        return
    import pandas as pd
    import plotly.express as px

    frame = pd.DataFrame(rows)
    fig = px.bar(
        frame,
        x="class_key",
        y="sample_count",
        title="Sample counts by category (completed observations)",
    )
    fig.update_layout(xaxis_tickangle=-30, margin=dict(l=20, r=20, t=40, b=80))
    st.plotly_chart(fig, use_container_width=True)


def _class_row_dict(row: ClassMetricRow) -> Mapping[str, object]:
    return {
        "class_key": row.class_key,
        "sample_count": row.sample_count,
        "detected_count": row.detected_count,
        "undetected_count": row.undetected_count,
        "equivalent_count": row.equivalent_count,
        "counterexample_count": row.counterexample_count,
        "timeout_count": row.timeout_count,
        "unknown_count": row.unknown_count,
        "detection_rate": row.detection_rate,
        "timeout_rate": row.timeout_rate,
        "unknown_rate": row.unknown_rate,
    }
