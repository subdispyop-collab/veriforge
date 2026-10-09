"""Phase 9 adversarial resilience tests (§15 controls).

Covers malformed input, resource limits, unsupported constructs, unexpected
exceptions, controlled export paths, and secret-safe error surfaces.
Does not claim resistance to every attack.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from veriforge.audit_engine import export_audit_records, record_optimization_run
from veriforge.config import SemanticConfiguration
from veriforge.exceptions import (
    AuditError,
    InvalidLiteralError,
    ResourceLimitError,
    UnapprovedASTNodeError,
    UnsupportedSyntaxError,
)
from veriforge.models import ExportFormat, SemanticMode, VerificationStatus
from veriforge.optimizer_engine import optimize
from veriforge.parser_engine import parse_expression
from veriforge.security import ErrorClass, classify_error, user_facing_error
from veriforge.storage import AuditRepository
from veriforge.ui.actions import parse_for_workbench, run_workbench
from veriforge.verifier_engine import verify_equivalence


def mode_a(**limit_changes: int | float) -> SemanticConfiguration:
    config = SemanticConfiguration(mode=SemanticMode.MODE_A)
    if limit_changes:
        return config.with_limits(**limit_changes)
    return config


class TestMalformedAndUnsupportedInput:
    @pytest.mark.parametrize(
        "source",
        [
            "f(x)",
            "__import__('os')",
            "open('/etc/passwd')",
            "exec('x')",
            "eval('1')",
            "x.attr",
            "x.__class__",
            "[x for x in y]",
            "lambda x: x",
            "import sys",
            "x = 1",
            "await x",
            "1 / 0",
            "x ** y",
            "x << 1",
            "'string'",
            "None",
            "True",
            "1.5",
            "{1, 2}",
            "(x, y)",
            "",
            "   ",
            "\x00",
            "x;" * 10,
        ],
    )
    def test_malformed_or_unsupported_fails_closed(self, source: str) -> None:
        with pytest.raises(
            (
                UnsupportedSyntaxError,
                UnapprovedASTNodeError,
                InvalidLiteralError,
                ResourceLimitError,
            )
        ):
            parse_expression(source, mode_a())

    def test_non_string_source_rejected(self) -> None:
        with pytest.raises((UnsupportedSyntaxError, TypeError, Exception)):
            parse_expression(12345, mode_a())  # type: ignore[arg-type]


class TestResourceLimits:
    def test_source_length_limit(self) -> None:
        cfg = mode_a(max_source_length=8)
        with pytest.raises(ResourceLimitError) as exc_info:
            parse_expression("x + y + z", cfg)
        assert classify_error(exc_info.value) is ErrorClass.RESOURCE_LIMIT

    def test_ast_node_limit(self) -> None:
        cfg = mode_a(max_ast_nodes=3)
        with pytest.raises(ResourceLimitError):
            parse_expression("x + y", cfg)

    def test_nesting_depth_limit(self) -> None:
        cfg = mode_a(max_nesting_depth=2)
        with pytest.raises(ResourceLimitError):
            parse_expression("((x + 1) + 1)", cfg)

    def test_mode_a_literal_bit_length_limit(self) -> None:
        cfg = mode_a(max_mode_a_literal_bit_length=8)
        with pytest.raises(InvalidLiteralError):
            parse_expression(str(2**10), cfg)

    def test_solver_timeout_applied_on_verification(self) -> None:
        z3 = pytest.importorskip("z3")  # noqa: F841
        cfg = mode_a(solver_timeout_seconds=0.001)
        # Even fast instances must carry the configured timeout on the result.
        result = verify_equivalence("x + 0", "x", cfg)
        assert result.timeout_seconds == pytest.approx(0.001)
        assert result.status in {
            VerificationStatus.EQUIVALENT_WITHIN_MODEL,
            VerificationStatus.TIMEOUT,
            VerificationStatus.UNKNOWN,
            VerificationStatus.COUNTEREXAMPLE_FOUND,
        }


class TestUnexpectedExceptionsAndClassification:
    def test_ui_surfaces_classified_parse_errors(self) -> None:
        outcome = parse_for_workbench("f(x)", mode_a())
        assert outcome.ok is False
        assert outcome.error is not None
        assert outcome.error.startswith("[")
        assert "Traceback" not in outcome.error

    def test_ui_workbench_rejects_unsupported_without_secret_leak(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        z3 = pytest.importorskip("z3")  # noqa: F841

        def boom(*_a: object, **_k: object) -> object:
            raise RuntimeError("password=supersecret api_key=leakme")

        monkeypatch.setattr(
            "veriforge.ui.actions.optimize", boom
        )
        result = run_workbench("x + 0", mode_a())
        assert result.error is not None
        assert "supersecret" not in result.error
        assert "leakme" not in result.error
        assert result.error.startswith("[unexpected]")


class TestNoArbitraryCodeExecution:
    def test_parser_does_not_call_eval_exec(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import builtins

        def boom(*_a: object, **_k: object) -> object:
            raise AssertionError("eval/exec must not run on user input")

        monkeypatch.setattr(builtins, "eval", boom)
        monkeypatch.setattr(builtins, "exec", boom)
        parse_expression("(x + 1) * 2", mode_a())


class TestControlledExportPaths:
    def test_export_default_stays_under_exports(
        self, tmp_path: Path
    ) -> None:
        z3 = pytest.importorskip("z3")  # noqa: F841
        result = optimize("x + 0", mode_a())
        with AuditRepository(root=tmp_path) as repo:
            record, _ = record_optimization_run(result, repository=repo)
            exported = export_audit_records(
                format=ExportFormat.JSON,
                run_ids=[record.run_id],
                repository=repo,
            )
            path = Path(exported.filesystem_path).resolve()
            assert path.is_relative_to(repo.exports_dir.resolve())

    def test_export_rejects_path_escape(self, tmp_path: Path) -> None:
        z3 = pytest.importorskip("z3")  # noqa: F841
        result = optimize("x + 0", mode_a())
        with AuditRepository(root=tmp_path) as repo:
            record, _ = record_optimization_run(result, repository=repo)
            with pytest.raises(AuditError, match="escapes|unsafe"):
                export_audit_records(
                    format=ExportFormat.JSON,
                    run_ids=[record.run_id],
                    repository=repo,
                    destination=tmp_path / ".." / "escape.json",
                )

    def test_derived_summary_rejects_traversal(self, tmp_path: Path) -> None:
        with AuditRepository(root=tmp_path) as repo:
            with pytest.raises(ValueError, match="unsafe"):
                repo.save_derived_summary(
                    run_id="../escape",
                    summary={"ok": 1},
                )
            with pytest.raises(ValueError, match="unsafe"):
                repo.save_derived_summary(
                    run_id="ok-run",
                    summary={"ok": 1},
                    filename="../escape.json",
                )


class TestSecretSafeMessages:
    def test_user_facing_error_never_embeds_private_key_blob(self) -> None:
        blob = "-----BEGIN PRIVATE KEY-----\nABCDEF\n-----END PRIVATE KEY-----"
        text = user_facing_error(ResourceLimitError(blob))
        assert "BEGIN PRIVATE KEY" not in text
        assert "[REDACTED]" in text or "private" not in text.lower()
