"""Unit tests for Phase 10 held-out evaluation machinery.

Requires z3-solver. On egress-blocked hosts these tests are skipped.
Protocol allow/forbid for held-out flags is also covered in
``test_experiment_engine.py`` without z3.
"""

from __future__ import annotations

from pathlib import Path

import pytest

z3 = pytest.importorskip("z3")  # noqa: F401

from veriforge.config import SemanticConfiguration
from veriforge.evaluation_engine import (
    EVALUATION_PROTOCOL_VERSION,
    EvaluationEngineError,
    baseline_catalog_phase10,
    make_evaluation_configuration,
    optimize_rules_without_smt,
    report_to_mapping,
    runtime_dependencies_available,
    run_held_out_evaluation,
    save_evaluation_configuration,
)
from veriforge.experiment_engine import create_experiment_run
from veriforge.models import (
    BaselineId,
    DatasetPartition,
    SemanticMode,
)
from veriforge.storage.database import ExperimentStore


def test_phase10_config_enables_held_out_flag() -> None:
    config = make_evaluation_configuration(collect_env=False)
    assert config.execute_held_out_evaluation is True
    assert config.dataset_partition is DatasetPartition.HELD_OUT
    assert config.protocol_version == EVALUATION_PROTOCOL_VERSION
    assert BaselineId.EXTERNAL_TOOL not in config.baseline_ids


def test_phase10_create_run_allows_held_out_execution_flag() -> None:
    config = make_evaluation_configuration(collect_env=False)
    run = create_experiment_run(
        configuration=config.to_mapping(),
        baseline_id=BaselineId.VERIFICATION_ENABLED,
        dataset_partition=DatasetPartition.HELD_OUT,
        random_seed=config.random_seed,
        protocol_version=config.protocol_version,
    )
    assert run.configuration["execute_held_out_evaluation"] is True
    assert run.dataset_partition is DatasetPartition.HELD_OUT


def test_external_tool_rejected_from_evaluation_config() -> None:
    with pytest.raises(EvaluationEngineError, match="not_selected"):
        make_evaluation_configuration(
            baseline_ids=(BaselineId.EXTERNAL_TOOL,),
            collect_env=False,
        )


def test_baseline_catalog_phase10_marks_measured() -> None:
    catalog = baseline_catalog_phase10(
        measured=(BaselineId.VERIFICATION_ENABLED,)
    )
    statuses = {b.baseline_id: b.status for b in catalog}
    assert statuses[BaselineId.VERIFICATION_ENABLED] == "measured_held_out"
    assert statuses[BaselineId.EXTERNAL_TOOL] == "not_selected"
    assert statuses[BaselineId.ORIGINAL_NO_OPTIMIZATION] == "defined_not_measured"


def test_save_evaluation_configuration(tmp_path: Path) -> None:
    config = make_evaluation_configuration(collect_env=False, random_seed=7)
    path = save_evaluation_configuration(config, tmp_path / "cfg.json")
    text = path.read_text(encoding="utf-8")
    assert "veriforge-phase10-held-out-evaluation" in text
    assert '"random_seed": 7' in text


def test_runtime_dependencies_probe_returns_tuple() -> None:
    ok, err = runtime_dependencies_available()
    assert ok is True
    assert err is None


def test_optimize_rules_without_smt_accepts_identity() -> None:
    cfg = SemanticConfiguration(mode=SemanticMode.MODE_A)
    result = optimize_rules_without_smt("x + 0", cfg)
    assert "x" in result.accepted.source.replace("(", "").replace(")", "")
    assert all(step.verification_result is None for step in result.trace)


def test_held_out_evaluation_runs(tmp_path: Path) -> None:
    config = make_evaluation_configuration(
        collect_env=True,
        trials_per_case=1,
        execution_iterations=5,
        notes="unit test held-out run",
    )
    with ExperimentStore(root=tmp_path) as store:
        report = run_held_out_evaluation(config, store=store, persist=True)
    payload = report_to_mapping(report)
    assert payload["protocol_id"] == "veriforge-phase10-held-out-evaluation"
    assert "hypothesis_status" in payload
    assert "latency_separation" in payload
    assert payload["baseline_runs"] or payload["unavailable_baselines"]
    if payload["dependency_available"]:
        assert payload["baseline_runs"]
        for run in payload["baseline_runs"]:
            assert run["overall"]["sample_count"] >= 1
            for row in run["by_class"]:
                assert "sample_count" in row
