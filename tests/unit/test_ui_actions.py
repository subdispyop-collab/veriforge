"""Action-layer interface tests (require z3 for engine-backed paths)."""

from __future__ import annotations

from pathlib import Path

from veriforge.config import SemanticConfiguration
from veriforge.models import SemanticMode, VerificationStatus
from veriforge.ui.actions import (
    build_semantic_configuration,
    list_baseline_options,
    load_research_metrics,
    parse_for_workbench,
    run_fuzz_lab,
    run_verification_explorer,
    run_workbench,
)
from veriforge.ui.presentation import (
    format_verification_status,
    is_labeled_equivalent,
    research_dashboard_state,
)


def test_build_semantic_configuration_modes() -> None:
    cfg_a = build_semantic_configuration(mode=SemanticMode.MODE_A)
    assert cfg_a.mode is SemanticMode.MODE_A
    cfg_b = build_semantic_configuration(
        mode=SemanticMode.MODE_B, bit_width=16, solver_timeout_seconds=2.5
    )
    assert cfg_b.bit_width == 16
    assert cfg_b.limits.solver_timeout_seconds == 2.5


def test_workbench_parse_reject_and_optimize() -> None:
    cfg = SemanticConfiguration(mode=SemanticMode.MODE_A)
    bad = parse_for_workbench("import os", cfg)
    assert bad.ok is False
    assert bad.error

    good = run_workbench("(x + 0) * 1", cfg)
    assert good.error is None
    assert good.optimization is not None
    assert good.optimization.accepted.source.replace(" ", "") in {"x", "(x)"}


def test_explorer_never_labels_unknown_timeout_as_equivalent() -> None:
    cfg = SemanticConfiguration(mode=SemanticMode.MODE_A)
    outcome = run_verification_explorer("x + 1", "x + 2", cfg)
    assert outcome.error is None
    assert outcome.timed is not None
    status = outcome.timed.result.status
    assert status is VerificationStatus.COUNTEREXAMPLE_FOUND
    assert is_labeled_equivalent(status) is False
    assert "equivalent within" not in format_verification_status(status).lower()

    eq = run_verification_explorer("x + 0", "x", cfg)
    assert eq.timed is not None
    assert eq.timed.result.status is VerificationStatus.EQUIVALENT_WITHIN_MODEL
    assert is_labeled_equivalent(eq.timed.result.status) is True


def test_fuzz_lab_marks_synthetic_and_never_accepts_production() -> None:
    cfg = SemanticConfiguration(mode=SemanticMode.MODE_A)
    outcome = run_fuzz_lab("x + 1", cfg, seed=1, max_mutations=4)
    assert outcome.error is None
    assert outcome.analyses
    for analysis in outcome.analyses:
        assert analysis.mutation.artificial is True
        assert analysis.accepted_into_production is False


def test_research_metrics_empty_store(tmp_path: Path) -> None:
    run_ids, metrics, versions = load_research_metrics(experiments_root=tmp_path)
    state = research_dashboard_state(
        completed_run_ids=run_ids, metrics=metrics, dataset_versions=versions
    )
    assert state.has_completed_runs is False
    assert state.unavailable_reason is not None


def test_baseline_catalog_exposed_to_ui() -> None:
    rows = list_baseline_options()
    assert len(rows) >= 4
    assert all("status" in row for row in rows)


def test_pages_module_declares_six_renderers() -> None:
    from veriforge.ui import pages
    from veriforge.ui.catalog import PAGE_NAMES

    assert callable(pages.render_expression_workbench)
    assert callable(pages.render_verification_explorer)
    assert callable(pages.render_fuzzing_mutation_lab)
    assert callable(pages.render_benchmark_lab)
    assert callable(pages.render_research_dashboard)
    assert callable(pages.render_audit_reproducibility)
    for name in PAGE_NAMES:
        # render_page dispatches without inventing pages
        assert name in {
            "Expression Workbench",
            "Verification Explorer",
            "Fuzzing and Mutation Lab",
            "Benchmark Lab",
            "Research Dashboard",
            "Audit and Reproducibility",
        }
