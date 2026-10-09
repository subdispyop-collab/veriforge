"""SQLite store for experiment run metadata; raw payloads stay on the filesystem.

Phase 5 uses a simple schema. Full audit export/replay deepens in Phase 7.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from veriforge.models import (
    BaselineId,
    DatasetPartition,
    ExperimentRun,
    ObservationKind,
    RawObservation,
    SemanticMode,
    TransformationCategory,
    ExpectedOutcome,
    VerificationStatus,
)

DEFAULT_EXPERIMENTS_ROOT = Path(__file__).resolve().parent.parent.parent / "experiments"
DEFAULT_SQLITE_NAME = "experiment_runs.sqlite3"
RAW_DIRNAME = "raw"


def default_experiments_root(root: Path | None = None) -> Path:
    return Path(root) if root is not None else DEFAULT_EXPERIMENTS_ROOT


def default_sqlite_path(*, root: Path | None = None) -> Path:
    return default_experiments_root(root) / DEFAULT_SQLITE_NAME


def raw_observations_dir(*, root: Path | None = None) -> Path:
    return default_experiments_root(root) / RAW_DIRNAME


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS experiment_runs (
    run_id TEXT PRIMARY KEY,
    created_at_utc TEXT NOT NULL,
    protocol_version TEXT NOT NULL,
    software_version TEXT NOT NULL,
    configuration_fingerprint TEXT NOT NULL,
    baseline_id TEXT,
    dataset_version TEXT,
    dataset_partition TEXT,
    random_seed INTEGER,
    semantic_mode TEXT,
    bit_width INTEGER,
    configuration_json TEXT NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS observation_index (
    observation_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    case_id TEXT,
    kind TEXT NOT NULL,
    filesystem_path TEXT NOT NULL,
    recorded_at_utc TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES experiment_runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_observation_run ON observation_index(run_id);
"""


def init_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_SQL)
    connection.commit()


def _run_to_row(run: ExperimentRun) -> tuple[Any, ...]:
    return (
        run.run_id,
        run.created_at_utc,
        run.protocol_version,
        run.software_version,
        run.configuration_fingerprint,
        None if run.baseline_id is None else run.baseline_id.value,
        run.dataset_version,
        None if run.dataset_partition is None else run.dataset_partition.value,
        run.random_seed,
        None if run.semantic_mode is None else run.semantic_mode.value,
        run.bit_width,
        json.dumps(dict(run.configuration), sort_keys=True),
        run.notes,
    )


def _row_to_run(row: sqlite3.Row) -> ExperimentRun:
    return ExperimentRun(
        run_id=row["run_id"],
        created_at_utc=row["created_at_utc"],
        protocol_version=row["protocol_version"],
        software_version=row["software_version"],
        configuration_fingerprint=row["configuration_fingerprint"],
        baseline_id=(
            None
            if row["baseline_id"] is None
            else BaselineId(row["baseline_id"])
        ),
        dataset_version=row["dataset_version"],
        dataset_partition=(
            None
            if row["dataset_partition"] is None
            else DatasetPartition(row["dataset_partition"])
        ),
        random_seed=row["random_seed"],
        semantic_mode=(
            None
            if row["semantic_mode"] is None
            else SemanticMode(row["semantic_mode"])
        ),
        bit_width=row["bit_width"],
        configuration=json.loads(row["configuration_json"]),
        notes=row["notes"],
    )


def observation_to_dict(obs: RawObservation) -> dict[str, Any]:
    return {
        "observation_id": obs.observation_id,
        "run_id": obs.run_id,
        "case_id": obs.case_id,
        "kind": obs.kind.value,
        "transformation_category": (
            None
            if obs.transformation_category is None
            else obs.transformation_category.value
        ),
        "verification_status": (
            None
            if obs.verification_status is None
            else obs.verification_status.value
        ),
        "detected_as_non_equivalent": obs.detected_as_non_equivalent,
        "expected_outcome": (
            None if obs.expected_outcome is None else obs.expected_outcome.value
        ),
        "payload": dict(obs.payload),
        "recorded_at_utc": obs.recorded_at_utc,
    }


def observation_from_dict(data: Mapping[str, Any]) -> RawObservation:
    cat = data.get("transformation_category")
    status = data.get("verification_status")
    expected = data.get("expected_outcome")
    return RawObservation(
        observation_id=str(data["observation_id"]),
        run_id=str(data["run_id"]),
        case_id=None if data.get("case_id") is None else str(data["case_id"]),
        kind=ObservationKind(str(data["kind"])),
        transformation_category=(
            None if cat is None else TransformationCategory(str(cat))
        ),
        verification_status=(
            None if status is None else VerificationStatus(str(status))
        ),
        detected_as_non_equivalent=(
            None
            if data.get("detected_as_non_equivalent") is None
            else bool(data["detected_as_non_equivalent"])
        ),
        expected_outcome=(
            None if expected is None else ExpectedOutcome(str(expected))
        ),
        payload=dict(data.get("payload") or {}),
        recorded_at_utc=str(data["recorded_at_utc"]),
    )


class ExperimentStore:
    """Persist experiment runs (SQLite) and raw observations (filesystem JSON)."""

    def __init__(self, *, root: Path | None = None) -> None:
        self.root = default_experiments_root(root)
        self.sqlite_path = default_sqlite_path(root=self.root)
        self.raw_dir = raw_observations_dir(root=self.root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.sqlite_path)
        self._conn.row_factory = sqlite3.Row
        init_schema(self._conn)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> ExperimentStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def save_run(self, run: ExperimentRun) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO experiment_runs (
                run_id, created_at_utc, protocol_version, software_version,
                configuration_fingerprint, baseline_id, dataset_version,
                dataset_partition, random_seed, semantic_mode, bit_width,
                configuration_json, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _run_to_row(run),
        )
        self._conn.commit()

    def get_run(self, run_id: str) -> ExperimentRun | None:
        cur = self._conn.execute(
            "SELECT * FROM experiment_runs WHERE run_id = ?", (run_id,)
        )
        row = cur.fetchone()
        return None if row is None else _row_to_run(row)

    def list_runs(self) -> tuple[ExperimentRun, ...]:
        cur = self._conn.execute(
            "SELECT * FROM experiment_runs ORDER BY created_at_utc"
        )
        return tuple(_row_to_run(row) for row in cur.fetchall())

    def save_observation(self, observation: RawObservation) -> Path:
        run_dir = self.raw_dir / observation.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / f"{observation.observation_id}.json"
        path.write_text(
            json.dumps(observation_to_dict(observation), indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        rel = str(path.relative_to(self.root))
        self._conn.execute(
            """
            INSERT OR REPLACE INTO observation_index (
                observation_id, run_id, case_id, kind, filesystem_path,
                recorded_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                observation.observation_id,
                observation.run_id,
                observation.case_id,
                observation.kind.value,
                rel,
                observation.recorded_at_utc,
            ),
        )
        self._conn.commit()
        return path

    def load_observations(self, run_id: str) -> tuple[RawObservation, ...]:
        cur = self._conn.execute(
            """
            SELECT filesystem_path FROM observation_index
            WHERE run_id = ?
            ORDER BY recorded_at_utc, observation_id
            """,
            (run_id,),
        )
        observations: list[RawObservation] = []
        for row in cur.fetchall():
            path = self.root / row["filesystem_path"]
            data = json.loads(path.read_text(encoding="utf-8"))
            observations.append(observation_from_dict(data))
        return tuple(observations)
