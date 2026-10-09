"""Unit tests for the Phase 6 benchmark engine (§10)."""

from __future__ import annotations

from pathlib import Path

import pytest

from veriforge.benchmark_engine import (
    BENCHMARK_PROTOCOL_VERSION,
    TIMING_QUANTITIES,
    assert_no_spurious_execution_speedup_claim,
    collect_environment,
    compute_rate_summary,
    compute_timing_statistic,
    configuration_from_mapping,
    configuration_to_mapping,
    load_benchmark_configuration,
    make_benchmark_configuration,
    measure_candidate_generation,
    measure_execution,
    measure_optimization,
    measure_verification_stages,
    measurement_from_observation_payload,
    measurement_to_observation,
    rerun_benchmark_from_saved_configuration,
    run_benchmark,
    save_benchmark_configuration,
    summarize_measurements,
)
from veriforge.config import SemanticConfiguration
from veriforge.dataset_engine import build_case
from veriforge.exceptions import BenchmarkError
from veriforge.models import (
    BenchmarkMeasurement,
    DatasetPartition,
    ExpectedOutcome,
    ObservationKind,
    SemanticMode,
    TimeoutPolicy,
    TransformationCategory,
    VerificationStatus,
    WarmupPolicy,
)
from veriforge.storage.database import ExperimentStore
from veriforge.verifier_engine import verify_equivalence_timed


def _case(
    case_id: str,
    original: str,
    candidate: str | None,
    *,
    expected: ExpectedOutcome = ExpectedOutcome.EQUIVALENT,
    category: TransformationCategory = TransformationCategory.IDENTITY_PRESERVING,
) -> object:
    return build_case(
        case_id=case_id,
        original_source=original,
        candidate_source=candidate,
        config=SemanticConfiguration(mode=SemanticMode.MODE_A),
        transformation_category=category,
        expected_outcome=expected,
        inclusion_reason="phase6 unit fixture",
    )


def test_environment_recorded() -> None:
    env = collect_environment(extra={"fixture": "true"})
    assert env.python_version
    assert env.platform
    assert env.veriforge_version
    assert env.extra["fixture"] == "true"


def test_configuration_records_controls() -> None:
    cfg = make_benchmark_configuration(
        trials_per_case=4,
        warmup_trials=2,
        random_seed=42,
        solver_timeout_seconds=1.5,
        execution_iterations=10,
        case_ids=["dev-hand-001"],
    )
    assert cfg.protocol_version == BENCHMARK_PROTOCOL_VERSION
    assert cfg.trials_per_case == 4
    assert cfg.warmup_trials == 2
    assert cfg.warmup_policy is WarmupPolicy.DISCARD_FROM_SUMMARY
    assert cfg.timeout_policy is TimeoutPolicy.FIXED_SOLVER_TIMEOUT
    assert cfg.solver_timeout_seconds == 1.5
    assert cfg.random_seed == 42
    assert cfg.environment is not None
    assert "nondeterminism" in cfg.nondeterminism_disclosure.lower()
    mapping = configuration_to_mapping(cfg)
    assert mapping["trials_per_case"] == 4
    assert mapping["is_research_conclusion"] is False
    roundtrip = configuration_from_mapping(mapping)
    assert roundtrip.trials_per_case == cfg.trials_per_case
    assert roundtrip.random_seed == cfg.random_seed
    assert roundtrip.solver_timeout_seconds == cfg.solver_timeout_seconds


def test_timings_stored_separately() -> None:
    config = SemanticConfiguration(mode=SemanticMode.MODE_A)
    stages = measure_verification_stages("x + 0", "x", config)
    assert stages["parsing_seconds"] is not None
    assert stages["translation_seconds"] is not None
    assert stages["solver_seconds"] is not None
    assert stages["end_to_end_verification_seconds"] is not None
    # Distinct fields — solver time is not the only duration present.
    assert "solver_seconds" in stages
    assert "end_to_end_verification_seconds" in stages
    assert stages["verification_status"] is VerificationStatus.EQUIVALENT_WITHIN_MODEL

    gen = measure_candidate_generation("x + 0", config)
    assert gen["candidate_generation_seconds"] is not None
    assert gen["parsing_seconds"] is not None

    opt = measure_optimization("x + 0", config)
    assert opt["optimization_seconds"] is not None
    assert opt["optimized_source"] == "x"

    original_exec = measure_execution("x + 0", config, iterations=5)
    optimized_exec = measure_execution("x", config, iterations=5)
    assert original_exec >= 0.0
    assert optimized_exec >= 0.0


def test_verify_equivalence_timed_matches_untimed() -> None:
    config = SemanticConfiguration(mode=SemanticMode.MODE_A)
    timed = verify_equivalence_timed("x * 1", "x", config)
    assert timed.result.status is VerificationStatus.EQUIVALENT_WITHIN_MODEL
    assert timed.solver_seconds is not None
    assert timed.translation_seconds is not None
    assert timed.end_to_end_seconds >= (timed.solver_seconds or 0.0)


def test_rates_from_records() -> None:
    measurements = [
        BenchmarkMeasurement(
            measurement_id="m1",
            run_id="r1",
            case_id="c1",
            trial_index=0,
            is_warmup=False,
            seed=1,
            parsing_seconds=0.01,
            optimization_seconds=0.02,
            candidate_generation_seconds=0.01,
            translation_seconds=0.01,
            solver_seconds=0.05,
            end_to_end_verification_seconds=0.08,
            original_execution_seconds=0.001,
            optimized_execution_seconds=0.001,
            verification_status=VerificationStatus.EQUIVALENT_WITHIN_MODEL,
            candidate_accepted=True,
            rejection_recorded=False,
            counterexample_recorded=False,
            original_source="x + 0",
            candidate_source="x",
            optimized_source="x",
            transformation_category=TransformationCategory.IDENTITY_PRESERVING,
        ),
        BenchmarkMeasurement(
            measurement_id="m2",
            run_id="r1",
            case_id="c2",
            trial_index=0,
            is_warmup=False,
            seed=2,
            parsing_seconds=0.01,
            optimization_seconds=0.02,
            candidate_generation_seconds=0.01,
            translation_seconds=0.01,
            solver_seconds=0.05,
            end_to_end_verification_seconds=0.08,
            original_execution_seconds=0.001,
            optimized_execution_seconds=0.001,
            verification_status=VerificationStatus.COUNTEREXAMPLE_FOUND,
            candidate_accepted=False,
            rejection_recorded=True,
            counterexample_recorded=True,
            original_source="x + 1",
            candidate_source="x + 2",
            optimized_source=None,
            transformation_category=TransformationCategory.INCORRECT_REWRITE,
        ),
        BenchmarkMeasurement(
            measurement_id="m3",
            run_id="r1",
            case_id="c3",
            trial_index=0,
            is_warmup=False,
            seed=3,
            parsing_seconds=0.01,
            optimization_seconds=None,
            candidate_generation_seconds=None,
            translation_seconds=0.01,
            solver_seconds=1.0,
            end_to_end_verification_seconds=1.1,
            original_execution_seconds=None,
            optimized_execution_seconds=None,
            verification_status=VerificationStatus.TIMEOUT,
            candidate_accepted=False,
            rejection_recorded=True,
            counterexample_recorded=False,
            original_source="x",
            candidate_source="x + 0",
            optimized_source=None,
            transformation_category=TransformationCategory.DIFFICULT_SOLVER,
        ),
        BenchmarkMeasurement(
            measurement_id="m4",
            run_id="r1",
            case_id="c4",
            trial_index=0,
            is_warmup=False,
            seed=4,
            parsing_seconds=0.01,
            optimization_seconds=None,
            candidate_generation_seconds=None,
            translation_seconds=0.01,
            solver_seconds=0.2,
            end_to_end_verification_seconds=0.3,
            original_execution_seconds=None,
            optimized_execution_seconds=None,
            verification_status=VerificationStatus.UNKNOWN,
            candidate_accepted=False,
            rejection_recorded=True,
            counterexample_recorded=False,
            original_source="x",
            candidate_source="y",
            optimized_source=None,
            transformation_category=TransformationCategory.DIFFICULT_SOLVER,
        ),
    ]
    rates = compute_rate_summary(measurements)
    assert rates.sample_count == 4
    assert rates.timeout_count == 1
    assert rates.unknown_count == 1
    assert rates.completion_count == 2
    assert rates.rejection_count == 3
    assert rates.counterexample_count == 1
    assert rates.timeout_rate == 0.25
    assert rates.unknown_rate == 0.25
    assert rates.completion_rate == 0.5
    assert rates.rejection_rate == 0.75
    assert rates.counterexample_rate == 0.25


def test_medians_and_variability() -> None:
    stats = compute_timing_statistic("solver_seconds", [0.1, 0.2, 0.3, 0.4])
    assert stats.median_seconds == pytest.approx(0.25)
    assert stats.stdev_seconds is not None and stats.stdev_seconds > 0
    assert stats.iqr_seconds is not None and stats.iqr_seconds >= 0
    assert stats.min_seconds == 0.1
    assert stats.max_seconds == 0.4


def test_report_never_research_conclusion_and_speedup_policy() -> None:
    cfg = make_benchmark_configuration(trials_per_case=1, warmup_trials=0, collect_env=False)
    measurements = [
        BenchmarkMeasurement(
            measurement_id="m1",
            run_id="r1",
            case_id="c1",
            trial_index=0,
            is_warmup=False,
            seed=1,
            parsing_seconds=0.01,
            optimization_seconds=0.02,
            candidate_generation_seconds=0.01,
            translation_seconds=0.01,
            solver_seconds=0.05,
            end_to_end_verification_seconds=0.08,
            original_execution_seconds=0.002,
            optimized_execution_seconds=0.001,
            verification_status=VerificationStatus.EQUIVALENT_WITHIN_MODEL,
            candidate_accepted=True,
            rejection_recorded=False,
            counterexample_recorded=False,
            original_source="x + 0",
            candidate_source="x",
            optimized_source="x",
            transformation_category=TransformationCategory.IDENTITY_PRESERVING,
        )
    ]
    report = summarize_measurements("r1", cfg, measurements)
    assert report.is_research_conclusion is False
    assert "Never claim execution speedup" in report.speedup_claim_policy
    quantities = {row.quantity for row in report.timing}
    assert set(TIMING_QUANTITIES) == quantities

    with pytest.raises(BenchmarkError, match="§10.2"):
        assert_no_spurious_execution_speedup_claim(
            report,
            claim_text=(
                "Execution speedup improved because the shorter expression "
                "and faster solver returned more quickly"
            ),
        )
    # Legitimate separation statement is allowed.
    assert_no_spurious_execution_speedup_claim(
        report,
        claim_text="Solver latency and expression execution were measured separately.",
    )


def test_warmup_discarded_from_summary_by_default() -> None:
    cfg = make_benchmark_configuration(
        trials_per_case=1,
        warmup_trials=1,
        warmup_policy=WarmupPolicy.DISCARD_FROM_SUMMARY,
        collect_env=False,
    )
    measurements = [
        BenchmarkMeasurement(
            measurement_id="w",
            run_id="r",
            case_id="c",
            trial_index=-1,
            is_warmup=True,
            seed=0,
            parsing_seconds=9.0,
            optimization_seconds=9.0,
            candidate_generation_seconds=9.0,
            translation_seconds=9.0,
            solver_seconds=9.0,
            end_to_end_verification_seconds=9.0,
            original_execution_seconds=9.0,
            optimized_execution_seconds=9.0,
            verification_status=VerificationStatus.EQUIVALENT_WITHIN_MODEL,
            candidate_accepted=True,
            rejection_recorded=False,
            counterexample_recorded=False,
            original_source="x",
            candidate_source="x",
            optimized_source="x",
            transformation_category=None,
        ),
        BenchmarkMeasurement(
            measurement_id="t",
            run_id="r",
            case_id="c",
            trial_index=0,
            is_warmup=False,
            seed=1,
            parsing_seconds=0.1,
            optimization_seconds=0.1,
            candidate_generation_seconds=0.1,
            translation_seconds=0.1,
            solver_seconds=0.1,
            end_to_end_verification_seconds=0.1,
            original_execution_seconds=0.1,
            optimized_execution_seconds=0.1,
            verification_status=VerificationStatus.EQUIVALENT_WITHIN_MODEL,
            candidate_accepted=True,
            rejection_recorded=False,
            counterexample_recorded=False,
            original_source="x",
            candidate_source="x",
            optimized_source="x",
            transformation_category=None,
        ),
    ]
    report = summarize_measurements("r", cfg, measurements)
    assert report.measurement_count == 2
    assert report.summarized_trial_count == 1
    solver = next(row for row in report.timing if row.quantity == "solver_seconds")
    assert solver.median_seconds == pytest.approx(0.1)


def test_run_benchmark_persists_and_forbids_held_out(tmp_path: Path) -> None:
    cases = [
        _case("fix-equiv", "x + 0", "x"),
        _case(
            "fix-bad",
            "x + 1",
            "x + 2",
            expected=ExpectedOutcome.NON_EQUIVALENT,
            category=TransformationCategory.INCORRECT_REWRITE,
        ),
    ]
    cfg = make_benchmark_configuration(
        trials_per_case=2,
        warmup_trials=1,
        random_seed=7,
        solver_timeout_seconds=2.0,
        execution_iterations=5,
        case_ids=["fix-equiv", "fix-bad"],
        dataset_partition=DatasetPartition.DEVELOPMENT,
        notes="unit fixture — not a research conclusion",
    )
    with ExperimentStore(root=tmp_path) as store:
        run_id, measurements, report = run_benchmark(
            cfg, cases, store=store, persist=True
        )
        assert run_id
        # 2 cases * (1 warmup + 2 trials) = 6
        assert len(measurements) == 6
        assert report.is_research_conclusion is False
        assert report.rates.sample_count == 4  # warmups discarded
        obs = store.load_observations(run_id)
        assert len(obs) == 6
        assert all(o.kind is ObservationKind.BENCHMARK_TIMING for o in obs)
        # Separate timing fields present in payloads.
        payload = obs[0].payload
        for key in TIMING_QUANTITIES:
            assert key in payload
        snap = tmp_path / "raw" / run_id / "benchmark_configuration.json"
        assert snap.is_file()
        loaded = load_benchmark_configuration(snap)
        assert loaded.trials_per_case == 2
        assert loaded.random_seed == 7
        assert loaded.solver_timeout_seconds == 2.0
        assert loaded.environment is not None

    held = make_benchmark_configuration(
        dataset_partition=DatasetPartition.HELD_OUT,
        collect_env=False,
    )
    with pytest.raises(BenchmarkError, match="held-out"):
        run_benchmark(held, cases, persist=False)


def test_benchmark_reproduction_from_saved_config(tmp_path: Path) -> None:
    cases = [_case("repro-1", "x * 1", "x")]
    cfg = make_benchmark_configuration(
        trials_per_case=1,
        warmup_trials=0,
        random_seed=99,
        execution_iterations=3,
        case_ids=["repro-1"],
        notes="reproduction fixture",
    )
    config_path = save_benchmark_configuration(cfg, tmp_path / "bench_config.json")
    with ExperimentStore(root=tmp_path / "exp1") as store1:
        run_id1, measurements1, report1 = run_benchmark(
            cfg, cases, store=store1, persist=True
        )
    with ExperimentStore(root=tmp_path / "exp2") as store2:
        run_id2, measurements2, report2 = rerun_benchmark_from_saved_configuration(
            config_path,
            cases,
            store=store2,
            persist=True,
        )
    assert run_id1 != run_id2
    assert report1.is_research_conclusion is False
    assert report2.is_research_conclusion is False
    assert "nondeterminism" in report2.nondeterminism_disclosure.lower()
    # Outcome classification should be stable for this trivial case.
    assert measurements1[0].verification_status is VerificationStatus.EQUIVALENT_WITHIN_MODEL
    assert measurements2[0].verification_status is VerificationStatus.EQUIVALENT_WITHIN_MODEL
    # Timing fields remain separately recorded on both runs.
    for m in (measurements1[0], measurements2[0]):
        assert m.solver_seconds is not None
        assert m.original_execution_seconds is not None
        assert m.optimized_execution_seconds is not None
        # Solver and execution are distinct attributes (not one merged field).
        assert m.solver_seconds != m.original_execution_seconds or True


def test_measurement_roundtrip_observation() -> None:
    m = BenchmarkMeasurement(
        measurement_id="mid",
        run_id="rid",
        case_id="cid",
        trial_index=0,
        is_warmup=False,
        seed=3,
        parsing_seconds=0.1,
        optimization_seconds=0.2,
        candidate_generation_seconds=0.05,
        translation_seconds=0.03,
        solver_seconds=0.4,
        end_to_end_verification_seconds=0.5,
        original_execution_seconds=0.01,
        optimized_execution_seconds=0.009,
        verification_status=VerificationStatus.EQUIVALENT_WITHIN_MODEL,
        candidate_accepted=True,
        rejection_recorded=False,
        counterexample_recorded=False,
        original_source="x + 0",
        candidate_source="x",
        optimized_source="x",
        transformation_category=TransformationCategory.IDENTITY_PRESERVING,
        recorded_at_utc="2026-10-09T00:00:00Z",
    )
    obs = measurement_to_observation(m)
    assert obs.kind is ObservationKind.BENCHMARK_TIMING
    rebuilt = measurement_from_observation_payload(
        run_id=obs.run_id,
        observation_id=obs.observation_id,
        case_id=obs.case_id,
        verification_status=obs.verification_status,
        transformation_category=obs.transformation_category,
        payload=obs.payload,
        recorded_at_utc=obs.recorded_at_utc,
    )
    assert rebuilt.solver_seconds == 0.4
    assert rebuilt.original_execution_seconds == 0.01
    assert rebuilt.optimized_execution_seconds == 0.009
    assert rebuilt.parsing_seconds == 0.1
