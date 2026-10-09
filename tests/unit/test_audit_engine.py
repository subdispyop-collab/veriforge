"""Unit tests for Phase 7 audit recording, export, replay, and integrity."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

z3 = pytest.importorskip("z3")  # noqa: F841 — suite needs z3 for optimize/replay

from veriforge.audit_engine import (
    AUDIT_PROTOCOL_VERSION,
    assert_no_secrets_in_payload,
    build_optimization_run_record,
    export_audit_records,
    is_sensitive_key,
    list_run_history,
    make_audit_event,
    optimization_run_from_dict,
    optimization_run_to_dict,
    record_optimization_run,
    redact_secrets,
    replay_optimization_from_record,
    save_derived_summary,
    semantic_configuration_from_mapping,
    semantic_configuration_to_mapping,
    verify_storage_integrity,
)
from veriforge.config import SemanticConfiguration
from veriforge.exceptions import AuditError
from veriforge.experiment_engine import (
    configuration_fingerprint,
    create_experiment_run,
    make_observation,
    persist_run_with_observations,
)
from veriforge.models import (
    AuditEventKind,
    CandidateDecision,
    ExportFormat,
    IntegrityStatus,
    ObservationKind,
    SemanticMode,
    VerificationStatus,
)
from veriforge.optimizer_engine import optimize
from veriforge.storage import AuditRepository


@pytest.fixture
def mode_a() -> SemanticConfiguration:
    return SemanticConfiguration(mode=SemanticMode.MODE_A)


def test_redact_secrets_strips_sensitive_and_personal_keys() -> None:
    payload = {
        "expression": "x + 0",
        "api_key": "should-not-persist",
        "password": "hunter2",
        "nested": {"access_token": "abc", "ok": 1},
        "email": "person@example.com",
        "HOME": "/home/someone",
    }
    cleaned = redact_secrets(payload)
    assert cleaned["expression"] == "x + 0"
    assert cleaned["api_key"] == "[REDACTED]"
    assert cleaned["password"] == "[REDACTED]"
    assert cleaned["nested"]["access_token"] == "[REDACTED]"
    assert cleaned["nested"]["ok"] == 1
    assert cleaned["email"] == "[REDACTED]"
    assert cleaned["HOME"] == "[REDACTED]"
    assert is_sensitive_key("Authorization")
    with pytest.raises(AuditError, match="sensitive"):
        assert_no_secrets_in_payload(payload)


def test_optimization_run_stores_section_13_fields(mode_a: SemanticConfiguration) -> None:
    result = optimize("(x + 0) * 1", mode_a)
    record = build_optimization_run_record(
        result,
        timing_measurements={
            "optimization_seconds": 0.01,
            "api_token": 1.0,  # type: ignore[dict-item]
        },
    )
    assert record.run_id
    assert record.configuration_fingerprint
    assert len(record.configuration_fingerprint) == 64
    assert record.original_input == "(x + 0) * 1"
    assert record.normalized_representation
    assert record.semantic_mode is SemanticMode.MODE_A
    assert record.semantic_configuration["mode"] == "mode_a"
    assert record.applicable_rule_ids
    assert record.accepted_transformations
    assert all(
        step["decision"] == CandidateDecision.ACCEPTED.value
        for step in record.accepted_transformations
    )
    assert record.verification_query_artifacts
    assert record.solver_statuses
    assert "optimization_seconds" in record.timing_measurements
    assert record.timing_measurements["api_token"] == "[REDACTED]"
    assert record.software_version
    assert record.content_sha256
    assert record.configuration["protocol_version"] == AUDIT_PROTOCOL_VERSION
    assert record.error_information is None


def test_unique_run_id_and_fingerprint(mode_a: SemanticConfiguration) -> None:
    result = optimize("x + 0", mode_a)
    a = build_optimization_run_record(result)
    b = build_optimization_run_record(result)
    assert a.run_id != b.run_id
    assert a.configuration_fingerprint == b.configuration_fingerprint
    other = optimize("x * 1", mode_a)
    c = build_optimization_run_record(other)
    # Same semantic config and overlapping rules → same fingerprint family;
    # applicable rule ids may differ by expression, so fingerprints may differ.
    assert c.run_id != a.run_id
    assert c.configuration_fingerprint


def test_persist_and_reload_optimization_run(
    tmp_path: Path, mode_a: SemanticConfiguration
) -> None:
    result = optimize("x * 0", mode_a)
    with AuditRepository(root=tmp_path) as repo:
        record, event = record_optimization_run(result, repository=repo)
        assert event.event_kind is AuditEventKind.OPTIMIZATION_RUN_RECORDED
        assert event.run_id == record.run_id
        assert event.result_ref
        assert event.configuration_fingerprint == record.configuration_fingerprint
        loaded = repo.get_optimization_run(record.run_id)
        assert loaded is not None
        assert loaded.content_sha256 == record.content_sha256
        assert loaded.accepted_source == result.accepted.source
        history = list_run_history(repository=repo)
        assert any(row["run_id"] == record.run_id for row in history)


def test_export_json_and_csv_link_to_results(
    tmp_path: Path, mode_a: SemanticConfiguration
) -> None:
    result = optimize("x - 0", mode_a)
    with AuditRepository(root=tmp_path) as repo:
        record, _ = record_optimization_run(result, repository=repo)
        json_export = export_audit_records(
            format=ExportFormat.JSON,
            run_ids=[record.run_id],
            repository=repo,
        )
        csv_export = export_audit_records(
            format=ExportFormat.CSV,
            run_ids=[record.run_id],
            repository=repo,
            # §15: destination must resolve under experiments/exports/.
            destination=repo.exports_dir / "custom_export.csv",
        )
        assert json_export.record_count >= 1
        assert record.run_id in json_export.run_ids
        assert record.configuration_fingerprint in json_export.configuration_fingerprints
        payload = json.loads(Path(json_export.filesystem_path).read_text(encoding="utf-8"))
        assert payload["export_id"] == json_export.export_id
        linked = [
            row
            for row in payload["records"]
            if row.get("run_id") == record.run_id and row.get("result_link")
        ]
        assert linked
        assert any(
            "optimization_run" in str(row.get("result_link"))
            or row.get("record_kind") == "optimization_run"
            for row in linked
        )
        with Path(csv_export.filesystem_path).open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        assert rows
        assert any(row.get("run_id") == record.run_id for row in rows)


def test_secrets_not_stored_on_disk(
    tmp_path: Path, mode_a: SemanticConfiguration
) -> None:
    result = optimize("x + 0", mode_a)
    with AuditRepository(root=tmp_path) as repo:
        record, event = record_optimization_run(
            result,
            repository=repo,
            timing_measurements={"solver_seconds": 0.1, "secret": 9},  # type: ignore[dict-item]
        )
        path = repo.optimization_run_path(record.run_id)
        text = path.read_text(encoding="utf-8")
        assert "should-not" not in text
        data = json.loads(text)
        assert data["timing_measurements"]["secret"] == "[REDACTED]"
        assert_no_secrets_in_payload(data)
        assert_no_secrets_in_payload(event.detail)


def test_raw_separate_from_derived(
    tmp_path: Path, mode_a: SemanticConfiguration
) -> None:
    result = optimize("x + 0", mode_a)
    with AuditRepository(root=tmp_path) as repo:
        record, _ = record_optimization_run(result, repository=repo)
        derived = save_derived_summary(
            run_id=record.run_id,
            summary={"median_solver_seconds": 0.01, "chart": "placeholder"},
            repository=repo,
        )
        assert derived.is_relative_to(repo.derived_dir)
        assert not derived.is_relative_to(repo.raw_dir)
        raw_file = repo.optimization_run_path(record.run_id)
        assert raw_file.is_relative_to(repo.raw_dir)
        assert repo.raw_dir.resolve() != repo.derived_dir.resolve()


def test_integrity_passes_for_consistent_store(
    tmp_path: Path, mode_a: SemanticConfiguration
) -> None:
    result = optimize("(x * 1) + 0", mode_a)
    with AuditRepository(root=tmp_path) as repo:
        record_optimization_run(result, repository=repo)
        exp = create_experiment_run(configuration={"fixture": "integrity"})
        obs = make_observation(
            run_id=exp.run_id,
            kind=ObservationKind.METRIC_FIXTURE,
            payload={"value": 1},
        )
        persist_run_with_observations(exp, [obs], store=repo.store)
        report = verify_storage_integrity(repository=repo, persist_event=True)
        assert report.status is IntegrityStatus.PASSED
        assert report.passed
        assert report.runs_checked >= 1
        assert report.raw_root != report.derived_root


def test_integrity_detects_fingerprint_tamper(
    tmp_path: Path, mode_a: SemanticConfiguration
) -> None:
    result = optimize("x + 0", mode_a)
    with AuditRepository(root=tmp_path) as repo:
        record, _ = record_optimization_run(result, repository=repo)
        path = repo.optimization_run_path(record.run_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        data["configuration_fingerprint"] = "0" * 64
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        report = verify_storage_integrity(repository=repo, persist_event=False)
        assert report.status is IntegrityStatus.FAILED
        codes = {issue.code for issue in report.issues}
        assert "opt_fingerprint_mismatch" in codes or "content_digest_mismatch" in codes


def test_replay_uses_recorded_configuration(
    tmp_path: Path, mode_a: SemanticConfiguration
) -> None:
    result = optimize("(x + 0) * 1", mode_a)
    with AuditRepository(root=tmp_path) as repo:
        record, _ = record_optimization_run(result, repository=repo)
        replayed = replay_optimization_from_record(record, repository=repo)
        assert replayed.accepted.source == record.accepted_source
        assert replayed.config.mode is mode_a.mode
        events = repo.list_audit_events(run_ids=[record.run_id])
        kinds = {event.event_kind for event in events}
        assert AuditEventKind.REPLAY_EXECUTED in kinds
        # Fingerprint of recorded configuration must still verify.
        assert (
            configuration_fingerprint(dict(record.configuration))
            == record.configuration_fingerprint
        )


def test_semantic_configuration_roundtrip(mode_a: SemanticConfiguration) -> None:
    mapping = semantic_configuration_to_mapping(mode_a)
    restored = semantic_configuration_from_mapping(mapping)
    assert restored.mode is mode_a.mode
    assert restored.bit_width == mode_a.bit_width
    assert restored.limits.solver_timeout_seconds == mode_a.limits.solver_timeout_seconds


def test_optimization_run_dict_roundtrip(mode_a: SemanticConfiguration) -> None:
    result = optimize("x * 1", mode_a)
    record = build_optimization_run_record(result)
    restored = optimization_run_from_dict(optimization_run_to_dict(record))
    assert restored.run_id == record.run_id
    assert restored.content_sha256 == record.content_sha256
    assert restored.accepted_transformations == record.accepted_transformations


def test_audit_event_links_result_ref(
    tmp_path: Path, mode_a: SemanticConfiguration
) -> None:
    result = optimize("x + 0", mode_a)
    with AuditRepository(root=tmp_path) as repo:
        record, event = record_optimization_run(result, repository=repo)
        assert event.result_ref == repo.optimization_run_relative_path(record.run_id)
        assert (repo.root / event.result_ref).exists()


def test_mode_b_optimization_run_records_bit_width() -> None:
    cfg = SemanticConfiguration(mode=SemanticMode.MODE_B, bit_width=32)
    result = optimize("x + 0", cfg)
    record = build_optimization_run_record(result)
    assert record.semantic_mode is SemanticMode.MODE_B
    assert record.bit_width == 32
    assert any(
        step.get("verification_result", {}).get("status")
        == VerificationStatus.EQUIVALENT_WITHIN_MODEL.value
        for step in record.accepted_transformations
    )


def test_make_audit_event_redacts_detail() -> None:
    event = make_audit_event(
        event_kind=AuditEventKind.ERROR_RECORDED,
        detail={"message": "ok", "password": "nope"},
        message="error",
    )
    assert event.detail["password"] == "[REDACTED]"
    assert event.detail["message"] == "ok"
