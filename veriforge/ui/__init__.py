"""Streamlit presentation for VERIFORGE (Phase 8).

Application logic lives in the engine modules and in ``veriforge.ui.presentation``
/ ``veriforge.ui.actions``. Streamlit pages call those helpers; they do not own
parsing, optimization, verification, benchmarking, or audit persistence.
"""

from veriforge.ui.presentation import (
    FeatureAvailability,
    UNEQUIVALENT_STATUSES,
    assumptions_text,
    feature_availability,
    format_verification_status,
    is_labeled_equivalent,
    research_dashboard_state,
    semantic_mode_display,
)

__all__ = [
    "FeatureAvailability",
    "UNEQUIVALENT_STATUSES",
    "assumptions_text",
    "feature_availability",
    "format_verification_status",
    "is_labeled_equivalent",
    "research_dashboard_state",
    "semantic_mode_display",
]
