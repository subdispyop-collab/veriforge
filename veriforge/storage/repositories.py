"""Repository facade over SQLite + filesystem storage (Phase 7).

Raw experimental and optimization records live under ``experiments/raw/``.
Derived charts and summaries live under ``experiments/reports/`` (derived).
Exports live under ``experiments/exports/``. Secrets must be redacted before
calling these methods.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from veriforge.models import (
    AuditEvent,
    OptimizationRunRecord,
)
from veriforge.storage.database import (
    ExperimentStore,
    default_experiments_root,
    init_schema,
)
from veriforge.storage.migrations.phase7 import apply_phase7_migrations

OPTIMIZATION_RUNS_DIRNAME = "optimization_runs"
EXPORTS_DIRNAME = "exports"
DERIVED_DIRNAME = "reports"


class AuditRepository:
    """Persist optimization runs, audit events, and derived summaries."""

    def __init__(self, *, root: Path | None = None) -> None:
        self.root = default_experiments_root(root)
        self.store = ExperimentStore(root=self.root)
        self.raw_dir = self.store.raw_dir
        self.derived_dir = self.root / DERIVED_DIRNAME
        self.exports_dir = self.root / EXPORTS_DIRNAME
        self.optimization_runs_dir = self.raw_dir / OPTIMIZATION_RUNS_DIRNAME
        self.derived_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.optimization_runs_dir.mkdir(parents=True, exist_ok=True)
        apply_phase7_migrations(self.store._conn)

    def close(self) -> None:
        self.store.close()

    def __enter__(self) -> AuditRepository:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @property
    def connection(self) -> sqlite3.Connection:
        return self.store._conn

    def optimization_run_relative_path(self, run_id: str) -> str:
        """Path relative to the experiments root (includes ``raw/``)."""

        return str(
            Path(self.raw_dir.name)
            / OPTIMIZATION_RUNS_DIRNAME
            / run_id
            / "optimization_run.json"
        )

    def optimization_run_path(self, run_id: str) -> Path:
        return self.root / self.optimization_run_relative_path(run_id)

    def save_optimization_run(self, record: OptimizationRunRecord) -> str:
        """Write the raw optimization-run JSON and index it in SQLite.

        Returns a result_ref relative to the experiments root (via raw/).
        """

        from veriforge.audit_engine import optimization_run_to_dict

        path = self.optimization_run_path(record.run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = optimization_run_to_dict(record)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        # Index path relative to experiments root for stable refs.
        rel_from_root = str(path.relative_to(self.root))
        self.connection.execute(
            """
            INSERT OR REPLACE INTO optimization_runs (
                run_id, created_at_utc, software_version,
                configuration_fingerprint, semantic_mode, bit_width,
                correctness_policy, original_input, accepted_source,
                content_sha256, filesystem_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.run_id,
                record.created_at_utc,
                record.software_version,
                record.configuration_fingerprint,
                record.semantic_mode.value,
                record.bit_width,
                record.correctness_policy,
                record.original_input,
                record.accepted_source,
                record.content_sha256,
                rel_from_root,
            ),
        )
        self.connection.commit()
        return rel_from_root

    def get_optimization_run(self, run_id: str) -> OptimizationRunRecord | None:
        from veriforge.audit_engine import optimization_run_from_dict

        cur = self.connection.execute(
            "SELECT filesystem_path FROM optimization_runs WHERE run_id = ?",
            (run_id,),
        )
        row = cur.fetchone()
        if row is None:
            path = self.optimization_run_path(run_id)
            if not path.exists():
                return None
            data = json.loads(path.read_text(encoding="utf-8"))
            return optimization_run_from_dict(data)
        path = self.root / row["filesystem_path"]
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return optimization_run_from_dict(data)

    def list_optimization_runs(self) -> tuple[OptimizationRunRecord, ...]:
        cur = self.connection.execute(
            "SELECT run_id FROM optimization_runs ORDER BY created_at_utc"
        )
        runs: list[OptimizationRunRecord] = []
        for row in cur.fetchall():
            record = self.get_optimization_run(row["run_id"])
            if record is not None:
                runs.append(record)
        return tuple(runs)

    def save_audit_event(self, event: AuditEvent) -> None:
        from veriforge.audit_engine import audit_event_to_dict

        detail = dict(audit_event_to_dict(event)["detail"])
        self.connection.execute(
            """
            INSERT OR REPLACE INTO audit_events (
                event_id, event_kind, created_at_utc, run_id,
                configuration_fingerprint, result_ref, software_version,
                message, detail_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.event_kind.value,
                event.created_at_utc,
                event.run_id,
                event.configuration_fingerprint,
                event.result_ref,
                event.software_version,
                event.message,
                json.dumps(detail, sort_keys=True),
            ),
        )
        self.connection.commit()

    def list_audit_events(
        self,
        *,
        run_ids: Sequence[str] | None = None,
    ) -> tuple[AuditEvent, ...]:
        from veriforge.audit_engine import audit_event_from_dict

        if run_ids is None:
            cur = self.connection.execute(
                "SELECT * FROM audit_events ORDER BY created_at_utc, event_id"
            )
        else:
            if not run_ids:
                return ()
            placeholders = ",".join("?" for _ in run_ids)
            cur = self.connection.execute(
                f"""
                SELECT * FROM audit_events
                WHERE run_id IN ({placeholders})
                ORDER BY created_at_utc, event_id
                """,
                tuple(run_ids),
            )
        events: list[AuditEvent] = []
        for row in cur.fetchall():
            events.append(
                audit_event_from_dict(
                    {
                        "event_id": row["event_id"],
                        "event_kind": row["event_kind"],
                        "created_at_utc": row["created_at_utc"],
                        "run_id": row["run_id"],
                        "configuration_fingerprint": row[
                            "configuration_fingerprint"
                        ],
                        "result_ref": row["result_ref"],
                        "software_version": row["software_version"],
                        "message": row["message"],
                        "detail": json.loads(row["detail_json"]),
                    }
                )
            )
        return tuple(events)

    def list_run_history(self) -> tuple[dict[str, Any], ...]:
        """Combined history of experiment and optimization runs."""

        rows: list[dict[str, Any]] = []
        for run in self.store.list_runs():
            rows.append(
                {
                    "kind": "experiment_run",
                    "run_id": run.run_id,
                    "created_at_utc": run.created_at_utc,
                    "configuration_fingerprint": run.configuration_fingerprint,
                    "software_version": run.software_version,
                    "protocol_version": run.protocol_version,
                    "notes": run.notes,
                }
            )
        for record in self.list_optimization_runs():
            rows.append(
                {
                    "kind": "optimization_run",
                    "run_id": record.run_id,
                    "created_at_utc": record.created_at_utc,
                    "configuration_fingerprint": record.configuration_fingerprint,
                    "software_version": record.software_version,
                    "original_input": record.original_input,
                    "accepted_source": record.accepted_source,
                    "result_ref": self.optimization_run_relative_path(
                        record.run_id
                    ),
                }
            )
        rows.sort(key=lambda item: item["created_at_utc"], reverse=True)
        return tuple(rows)

    def save_derived_summary(
        self,
        *,
        run_id: str,
        summary: Mapping[str, Any],
        filename: str | None = None,
    ) -> Path:
        """Persist a derived summary under reports/, never under raw/."""

        from veriforge.security import is_safe_relative_name, resolve_under_root

        # §15: run_id and filename must be single safe segments (no traversal).
        if not is_safe_relative_name(run_id):
            raise ValueError(f"unsafe derived summary run_id: {run_id!r}")
        run_dir = self.derived_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        name = filename or "summary.json"
        if not is_safe_relative_name(name):
            raise ValueError(f"unsafe derived summary filename: {name!r}")
        path = resolve_under_root(self.derived_dir, run_dir / name)
        # Guard: refuse writing into the raw tree.
        if self.raw_dir.resolve() in path.parents or path == self.raw_dir.resolve():
            raise ValueError("refusing to write derived summary under raw/")
        path.write_text(
            json.dumps(dict(summary), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path

    def ensure_schema(self) -> None:
        init_schema(self.connection)
        apply_phase7_migrations(self.connection)
