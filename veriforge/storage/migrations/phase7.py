"""Phase 7 schema additions: optimization runs and audit events."""

from __future__ import annotations

import sqlite3

PHASE7_SCHEMA_VERSION = 7

PHASE7_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at_utc TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS optimization_runs (
    run_id TEXT PRIMARY KEY,
    created_at_utc TEXT NOT NULL,
    software_version TEXT NOT NULL,
    configuration_fingerprint TEXT NOT NULL,
    semantic_mode TEXT NOT NULL,
    bit_width INTEGER,
    correctness_policy TEXT NOT NULL,
    original_input TEXT NOT NULL,
    accepted_source TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    filesystem_path TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY,
    event_kind TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    run_id TEXT,
    configuration_fingerprint TEXT,
    result_ref TEXT,
    software_version TEXT NOT NULL,
    message TEXT,
    detail_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_events_run ON audit_events(run_id);
CREATE INDEX IF NOT EXISTS idx_optimization_runs_fingerprint
    ON optimization_runs(configuration_fingerprint);
"""


def apply_phase7_migrations(connection: sqlite3.Connection) -> None:
    """Apply Phase 7 tables if missing. Idempotent."""

    connection.executescript(PHASE7_SQL)
    cur = connection.execute(
        "SELECT 1 FROM schema_migrations WHERE version = ?",
        (PHASE7_SCHEMA_VERSION,),
    )
    if cur.fetchone() is None:
        from datetime import datetime, timezone

        applied = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        connection.execute(
            """
            INSERT INTO schema_migrations (version, applied_at_utc, description)
            VALUES (?, ?, ?)
            """,
            (
                PHASE7_SCHEMA_VERSION,
                applied,
                "optimization_runs + audit_events + schema_migrations",
            ),
        )
    connection.commit()
