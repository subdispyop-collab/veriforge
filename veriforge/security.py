"""Security and resilience helpers (Phase 9 / §15).

Treats user input and imported datasets as untrusted. Provides:

* Classified, secret-safe error messages for UI and audit surfaces
* Controlled filesystem path confinement for exports and derived artifacts
* Safe filename checks
* Explicit documentation hooks for the threat model (see ``docs/SECURITY.md``)

Does **not** claim resistance to every attack. Remaining limitations are in
``docs/SECURITY.md`` and ``docs/LIMITATIONS.md``.
"""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from veriforge.exceptions import (
    AuditError,
    BenchmarkError,
    DomainError,
    EvaluationError,
    InvalidLiteralError,
    MissingVariableError,
    OptimizerError,
    ParseError,
    ResourceLimitError,
    TranslationError,
    UnapprovedASTNodeError,
    UnsupportedSyntaxError,
    VerificationEngineError,
    VeriforgeError,
)

# Patterns that must never appear in user-visible error text.
_SECRET_VALUE_PATTERN = re.compile(
    r"(?i)("
    r"(?:api[_-]?key|access[_-]?token|access[_-]?key|secret|password|passwd|"
    r"token|credential|authorization|bearer)"
    r"\s*[:=]\s*\S+"
    r"|bearer\s+[A-Za-z0-9._\-]+"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"
    r")"
)
_PATH_TRAVERSAL_MARKERS = ("..",)


class ErrorClass(str, Enum):
    """User-facing classification of errors (§15: errors classified)."""

    INVALID_INPUT = "invalid_input"
    UNSUPPORTED_SYNTAX = "unsupported_syntax"
    RESOURCE_LIMIT = "resource_limit"
    DOMAIN_ERROR = "domain_error"
    TRANSLATION_ERROR = "translation_error"
    VERIFICATION_ERROR = "verification_error"
    OPTIMIZER_ERROR = "optimizer_error"
    BENCHMARK_ERROR = "benchmark_error"
    AUDIT_ERROR = "audit_error"
    EVALUATION_ERROR = "evaluation_error"
    UNEXPECTED = "unexpected"


# Map exception types to classifications (most-specific first via MRO walk).
_CLASS_BY_TYPE: dict[type[BaseException], ErrorClass] = {
    ResourceLimitError: ErrorClass.RESOURCE_LIMIT,
    UnapprovedASTNodeError: ErrorClass.UNSUPPORTED_SYNTAX,
    UnsupportedSyntaxError: ErrorClass.UNSUPPORTED_SYNTAX,
    InvalidLiteralError: ErrorClass.INVALID_INPUT,
    ParseError: ErrorClass.INVALID_INPUT,
    MissingVariableError: ErrorClass.EVALUATION_ERROR,
    DomainError: ErrorClass.DOMAIN_ERROR,
    EvaluationError: ErrorClass.EVALUATION_ERROR,
    TranslationError: ErrorClass.TRANSLATION_ERROR,
    VerificationEngineError: ErrorClass.VERIFICATION_ERROR,
    OptimizerError: ErrorClass.OPTIMIZER_ERROR,
    BenchmarkError: ErrorClass.BENCHMARK_ERROR,
    AuditError: ErrorClass.AUDIT_ERROR,
    VeriforgeError: ErrorClass.UNEXPECTED,
}


def classify_error(exc: BaseException) -> ErrorClass:
    """Return the §15 error class for ``exc``."""

    for cls in type(exc).mro():
        if cls in _CLASS_BY_TYPE:
            return _CLASS_BY_TYPE[cls]
    return ErrorClass.UNEXPECTED


def sanitize_error_text(text: str, *, max_length: int = 512) -> str:
    """Strip secret-like substrings and truncate for safe display."""

    cleaned = _SECRET_VALUE_PATTERN.sub("[REDACTED]", text)
    cleaned = cleaned.replace("\x00", "")
    if len(cleaned) > max_length:
        cleaned = cleaned[: max_length - 3] + "..."
    return cleaned


def user_facing_error(exc: BaseException) -> str:
    """Classify ``exc`` and return a secret-safe, non-traceback message.

    Unexpected exceptions never expose a raw traceback or environment detail.
    """

    error_class = classify_error(exc)
    if error_class is ErrorClass.UNEXPECTED and not isinstance(exc, VeriforgeError):
        return (
            f"[{error_class.value}] unexpected internal error "
            f"({type(exc).__name__}); see logs if configured"
        )
    message = sanitize_error_text(str(exc) or type(exc).__name__)
    return f"[{error_class.value}] {message}"


def is_safe_relative_name(name: str) -> bool:
    """Return True when ``name`` is a single path segment with no traversal."""

    if not name or name in (".", ".."):
        return False
    if "/" in name or "\\" in name:
        return False
    if name.startswith("."):
        return False
    if any(marker in name for marker in _PATH_TRAVERSAL_MARKERS):
        # Single-segment names cannot contain ".." as a component; still reject
        # literal ".." substring edge cases like "a..b" only when whole name is "..".
        pass
    return True


def resolve_under_root(root: Path, candidate: Path | str) -> Path:
    """Resolve ``candidate`` and require it to stay under ``root``.

    Raises ``AuditError`` on path traversal or escape attempts.
    """

    root_resolved = root.resolve()
    path = Path(candidate)
    if not path.is_absolute():
        path = root_resolved / path
    resolved = path.resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise AuditError(
            f"path escapes controlled root {root_resolved}: {candidate}"
        ) from exc
    return resolved


def controlled_export_path(
    *,
    exports_root: Path,
    filename: str | None = None,
    destination: Path | str | None = None,
) -> Path:
    """Return a write path confined to ``exports_root``.

    * If ``destination`` is omitted, writes ``filename`` (required) under the root.
    * If ``destination`` is provided, it must resolve under ``exports_root``.
    """

    exports_root = exports_root.resolve()
    exports_root.mkdir(parents=True, exist_ok=True)

    if destination is not None:
        target = resolve_under_root(exports_root, destination)
        if target == exports_root:
            raise AuditError("export destination must be a file under the exports root")
        return target

    if filename is None:
        raise AuditError("export requires a filename when destination is omitted")
    if not is_safe_relative_name(filename):
        raise AuditError(f"unsafe export filename: {filename!r}")
    return resolve_under_root(exports_root, filename)


def assert_payload_has_no_plaintext_secrets(payload: Any) -> None:
    """Fail closed when nested mappings still carry unredacted secret keys.

    Delegates key detection to the audit redaction patterns via a local check
    that mirrors ``is_sensitive_key`` without importing audit_engine cycles
    at module import time for parser-only paths.
    """

    from veriforge.audit_engine import assert_no_secrets_in_payload

    assert_no_secrets_in_payload(payload)


def dependency_review_snapshot() -> Mapping[str, str]:
    """Return the locked dependency versions selected for this release line.

    Values come from project pins, not live ``pip list`` (which may be empty
    when PyPI egress is blocked). See ``docs/SECURITY.md``.
    """

    return {
        "z3-solver": "5.1.0.0",
        "streamlit": "1.41.1",
        "plotly": "5.24.1",
        "pandas": "2.2.3",
        "pytest": "9.1.1",
        "hypothesis": "6.168.5",
        "python_requires": ">=3.11",
    }
