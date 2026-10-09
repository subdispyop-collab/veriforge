"""Unit tests for Phase 5 dataset engine and leakage controls."""

from __future__ import annotations

from pathlib import Path

import pytest

from veriforge.config import SemanticConfiguration
from veriforge.dataset_engine import (
    DatasetError,
    assert_no_cross_partition_leakage,
    build_case,
    find_cross_partition_leaks,
    load_all_partitions,
    load_bundle,
    near_duplicate_key,
    normalize_expression_text,
    write_bundle,
)
from veriforge.models import (
    ARTIFICIAL_90_10_MIX,
    DatasetBundle,
    DatasetMetadata,
    DatasetPartition,
    ExpectedOutcome,
    SemanticMode,
    TransformationCategory,
)


def mode_a() -> SemanticConfiguration:
    return SemanticConfiguration(mode=SemanticMode.MODE_A)


def test_normalize_collapses_whitespace() -> None:
    assert normalize_expression_text("  x  +   0 ") == "x + 0"


def test_near_duplicate_key_stable() -> None:
    k1 = near_duplicate_key(
        "x + 0",
        "x",
        TransformationCategory.IDENTITY_PRESERVING,
        SemanticMode.MODE_A,
        None,
    )
    k2 = near_duplicate_key(
        "x  +  0",
        "x",
        TransformationCategory.IDENTITY_PRESERVING,
        SemanticMode.MODE_A,
        None,
    )
    assert k1 == k2


def test_cross_partition_leak_detected(tmp_path: Path) -> None:
    a = mode_a()
    shared = build_case(
        case_id="a",
        original_source="x + 0",
        candidate_source="x",
        config=a,
        transformation_category=TransformationCategory.IDENTITY_PRESERVING,
        expected_outcome=ExpectedOutcome.EQUIVALENT,
        inclusion_reason="test",
    )
    twin = build_case(
        case_id="b",
        original_source="x  + 0",
        candidate_source="x",
        config=a,
        transformation_category=TransformationCategory.IDENTITY_PRESERVING,
        expected_outcome=ExpectedOutcome.EQUIVALENT,
        inclusion_reason="test",
    )
    leaks = find_cross_partition_leaks([shared], [twin])
    assert leaks
    with pytest.raises(DatasetError, match="near-duplicate leakage"):
        assert_no_cross_partition_leakage([shared], [twin])


def test_write_and_load_roundtrip(tmp_path: Path) -> None:
    a = mode_a()
    case = build_case(
        case_id="c1",
        original_source="y * 1",
        candidate_source="y",
        config=a,
        transformation_category=TransformationCategory.IDENTITY_PRESERVING,
        expected_outcome=ExpectedOutcome.EQUIVALENT,
        inclusion_reason="roundtrip",
    )
    meta = DatasetMetadata(
        dataset_version="test-0",
        generation_procedure="unit test",
        semantic_model="mode_a",
        random_seed=1,
        partition=DatasetPartition.DEVELOPMENT,
        case_count=1,
        created_at_utc="2026-10-09T00:00:00Z",
        description="unit",
    )
    write_bundle(DatasetBundle(metadata=meta, cases=(case,)), root=tmp_path)
    loaded = load_bundle(DatasetPartition.DEVELOPMENT, root=tmp_path)
    assert loaded.metadata.case_count == 1
    assert loaded.cases[0].case_id == "c1"
    assert loaded.cases[0].near_duplicate_key


def test_controlled_mix_requires_label() -> None:
    with pytest.raises(ValueError, match="controlled_mix"):
        DatasetMetadata(
            dataset_version="t",
            generation_procedure="g",
            semantic_model="m",
            random_seed=None,
            partition=DatasetPartition.DEVELOPMENT,
            case_count=0,
            created_at_utc="2026-10-09T00:00:00Z",
            description="d",
            controlled_mix=True,
            controlled_mix_label=None,
        )


def test_artificial_90_10_not_prevalence() -> None:
    mix = ARTIFICIAL_90_10_MIX
    assert mix.correct_fraction == 0.9
    assert mix.incorrect_fraction == 0.1
    assert "not" in mix.label.lower()
    assert "prevalence" in mix.label.lower()


def test_repo_seed_datasets_have_no_leakage() -> None:
    """Integration check against the committed seed partitions."""

    root = Path(__file__).resolve().parents[2] / "datasets"
    bundles = load_all_partitions(root=root)
    assert bundles[DatasetPartition.DEVELOPMENT].metadata.dataset_version == "0.5.0"
    assert bundles[DatasetPartition.HELD_OUT].metadata.partition is DatasetPartition.HELD_OUT
    assert bundles[DatasetPartition.DEVELOPMENT].metadata.controlled_mix is True
    assert "real-world" in (
        bundles[DatasetPartition.DEVELOPMENT].metadata.controlled_mix_label or ""
    ).lower()
    # Held-out must remain unevaluated; metadata should not claim results.
    assert bundles[DatasetPartition.HELD_OUT].metadata.controlled_mix is False
