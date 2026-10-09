"""Streamlit entry point for VERIFORGE (Phase 8).

Run:

    streamlit run veriforge/app.py --server.port 8513 --server.address 127.0.0.1

Application logic remains in engine modules and ``veriforge.ui.actions`` /
``veriforge.ui.presentation``. This file only wires navigation and page
rendering.
"""

from __future__ import annotations

from veriforge.ui.catalog import PAGE_NAMES
from veriforge.ui.pages import render_page
from veriforge.version import __version__


def main() -> None:
    import streamlit as st

    st.set_page_config(
        page_title="VERIFORGE",
        page_icon="VF",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.sidebar.title("VERIFORGE")
    st.sidebar.caption(f"v{__version__} — research prototype")
    st.sidebar.markdown(
        "Formal-verification-guided arithmetic expression research platform. "
        "Interpretability over decoration."
    )
    page = st.sidebar.radio("Pages", options=list(PAGE_NAMES), index=0)
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "Active semantic mode, bit width (Mode B), and assumptions appear on "
        "each analysis page. UNKNOWN and timeout are never labeled equivalent. "
        "Charts show only completed-run measurements."
    )
    render_page(page)


if __name__ == "__main__":
    main()
