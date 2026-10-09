"""Auditability, export, replay, and storage integrity (Phase 7 / §13).

Each optimization run preserves the fields required by the controlling
specification section 13. Experiment runs keep unique identifiers and
configuration fingerprints. Audit records export to JSON or CSV and link to
the results they describe. Secrets and unnecessary personal data are stripped
before persistence. Replay uses the recorded configuration. Raw records stay
separate from derived charts and summaries.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import uuid
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from veriforge.config import SemanticConfiguration
from veriforge.exceptions import AuditError
from veriforge.experiment_engine import (
    configuration_fingerprint,
    new_run_id,
    utc_now_iso,
)
from veriforge.models import (
    AuditEvent,
    AuditEventKind,
    AuditExportResult,
    CandidateDecision,
    Counterexample,
    ExportFormat,
    IntegrityIssue,
    IntegrityReport,
    IntegrityStatus,
    ObservationKind,
    OptimizationResult,
    OptimizationRunRecord,
    OptimizationRule,
    RawObservation,
    SemanticMode,
    TransformationStep,
    VerificationResult,
)
from veriforge.storage.database import ExperimentStore
from veriforge.storage.repositories import AuditRepository
from veriforge.version import __version__ as SOFTWARE_VERSION


def _optimizer():
    """Lazy import so audit helpers that do not optimize can load without z3."""

    from veriforge import optimizer_engine

    return optimizer_engine

AUDIT_PROTOCOL_ID = "veriforge-phase7-audit-protocol"
AUDIT_PROTOCOL_VERSION = "0.7.0"

# Keys / substrings that must never appear in persisted audit payloads (§12).
_SECRET_KEY_PATTERN = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|access[_-]?key|"
    r"private[_-]?key|credential|auth(?:orization)?|bearer|"
    r"session[_-]?id|cookie|ssh[_-]?key)",
    re.IGNORECASE,
)
_PERSONAL_KEY_PATTERN = re.compile(
    r"(home|user(?:name)?|email|full[_-]?name|phone|ssn|"
    r"ip[_-]?address|mac[_-]?address|geolocation)",
    re.IGNORECASE,
)
_REDACTED = "[REDACTED]"

VERIFICATION_QUERY_FORM = "exists x: E_o(x) != E_c(x)"


def new_event_id() -> str:
    return str(uuid.uuid4())


def new_export_id() -> str:
    return str(uuid.uuid4())


def is_sensitive_key(key: str) -> bool:
    """Return True when a mapping key must not be stored in audit artifacts."""

    return bool(_SECRET_KEY_PATTERN.search(key) or _PERSONAL_KEY_PATTERN.search(key))


def redact_secrets(value: Any) -> Any:
    """Recursively strip secrets and unnecessary personal data from payloads."""

    if isinstance(value, Mapping):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            key_str = str(key)
            if is_sensitive_key(key_str):
                cleaned[key_str] = _REDACTED
            else:
                cleaned[key_str] = redact_secrets(item)
        return cleaned
    if isinstance(value, (list, tuple)):
        return [redact_secrets(item) for item in value]
    return value


def semantic_configuration_to_mapping(config: SemanticConfiguration) -> dict[str, Any]:
    """Serialize a SemanticConfiguration for fingerprints and replay."""

    return {
        "mode": config.mode.value,
        "bit_width": config.bit_width,
        "limits": {
            "max_source_length": config.limits.max_source_length,
            "max_ast_nodes": config.limits.max_ast_nodes,
            "max_nesting_depth": config.limits.max_nesting_depth,
            "max_mode_a_literal_bit_length": (
                config.limits.max_mode_a_literal_bit_length
            ),
            "solver_timeout_seconds": config.limits.solver_timeout_seconds,
        },
    }


def semantic_configuration_from_mapping(
    data: Mapping[str, Any],
) -> SemanticConfiguration:
    """Rebuild a SemanticConfiguration from a recorded mapping."""

    from veriforge.config import ResourceLimits

    limits_data = data.get("limits") or {}
    limits = ResourceLimits(
        max_source_length=int(
            limits_data.get("max_source_length", ResourceLimits().max_source_length)
        ),
        max_ast_nodes=int(
            limits_data.get("max_ast_nodes", ResourceLimits().max_ast_nodes)
        ),
        max_nesting_depth=int(
            limits_data.get(
                "max_nesting_depth", ResourceLimits().max_nesting_depth
            )
        ),
        max_mode_a_literal_bit_length=int(
            limits_data.get(
                "max_mode_a_literal_bit_length",
                ResourceLimits().max_mode_a_literal_bit_length,
            )
        ),
        solver_timeout_seconds=float(
            limits_data.get(
                "solver_timeout_seconds",
                ResourceLimits().solver_timeout_seconds,
            )
        ),
    )
    return SemanticConfiguration(
        mode=SemanticMode(str(data["mode"])),
        bit_width=int(data.get("bit_width", 32)),
        limits=limits,
    )


def optimization_configuration_mapping(
    *,
    config: SemanticConfiguration,
    policy: str,
    rule_ids: Sequence[str],
    software_version: str = SOFTWARE_VERSION,
    protocol_version: str = AUDIT_PROTOCOL_VERSION,
) -> dict[str, Any]:
    """Build the configuration mapping fingerprinted for an optimization run."""

    return redact_secrets(
        {
            "protocol_id": AUDIT_PROTOCOL_ID,
            "protocol_version": protocol_version,
            "software_version": software_version,
            "correctness_policy": policy,
            "semantic_configuration": semantic_configuration_to_mapping(config),
            "rule_ids": list(rule_ids),
        }
    )


def _counterexample_to_mapping(cex: Counterexample | None) -> dict[str, Any] | None:
    if cex is None:
        return None
    return {
        "assignment": dict(cex.assignment),
        "original_value": cex.original_value,
        "candidate_value": cex.candidate_value,
        "validation_status": cex.validation_status.value,
        "detail": cex.detail,
    }


def _verification_to_mapping(result: VerificationResult | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "status": result.status.value,
        "mode": result.mode.value,
        "bit_width": result.bit_width,
        "timeout_seconds": result.timeout_seconds,
        "original_source": result.original_source,
        "candidate_source": result.candidate_source,
        "solver_status": result.solver_status,
        "reason": result.reason,
        "counterexample": _counterexample_to_mapping(result.counterexample),
    }


def _step_to_mapping(step: TransformationStep) -> dict[str, Any]:
    return {
        "step_index": step.step_index,
        "rule_id": step.rule_id,
        "rule_name": step.rule_name,
        "formal_description": step.formal_description,
        "preconditions": list(step.preconditions),
        "matched_preconditions": list(step.matched_preconditions),
        "supported_modes": sorted(mode.value for mode in step.supported_modes),
        "verification_policy": step.verification_policy.value,
        "before_source": step.before_source,
        "after_source": step.after_source,
        "decision": step.decision.value,
        "verification_result": _verification_to_mapping(step.verification_result),
        "rejection_reason": step.rejection_reason,
    }


def _query_artifact_for_step(step: TransformationStep) -> dict[str, Any]:
    verification = step.verification_result
    return {
        "query_form": VERIFICATION_QUERY_FORM,
        "step_index": step.step_index,
        "rule_id": step.rule_id,
        "original_source": (
            None if verification is None else verification.original_source
        ),
        "candidate_source": step.after_source,
        "mode": None if verification is None else verification.mode.value,
        "bit_width": None if verification is None else verification.bit_width,
        "timeout_seconds": (
            None if verification is None else verification.timeout_seconds
        ),
        "solver_status": None if verification is None else verification.solver_status,
        "verification_status": (
            None if verification is None else verification.status.value
        ),
    }


def content_sha256(payload: Mapping[str, Any]) -> str:
    """Stable content digest used by integrity checks."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def build_optimization_run_record(
    result: OptimizationResult,
    *,
    run_id: str | None = None,
    timing_measurements: Mapping[str, float | None] | None = None,
    error_information: str | None = None,
    applicable_rules: Sequence[OptimizationRule] | None = None,
    software_version: str = SOFTWARE_VERSION,
    created_at_utc: str | None = None,
) -> OptimizationRunRecord:
    """Build a §13 optimization-run record from an OptimizationResult.

    Does not persist. Secrets in caller-supplied timing/error maps are redacted.
    """

    opt = _optimizer()
    rules = (
        tuple(applicable_rules)
        if applicable_rules is not None
        else opt.default_rules()
    )
    matches = opt.find_applicable_matches(
        result.original, result.config, rules=rules
    )
    applicable_ids = tuple(dict.fromkeys(match.rule.rule_id for match in matches))
    # Also include rules that actually appeared in the trace (accepted/rejected).
    for step in result.trace:
        if step.rule_id not in applicable_ids:
            applicable_ids = applicable_ids + (step.rule_id,)

    accepted = tuple(
        _step_to_mapping(step)
        for step in result.trace
        if step.decision is CandidateDecision.ACCEPTED
    )
    rejected = tuple(
        _step_to_mapping(step)
        for step in result.trace
        if step.decision is CandidateDecision.REJECTED
    )
    query_artifacts = tuple(_query_artifact_for_step(step) for step in result.trace)
    solver_statuses = tuple(
        (
            step.verification_result.solver_status
            if step.verification_result and step.verification_result.solver_status
            else (
                step.verification_result.status.value
                if step.verification_result
                else "no_verification"
            )
        )
        for step in result.trace
    )
    counterexamples = tuple(
        cex
        for cex in (
            _counterexample_to_mapping(
                None
                if step.verification_result is None
                else step.verification_result.counterexample
            )
            for step in result.trace
        )
        if cex is not None
    )

    policy = result.policy.value
    configuration = optimization_configuration_mapping(
        config=result.config,
        policy=policy,
        rule_ids=applicable_ids,
        software_version=software_version,
    )
    fingerprint = configuration_fingerprint(configuration)
    semantic_cfg = semantic_configuration_to_mapping(result.config)
    timing = redact_secrets(dict(timing_measurements or {}))
    normalized = opt.render_expr(result.original.root)

    body = {
        "original_input": result.original.source,
        "normalized_representation": normalized,
        "semantic_configuration": semantic_cfg,
        "applicable_rule_ids": list(applicable_ids),
        "accepted_transformations": list(accepted),
        "rejected_transformations": list(rejected),
        "verification_query_artifacts": list(query_artifacts),
        "solver_statuses": list(solver_statuses),
        "counterexample_records": list(counterexamples),
        "timing_measurements": timing,
        "error_information": error_information,
        "configuration": configuration,
        "correctness_policy": policy,
        "accepted_source": result.accepted.source,
        "software_version": software_version,
        "configuration_fingerprint": fingerprint,
    }
    digest = content_sha256(body)
    rid = run_id or new_run_id()
    return OptimizationRunRecord(
        run_id=rid,
        created_at_utc=created_at_utc or utc_now_iso(),
        software_version=software_version,
        configuration_fingerprint=fingerprint,
        original_input=result.original.source,
        normalized_representation=normalized,
        semantic_mode=result.config.mode,
        bit_width=(
            result.config.bit_width
            if result.config.mode is SemanticMode.MODE_B
            else None
        ),
        semantic_configuration=semantic_cfg,
        applicable_rule_ids=applicable_ids,
        accepted_transformations=accepted,
        rejected_transformations=rejected,
        verification_query_artifacts=query_artifacts,
        solver_statuses=solver_statuses,
        counterexample_records=counterexamples,
        timing_measurements=timing,
        error_information=error_information,
        configuration=configuration,
        correctness_policy=policy,
        accepted_source=result.accepted.source,
        content_sha256=digest,
    )


def optimization_run_to_dict(record: OptimizationRunRecord) -> dict[str, Any]:
    return redact_secrets(
        {
            "run_id": record.run_id,
            "created_at_utc": record.created_at_utc,
            "software_version": record.software_version,
            "configuration_fingerprint": record.configuration_fingerprint,
            "original_input": record.original_input,
            "normalized_representation": record.normalized_representation,
            "semantic_mode": record.semantic_mode.value,
            "bit_width": record.bit_width,
            "semantic_configuration": dict(record.semantic_configuration),
            "applicable_rule_ids": list(record.applicable_rule_ids),
            "accepted_transformations": [
                dict(item) for item in record.accepted_transformations
            ],
            "rejected_transformations": [
                dict(item) for item in record.rejected_transformations
            ],
            "verification_query_artifacts": [
                dict(item) for item in record.verification_query_artifacts
            ],
            "solver_statuses": list(record.solver_statuses),
            "counterexample_records": [
                dict(item) for item in record.counterexample_records
            ],
            "timing_measurements": dict(record.timing_measurements),
            "error_information": record.error_information,
            "configuration": dict(record.configuration),
            "correctness_policy": record.correctness_policy,
            "accepted_source": record.accepted_source,
            "content_sha256": record.content_sha256,
            "record_kind": "optimization_run",
        }
    )


def optimization_run_from_dict(data: Mapping[str, Any]) -> OptimizationRunRecord:
    return OptimizationRunRecord(
        run_id=str(data["run_id"]),
        created_at_utc=str(data["created_at_utc"]),
        software_version=str(data["software_version"]),
        configuration_fingerprint=str(data["configuration_fingerprint"]),
        original_input=str(data["original_input"]),
        normalized_representation=str(data["normalized_representation"]),
        semantic_mode=SemanticMode(str(data["semantic_mode"])),
        bit_width=None if data.get("bit_width") is None else int(data["bit_width"]),
        semantic_configuration=dict(data.get("semantic_configuration") or {}),
        applicable_rule_ids=tuple(str(x) for x in data.get("applicable_rule_ids") or ()),
        accepted_transformations=tuple(
            dict(x) for x in data.get("accepted_transformations") or ()
        ),
        rejected_transformations=tuple(
            dict(x) for x in data.get("rejected_transformations") or ()
        ),
        verification_query_artifacts=tuple(
            dict(x) for x in data.get("verification_query_artifacts") or ()
        ),
        solver_statuses=tuple(str(x) for x in data.get("solver_statuses") or ()),
        counterexample_records=tuple(
            dict(x) for x in data.get("counterexample_records") or ()
        ),
        timing_measurements=dict(data.get("timing_measurements") or {}),
        error_information=(
            None
            if data.get("error_information") is None
            else str(data["error_information"])
        ),
        configuration=dict(data.get("configuration") or {}),
        correctness_policy=str(data["correctness_policy"]),
        accepted_source=str(data["accepted_source"]),
        content_sha256=str(data["content_sha256"]),
    )


def make_audit_event(
    *,
    event_kind: AuditEventKind,
    run_id: str | None = None,
    configuration_fingerprint: str | None = None,
    result_ref: str | None = None,
    detail: Mapping[str, Any] | None = None,
    message: str | None = None,
    software_version: str = SOFTWARE_VERSION,
    event_id: str | None = None,
    created_at_utc: str | None = None,
) -> AuditEvent:
    return AuditEvent(
        event_id=event_id or new_event_id(),
        event_kind=event_kind,
        created_at_utc=created_at_utc or utc_now_iso(),
        run_id=run_id,
        configuration_fingerprint=configuration_fingerprint,
        result_ref=result_ref,
        software_version=software_version,
        detail=redact_secrets(dict(detail or {})),
        message=message,
    )


def audit_event_to_dict(event: AuditEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "event_kind": event.event_kind.value,
        "created_at_utc": event.created_at_utc,
        "run_id": event.run_id,
        "configuration_fingerprint": event.configuration_fingerprint,
        "result_ref": event.result_ref,
        "software_version": event.software_version,
        "detail": dict(event.detail),
        "message": event.message,
    }


def audit_event_from_dict(data: Mapping[str, Any]) -> AuditEvent:
    return AuditEvent(
        event_id=str(data["event_id"]),
        event_kind=AuditEventKind(str(data["event_kind"])),
        created_at_utc=str(data["created_at_utc"]),
        run_id=None if data.get("run_id") is None else str(data["run_id"]),
        configuration_fingerprint=(
            None
            if data.get("configuration_fingerprint") is None
            else str(data["configuration_fingerprint"])
        ),
        result_ref=(
            None if data.get("result_ref") is None else str(data["result_ref"])
        ),
        software_version=str(data["software_version"]),
        detail=dict(data.get("detail") or {}),
        message=None if data.get("message") is None else str(data["message"]),
    )


def record_optimization_run(
    result: OptimizationResult,
    *,
    repository: AuditRepository | None = None,
    root: Path | None = None,
    run_id: str | None = None,
    timing_measurements: Mapping[str, float | None] | None = None,
    error_information: str | None = None,
    applicable_rules: Sequence[OptimizationRule] | None = None,
) -> tuple[OptimizationRunRecord, AuditEvent]:
    """Persist an optimization run (§13) and a linking audit event."""

    owns = repository is None
    repo = repository or AuditRepository(root=root)
    try:
        record = build_optimization_run_record(
            result,
            run_id=run_id,
            timing_measurements=timing_measurements,
            error_information=error_information,
            applicable_rules=applicable_rules,
        )
        result_ref = repo.save_optimization_run(record)
        event = make_audit_event(
            event_kind=AuditEventKind.OPTIMIZATION_RUN_RECORDED,
            run_id=record.run_id,
            configuration_fingerprint=record.configuration_fingerprint,
            result_ref=result_ref,
            detail={
                "original_input": record.original_input,
                "accepted_source": record.accepted_source,
                "content_sha256": record.content_sha256,
            },
            message="optimization run recorded",
        )
        repo.save_audit_event(event)
        return record, event
    finally:
        if owns:
            repo.close()


def list_run_history(
    *,
    repository: AuditRepository | None = None,
    root: Path | None = None,
) -> tuple[dict[str, Any], ...]:
    """Return run-history rows (optimization + experiment) newest-first."""

    owns = repository is None
    repo = repository or AuditRepository(root=root)
    try:
        return repo.list_run_history()
    finally:
        if owns:
            repo.close()


def export_audit_records(
    *,
    format: ExportFormat,
    run_ids: Sequence[str] | None = None,
    repository: AuditRepository | None = None,
    root: Path | None = None,
    destination: Path | None = None,
) -> AuditExportResult:
    """Export audit events (and linked result refs) to JSON or CSV."""

    owns = repository is None
    repo = repository or AuditRepository(root=root)
    try:
        events = repo.list_audit_events(run_ids=run_ids)
        if not events and run_ids:
            # Still allow exporting optimization-run payloads linked by run_id.
            pass
        rows: list[dict[str, Any]] = []
        fingerprints: list[str] = []
        linked_run_ids: list[str] = []
        for event in events:
            row = audit_event_to_dict(event)
            row["result_link"] = event.result_ref
            rows.append(row)
            if event.run_id:
                linked_run_ids.append(event.run_id)
            if event.configuration_fingerprint:
                fingerprints.append(event.configuration_fingerprint)

        # Include optimization-run result payloads so exports link to results.
        target_runs = (
            tuple(run_ids)
            if run_ids is not None
            else tuple(dict.fromkeys(linked_run_ids))
        )
        for rid in target_runs:
            opt = repo.get_optimization_run(rid)
            if opt is None:
                continue
            payload = optimization_run_to_dict(opt)
            payload["result_link"] = repo.optimization_run_relative_path(rid)
            payload["linked_from"] = "optimization_run_record"
            rows.append(payload)
            linked_run_ids.append(rid)
            fingerprints.append(opt.configuration_fingerprint)

        if not rows:
            raise AuditError("no audit records available to export")

        export_id = new_export_id()
        created = utc_now_iso()
        unique_runs = tuple(dict.fromkeys(linked_run_ids))
        unique_fps = tuple(dict.fromkeys(fingerprints))

        if destination is None:
            dest_dir = repo.exports_dir
            dest_dir.mkdir(parents=True, exist_ok=True)
            suffix = "json" if format is ExportFormat.JSON else "csv"
            destination = dest_dir / f"audit_export_{export_id}.{suffix}"
        else:
            destination = Path(destination)
            destination.parent.mkdir(parents=True, exist_ok=True)

        if format is ExportFormat.JSON:
            envelope = {
                "export_id": export_id,
                "created_at_utc": created,
                "format": format.value,
                "run_ids": list(unique_runs),
                "configuration_fingerprints": list(unique_fps),
                "records": rows,
            }
            destination.write_text(
                json.dumps(envelope, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        elif format is ExportFormat.CSV:
            fieldnames = sorted({key for row in rows for key in _flatten_row(row)})
            with destination.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    writer.writerow(_flatten_row(row))
        else:
            raise AuditError(f"unsupported export format: {format}")

        result = AuditExportResult(
            export_id=export_id,
            format=format,
            created_at_utc=created,
            filesystem_path=str(destination),
            run_ids=unique_runs,
            record_count=len(rows),
            configuration_fingerprints=unique_fps,
        )
        export_event = make_audit_event(
            event_kind=AuditEventKind.EXPORT_CREATED,
            run_id=unique_runs[0] if unique_runs else None,
            configuration_fingerprint=unique_fps[0] if unique_fps else None,
            result_ref=str(destination),
            detail={
                "export_id": export_id,
                "format": format.value,
                "record_count": len(rows),
                "run_ids": list(unique_runs),
            },
            message="audit records exported",
        )
        repo.save_audit_event(export_event)
        return result
    finally:
        if owns:
            repo.close()


def _flatten_row(row: Mapping[str, Any]) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, (dict, list, tuple)):
            flat[key] = json.dumps(value, sort_keys=True, separators=(",", ":"))
        else:
            flat[key] = value
    return flat


def replay_optimization_from_record(
    record: OptimizationRunRecord,
    *,
    repository: AuditRepository | None = None,
    root: Path | None = None,
    persist_event: bool = True,
) -> OptimizationResult:
    """Rerun optimization using the recorded configuration (§13 replay).

    Uses ``record.configuration`` / ``semantic_configuration`` rather than
    ambient defaults. Timing and solver nondeterminism may still differ;
    see ``docs/LIMITATIONS.md``.
    """

    opt = _optimizer()
    cfg_map = record.semantic_configuration or record.configuration.get(
        "semantic_configuration"
    )
    if not isinstance(cfg_map, Mapping):
        raise AuditError(
            "recorded optimization run is missing semantic_configuration for replay"
        )
    config = semantic_configuration_from_mapping(cfg_map)
    expected_fp = configuration_fingerprint(
        optimization_configuration_mapping(
            config=config,
            policy=str(
                record.correctness_policy
                or record.configuration.get("correctness_policy")
            ),
            rule_ids=list(
                record.applicable_rule_ids
                or record.configuration.get("rule_ids")
                or [rule.rule_id for rule in opt.default_rules()]
            ),
            software_version=str(
                record.configuration.get("software_version", record.software_version)
            ),
            protocol_version=str(
                record.configuration.get("protocol_version", AUDIT_PROTOCOL_VERSION)
            ),
        )
    )
    if expected_fp != record.configuration_fingerprint:
        # Soft check: fingerprint uses the rule set that was applicable at
        # record time; recreate with the same recorded configuration body.
        recorded_cfg = dict(record.configuration)
        if configuration_fingerprint(recorded_cfg) != record.configuration_fingerprint:
            raise AuditError(
                "configuration fingerprint does not match recorded configuration; "
                "refusing replay"
            )

    result = opt.optimize(record.original_input, config)
    if persist_event:
        owns = repository is None
        repo = repository or AuditRepository(root=root)
        try:
            event = make_audit_event(
                event_kind=AuditEventKind.REPLAY_EXECUTED,
                run_id=record.run_id,
                configuration_fingerprint=record.configuration_fingerprint,
                result_ref=repo.optimization_run_relative_path(record.run_id),
                detail={
                    "replayed_accepted_source": result.accepted.source,
                    "recorded_accepted_source": record.accepted_source,
                    "used_recorded_configuration": True,
                },
                message="optimization replayed from recorded configuration",
            )
            repo.save_audit_event(event)
        finally:
            if owns:
                repo.close()
    return result


def assert_no_secrets_in_payload(payload: Any, *, path: str = "$") -> None:
    """Raise AuditError if a sensitive key escapes redaction."""

    if isinstance(payload, Mapping):
        for key, value in payload.items():
            key_str = str(key)
            child = f"{path}.{key_str}"
            if is_sensitive_key(key_str) and value != _REDACTED:
                raise AuditError(
                    f"sensitive key {key_str!r} at {child} must be redacted"
                )
            assert_no_secrets_in_payload(value, path=child)
    elif isinstance(payload, (list, tuple)):
        for index, item in enumerate(payload):
            assert_no_secrets_in_payload(item, path=f"{path}[{index}]")


def verify_storage_integrity(
    *,
    repository: AuditRepository | None = None,
    root: Path | None = None,
    persist_event: bool = True,
) -> IntegrityReport:
    """Check fingerprints, raw/derived separation, and observation linkage."""

    owns = repository is None
    repo = repository or AuditRepository(root=root)
    try:
        issues: list[IntegrityIssue] = []
        raw_root = repo.raw_dir
        derived_root = repo.derived_dir

        if raw_root.resolve() == derived_root.resolve():
            issues.append(
                IntegrityIssue(
                    code="raw_derived_collision",
                    path_or_id=str(raw_root),
                    detail="raw and derived roots must be distinct paths",
                )
            )

        # Raw tree must not contain derived summary markers.
        if raw_root.exists():
            for path in raw_root.rglob("*"):
                if not path.is_file():
                    continue
                name = path.name.lower()
                if name.endswith((".png", ".svg", ".html")) or name.startswith(
                    "summary_"
                ):
                    issues.append(
                        IntegrityIssue(
                            code="derived_in_raw",
                            path_or_id=str(path),
                            detail="derived chart/summary artifact found under raw/",
                        )
                    )

        runs = repo.store.list_runs()
        observations_checked = 0
        for run in runs:
            recomputed = configuration_fingerprint(dict(run.configuration))
            if recomputed != run.configuration_fingerprint:
                issues.append(
                    IntegrityIssue(
                        code="fingerprint_mismatch",
                        path_or_id=run.run_id,
                        detail=(
                            "stored configuration_fingerprint does not match "
                            "hash of configuration_json"
                        ),
                    )
                )
            for obs in repo.store.load_observations(run.run_id):
                observations_checked += 1
                if obs.run_id != run.run_id:
                    issues.append(
                        IntegrityIssue(
                            code="observation_run_mismatch",
                            path_or_id=obs.observation_id,
                            detail=(
                                f"observation.run_id={obs.run_id} "
                                f"!= run.run_id={run.run_id}"
                            ),
                        )
                    )
                try:
                    assert_no_secrets_in_payload(obs.payload)
                except AuditError as exc:
                    issues.append(
                        IntegrityIssue(
                            code="secret_in_payload",
                            path_or_id=obs.observation_id,
                            detail=str(exc),
                        )
                    )

        opt_runs = repo.list_optimization_runs()
        for record in opt_runs:
            body = optimization_run_to_dict(record)
            # Recompute using the same fields as build time.
            rebuild = {
                "original_input": record.original_input,
                "normalized_representation": record.normalized_representation,
                "semantic_configuration": dict(record.semantic_configuration),
                "applicable_rule_ids": list(record.applicable_rule_ids),
                "accepted_transformations": [
                    dict(x) for x in record.accepted_transformations
                ],
                "rejected_transformations": [
                    dict(x) for x in record.rejected_transformations
                ],
                "verification_query_artifacts": [
                    dict(x) for x in record.verification_query_artifacts
                ],
                "solver_statuses": list(record.solver_statuses),
                "counterexample_records": [
                    dict(x) for x in record.counterexample_records
                ],
                "timing_measurements": dict(record.timing_measurements),
                "error_information": record.error_information,
                "configuration": dict(record.configuration),
                "correctness_policy": record.correctness_policy,
                "accepted_source": record.accepted_source,
                "software_version": record.software_version,
                "configuration_fingerprint": record.configuration_fingerprint,
            }
            digest = content_sha256(rebuild)
            if digest != record.content_sha256:
                issues.append(
                    IntegrityIssue(
                        code="content_digest_mismatch",
                        path_or_id=record.run_id,
                        detail="optimization run content_sha256 mismatch",
                    )
                )
            fp = configuration_fingerprint(dict(record.configuration))
            if fp != record.configuration_fingerprint:
                issues.append(
                    IntegrityIssue(
                        code="opt_fingerprint_mismatch",
                        path_or_id=record.run_id,
                        detail="optimization configuration fingerprint mismatch",
                    )
                )
            try:
                assert_no_secrets_in_payload(body)
            except AuditError as exc:
                issues.append(
                    IntegrityIssue(
                        code="secret_in_optimization_run",
                        path_or_id=record.run_id,
                        detail=str(exc),
                    )
                )

        events = repo.list_audit_events()
        for event in events:
            try:
                assert_no_secrets_in_payload(event.detail)
            except AuditError as exc:
                issues.append(
                    IntegrityIssue(
                        code="secret_in_audit_event",
                        path_or_id=event.event_id,
                        detail=str(exc),
                    )
                )
            if event.result_ref:
                # result_ref may be absolute or relative to store root.
                ref_path = Path(event.result_ref)
                if not ref_path.is_absolute():
                    ref_path = repo.root / ref_path
                if event.event_kind is not AuditEventKind.EXPORT_CREATED:
                    if not ref_path.exists():
                        issues.append(
                            IntegrityIssue(
                                code="missing_result_ref",
                                path_or_id=event.event_id,
                                detail=f"result_ref not found: {event.result_ref}",
                            )
                        )

        status = (
            IntegrityStatus.PASSED if not issues else IntegrityStatus.FAILED
        )
        report = IntegrityReport(
            status=status,
            checked_at_utc=utc_now_iso(),
            runs_checked=len(runs) + len(opt_runs),
            observations_checked=observations_checked,
            audit_events_checked=len(events),
            issues=tuple(issues),
            raw_root=str(raw_root),
            derived_root=str(derived_root),
        )
        if persist_event:
            event = make_audit_event(
                event_kind=AuditEventKind.INTEGRITY_CHECK,
                detail={
                    "status": status.value,
                    "issue_count": len(issues),
                    "runs_checked": report.runs_checked,
                    "observations_checked": report.observations_checked,
                },
                message=f"integrity check {status.value}",
            )
            repo.save_audit_event(event)
        return report
    finally:
        if owns:
            repo.close()


def save_derived_summary(
    *,
    run_id: str,
    summary: Mapping[str, Any],
    repository: AuditRepository | None = None,
    root: Path | None = None,
    filename: str | None = None,
) -> Path:
    """Write a derived summary under the derived/reports tree (never under raw/)."""

    owns = repository is None
    repo = repository or AuditRepository(root=root)
    try:
        return repo.save_derived_summary(
            run_id=run_id,
            summary=redact_secrets(dict(summary)),
            filename=filename,
        )
    finally:
        if owns:
            repo.close()


def observation_for_optimization_run(
    record: OptimizationRunRecord,
) -> RawObservation:
    """Wrap an optimization-run record as a RawObservation for ExperimentStore."""

    from veriforge.experiment_engine import make_observation

    return make_observation(
        run_id=record.run_id,
        kind=ObservationKind.OPTIMIZATION_RUN,
        payload=optimization_run_to_dict(record),
        observation_id=record.run_id,
        recorded_at_utc=record.created_at_utc,
    )


def csv_dumps(rows: Iterable[Mapping[str, Any]]) -> str:
    """Helper used by tests to inspect CSV serialization."""

    materialized = [_flatten_row(row) for row in rows]
    if not materialized:
        return ""
    fieldnames = sorted({key for row in materialized for key in row})
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in materialized:
        writer.writerow(row)
    return buffer.getvalue()


def open_audit_repository(root: Path | None = None) -> AuditRepository:
    """Construct an AuditRepository (caller must close)."""

    return AuditRepository(root=root)


def open_experiment_store(root: Path | None = None) -> ExperimentStore:
    """Construct an ExperimentStore (caller must close)."""

    return ExperimentStore(root=root)
