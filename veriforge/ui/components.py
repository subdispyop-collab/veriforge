"""Reusable Streamlit widgets for VERIFORGE pages.

Thin presentation wrappers only. Domain logic stays in engines / presentation
helpers / actions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from veriforge.models import SemanticMode, VerificationStatus
from veriforge.ui.presentation import (
    FeatureAvailability,
    format_verification_status,
    is_labeled_equivalent,
    semantic_mode_display,
    status_badge_kind,
)

if TYPE_CHECKING:
    from veriforge.config import SemanticConfiguration


def _st():
    import streamlit as st

    return st


def render_semantic_banner(config: SemanticConfiguration) -> None:
    """Always show active semantic mode, width, signedness, and assumptions."""

    st = _st()
    display = semantic_mode_display(config)
    cols = st.columns(3)
    cols[0].markdown(f"**Semantic mode:** {display.mode_label}")
    if display.bit_width is not None:
        cols[1].markdown(f"**Bit width:** {display.bit_width}")
    else:
        cols[1].markdown("**Bit width:** n/a (Mode A)")
    cols[2].markdown(f"**Signedness:** {display.signedness}")
    with st.expander("Assumptions", expanded=True):
        for line in display.assumptions:
            st.markdown(f"- {line}")


def render_unavailable(feature: FeatureAvailability) -> None:
    """Show a clear unavailable state instead of a simulated feature."""

    st = _st()
    st.warning(
        f"**Unavailable:** `{feature.feature_id}` — {feature.reason}"
    )


def render_verification_status(status: VerificationStatus) -> None:
    """Render an explicit verification status without Boolean collapse."""

    st = _st()
    label = format_verification_status(status)
    kind = status_badge_kind(status)
    if is_labeled_equivalent(status):
        st.success(label)
    elif kind == "counterexample":
        st.error(label)
    elif kind in {"unknown", "timeout"}:
        st.warning(label)
    else:
        st.error(label)
    st.caption(
        "Statuses are never collapsed to a Boolean success/failure field. "
        "UNKNOWN and timeout are not equivalence."
    )


def semantic_mode_selector(
    *,
    key_prefix: str = "sem",
    default_mode: SemanticMode = SemanticMode.MODE_A,
) -> tuple[SemanticMode, int, float]:
    """Sidebar/main controls for mode, bit width, and solver timeout."""

    st = _st()
    mode_label = st.selectbox(
        "Semantic mode",
        options=["Mode A (mathematical integers)", "Mode B (unsigned bit-vectors)"],
        index=0 if default_mode is SemanticMode.MODE_A else 1,
        key=f"{key_prefix}_mode",
    )
    mode = (
        SemanticMode.MODE_A
        if mode_label.startswith("Mode A")
        else SemanticMode.MODE_B
    )
    bit_width = 32
    if mode is SemanticMode.MODE_B:
        bit_width = int(
            st.number_input(
                "Bit width",
                min_value=1,
                max_value=512,
                value=32,
                step=1,
                key=f"{key_prefix}_width",
            )
        )
        st.caption("Mode B uses unsigned interpretation; signedness is not used.")
    timeout = float(
        st.number_input(
            "Solver timeout (seconds)",
            min_value=0.1,
            max_value=120.0,
            value=5.0,
            step=0.5,
            key=f"{key_prefix}_timeout",
        )
    )
    return mode, bit_width, timeout


def page_intro(title: str, body: str) -> None:
    st = _st()
    st.header(title)
    st.markdown(body)
