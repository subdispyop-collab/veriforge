"""Unit tests for experiment identifiers, persistence, and metric calculations."""

from __future__ import annotations

from pathlib import Path

import pytest

from veriforge.experiment_engine import (
    ExperimentError,
    PROTOCOL_VERSION,
    artificial_90_10_configuration,
    baseline_catalog,
    compute_metrics_for_stored_run,
    compute_metrics_from_observations,
    configuration_fingerprint,
    create_experiment_run,
    make_observation,
    persist_run_with_observations,
)
from veriforge.models import (
    BaselineId,
    DatasetPartition,
    ExpectedOutcome,
    ObservationKind,
    SemanticMode,
    TransformationCategory,
    VerificationStatus,
)
from veriforge.storage import ExperimentStore


def test_configuration_fingerprint_stable() -> None:
    a = configuration_fingerprint({"seed": 1, "mode": "a"})
    b = configuration_fingerprint({"mode": "a", "seed": 1})
    c = configuration_fingerprint({"seed": 2, "mode": "a"})
    assert a == b
    assert a != c
    assert len(a) == 64


def test_create_run_assigns_id_and_fingerprint() -> None:
    run = create_experiment_run(
        configuration={"trial": 1, "timeout_seconds": 5.0},
        baseline_id=BaselineId.VERIFICATION_ENABLED,
        dataset_version="0.5.0",
        dataset_partition=DatasetPartition.DEVELOPMENT,
        random_seed=20261009,
        semantic_mode=SemanticMode.MODE_A,
    )
    assert run.run_id
    assert run.protocol_version == PROTOCOL_VERSION
    assert run.configuration_fingerprint == configuration_fingerprint(
        dict(run.configuration)
    )
    assert run.configuration["protocol_id"]


def test_phase5_forbids_held_out_evaluation_flag() -> None:
    with pytest.raises(ExperimentError, match="held-out"):
        create_experiment_run(
            configuration={"execute_held_out_evaluation": True},
            dataset_partition=DatasetPartition.HELD_OUT,
        )


def test_baselines_defined_not_measured() -> None:
    catalog = baseline_catalog()
    assert len(catalog) == 5
    ids = {b.baseline_id for b in catalog}
    assert BaselineId.EXTERNAL_TOOL in ids
    external = next(b for b in catalog if b.baseline_id is BaselineId.EXTERNAL_TOOL)
    assert external.status == "not_selected"
    for b in catalog:
        if b.baseline_id is not BaselineId.EXTERNAL_TOOL:
            assert b.status == "defined_not_measured"


def test_artificial_90_10_config_labeled() -> None:
    cfg = artificial_90_10_configuration()
    assert cfg["controlled_mix"] is True
    assert cfg["correct_fraction"] == 0.9
    assert cfg["incorrect_fraction"] == 0.1
    assert cfg["not_real_world_prevalence"] is True


def test_persist_and_reload_observations(tmp_path: Path) -> None:
    run = create_experiment_run(
        configuration={"fixture": "persist"},
        dataset_partition=DatasetPartition.DEVELOPMENT,
        notes="phase5 persistence fixture",
    )
    obs = make_observation(
        run_id=run.run_id,
        kind=ObservationKind.MUTATION_DETECTION,
        case_id="dev-incorrect-001",
        transformation_category=TransformationCategory.INCORRECT_REWRITE,
        verification_status=VerificationStatus.COUNTEREXAMPLE_FOUND,
        detected_as_non_equivalent=True,
        expected_outcome=ExpectedOutcome.NON_EQUIVALENT,
        payload={"note": "fixture"},
    )
    store = persist_run_with_observations(run, [obs], root=tmp_path)
    try:
        loaded = store.get_run(run.run_id)
        assert loaded is not None
        assert loaded.configuration_fingerprint == run.configuration_fingerprint
        observations = store.load_observations(run.run_id)
        assert len(observations) == 1
        assert observations[0].detected_as_non_equivalent is True
    finally:
        store.close()


def test_metrics_known_cases_by_class(tmp_path: Path) -> None:
    """Validate metric calculations against known detection counts.

    Fixture (not a research finding):
    - class incorrect_rewrite: 2 detectable, both detected → rate 1.0
    - class artificial_mutation: 2 detectable, 1 detected → rate 0.5
    - overall detectable 4, detected 3 → rate 0.75
    - one timeout among 5 samples → timeout_rate 0.2
    """

    run = create_experiment_run(
        configuration={"fixture": "metrics-known"},
        dataset_partition=DatasetPartition.DEVELOPMENT,
        notes="metric validation fixture — not experimental results",
    )
    observations = [
        make_observation(
            run_id=run.run_id,
            kind=ObservationKind.MUTATION_DETECTION,
            case_id="k1",
            transformation_category=TransformationCategory.INCORRECT_REWRITE,
            verification_status=VerificationStatus.COUNTEREXAMPLE_FOUND,
            detected_as_non_equivalent=True,
            expected_outcome=ExpectedOutcome.NON_EQUIVALENT,
            payload={},
        ),
        make_observation(
            run_id=run.run_id,
            kind=ObservationKind.MUTATION_DETECTION,
            case_id="k2",
            transformation_category=TransformationCategory.INCORRECT_REWRITE,
            verification_status=VerificationStatus.COUNTEREXAMPLE_FOUND,
            detected_as_non_equivalent=True,
            expected_outcome=ExpectedOutcome.NON_EQUIVALENT,
            payload={},
        ),
        make_observation(
            run_id=run.run_id,
            kind=ObservationKind.MUTATION_DETECTION,
            case_id="k3",
            transformation_category=TransformationCategory.ARTIFICIAL_MUTATION,
            verification_status=VerificationStatus.COUNTEREXAMPLE_FOUND,
            detected_as_non_equivalent=True,
            expected_outcome=ExpectedOutcome.NON_EQUIVALENT,
            payload={},
        ),
        make_observation(
            run_id=run.run_id,
            kind=ObservationKind.MUTATION_DETECTION,
            case_id="k4",
            transformation_category=TransformationCategory.ARTIFICIAL_MUTATION,
            verification_status=VerificationStatus.EQUIVALENT_WITHIN_MODEL,
            detected_as_non_equivalent=False,
            expected_outcome=ExpectedOutcome.NON_EQUIVALENT,
            payload={},
        ),
        make_observation(
            run_id=run.run_id,
            kind=ObservationKind.EQUIVALENCE_CHECK,
            case_id="k5",
            transformation_category=TransformationCategory.DIFFICULT_SOLVER,
            verification_status=VerificationStatus.TIMEOUT,
            detected_as_non_equivalent=None,
            expected_outcome=ExpectedOutcome.UNKNOWN_EXPECTED,
            payload={},
        ),
    ]
    summary = compute_metrics_from_observations(run.run_id, observations)
    assert summary.observation_count == 5
    assert summary.overall.detection_rate == pytest.approx(0.75)
    assert summary.overall.timeout_rate == pytest.approx(0.2)
    by = {row.class_key: row for row in summary.by_class}
    assert by["incorrect_rewrite"].detection_rate == pytest.approx(1.0)
    assert by["artificial_mutation"].detection_rate == pytest.approx(0.5)
    assert by["difficult_solver"].timeout_count == 1

    store = persist_run_with_observations(run, observations, root=tmp_path)
    try:
        reloaded = compute_metrics_for_stored_run(run.run_id, store=store)
        assert reloaded.overall.detection_rate == pytest.approx(0.75)
        assert reloaded.computed_from == "raw_observations"
    finally:
        store.close()


def test_sqlite_store_lists_runs(tmp_path: Path) -> None:
    store = ExperimentStore(root=tmp_path)
    try:
        run = create_experiment_run(configuration={"n": 1})
        store.save_run(run)
        assert len(store.list_runs()) == 1
    finally:
        store.close()
