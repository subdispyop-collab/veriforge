"""Unit tests for Phase 9 security helpers (§15)."""

from __future__ import annotations

from pathlib import Path

import pytest

from veriforge.exceptions import (
    AuditError,
    ParseError,
    ResourceLimitError,
    UnsupportedSyntaxError,
    VeriforgeError,
)
from veriforge.security import (
    ErrorClass,
    classify_error,
    controlled_export_path,
    dependency_review_snapshot,
    is_safe_relative_name,
    resolve_under_root,
    sanitize_error_text,
    user_facing_error,
)


def test_classify_error_hierarchy() -> None:
    assert classify_error(ResourceLimitError("x")) is ErrorClass.RESOURCE_LIMIT
    assert classify_error(UnsupportedSyntaxError("x")) is ErrorClass.UNSUPPORTED_SYNTAX
    assert classify_error(ParseError("x")) is ErrorClass.INVALID_INPUT
    assert classify_error(VeriforgeError("x")) is ErrorClass.UNEXPECTED
    assert classify_error(RuntimeError("boom")) is ErrorClass.UNEXPECTED


def test_user_facing_error_redacts_secrets_and_avoids_traceback() -> None:
    message = user_facing_error(
        ResourceLimitError("source length 9999 exceeds limit 4096 api_key=sekrit")
    )
    assert "api_key" not in message.lower() or "[REDACTED]" in message
    assert "sekrit" not in message
    assert message.startswith("[resource_limit]")

    unexpected = user_facing_error(RuntimeError("password=hunter2 /home/secret"))
    assert unexpected.startswith("[unexpected]")
    assert "hunter2" not in unexpected
    assert "Traceback" not in unexpected


def test_sanitize_error_text_truncates() -> None:
    long = "a" * 1000
    cleaned = sanitize_error_text(long, max_length=50)
    assert len(cleaned) <= 50
    assert cleaned.endswith("...")


def test_is_safe_relative_name() -> None:
    assert is_safe_relative_name("audit_export.json")
    assert is_safe_relative_name("summary.json")
    assert not is_safe_relative_name("../etc/passwd")
    assert not is_safe_relative_name("a/b")
    assert not is_safe_relative_name(".hidden")
    assert not is_safe_relative_name("")
    assert not is_safe_relative_name("..")


def test_resolve_under_root_rejects_escape(tmp_path: Path) -> None:
    root = tmp_path / "exports"
    root.mkdir()
    inside = resolve_under_root(root, "ok.json")
    assert inside.parent == root.resolve()
    with pytest.raises(AuditError, match="escapes"):
        resolve_under_root(root, tmp_path / "outside.json")
    with pytest.raises(AuditError, match="escapes"):
        resolve_under_root(root, "../escape.json")


def test_controlled_export_path(tmp_path: Path) -> None:
    exports = tmp_path / "exports"
    path = controlled_export_path(exports_root=exports, filename="out.json")
    assert path == (exports / "out.json").resolve()
    nested = controlled_export_path(
        exports_root=exports, destination=exports / "nested" / "out.json"
    )
    assert nested.is_relative_to(exports.resolve())
    with pytest.raises(AuditError):
        controlled_export_path(exports_root=exports, filename="../x.json")
    with pytest.raises(AuditError):
        controlled_export_path(
            exports_root=exports, destination=tmp_path / "escape.json"
        )


def test_dependency_review_snapshot_matches_locked_pins() -> None:
    snap = dependency_review_snapshot()
    assert snap["z3-solver"] == "5.1.0.0"
    assert snap["streamlit"] == "1.41.1"
    assert snap["plotly"] == "5.24.1"
    assert snap["pandas"] == "2.2.3"
    assert snap["pytest"] == "9.1.1"
    assert snap["hypothesis"] == "6.168.5"
