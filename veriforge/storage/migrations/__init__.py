"""Schema migrations for VERIFORGE storage.

Phase 5 created the base experiment_runs / observation_index schema.
Phase 7 adds optimization_runs and audit_events tables via
``apply_phase7_migrations``.
"""

from veriforge.storage.migrations.phase7 import (
    PHASE7_SCHEMA_VERSION,
    apply_phase7_migrations,
)

__all__ = [
    "PHASE7_SCHEMA_VERSION",
    "apply_phase7_migrations",
]
