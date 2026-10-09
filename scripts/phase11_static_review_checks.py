#!/usr/bin/env python3
"""Phase 11 static review checks that do not require Z3.

Loads parser/semantics/reference-evaluator modules without importing the
package ``__init__`` (which pulls ``z3`` via the benchmark engine).

Exit 0 on success. Does **not** claim SMT equivalence or held-out findings.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_leaf_modules() -> None:
    pkg = types.ModuleType("veriforge")
    pkg.__path__ = [str(ROOT / "veriforge")]
    sys.modules["veriforge"] = pkg
    for name in (
        "veriforge.exceptions",
        "veriforge.models",
        "veriforge.config",
        "veriforge.semantics",
        "veriforge.parser_engine",
        "veriforge.reference_evaluator",
    ):
        path = ROOT / (name.replace(".", "/") + ".py")
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)


def main() -> int:
    _load_leaf_modules()
    from veriforge.config import SemanticConfiguration
    from veriforge.exceptions import InvalidLiteralError
    from veriforge.models import SemanticMode
    from veriforge.parser_engine import parse_expression
    from veriforge.reference_evaluator import evaluate

    failures: list[str] = []

    def mode_a() -> SemanticConfiguration:
        return SemanticConfiguration(mode=SemanticMode.MODE_A)

    def mode_b(width: int = 32) -> SemanticConfiguration:
        return SemanticConfiguration(mode=SemanticMode.MODE_B, bit_width=width)

    cfg = mode_a()
    for x in (-5, 0, 1, 100):
        o = evaluate(parse_expression("x + 1", cfg), {"x": x}, cfg)
        c = evaluate(parse_expression("x + 2", cfg), {"x": x}, cfg)
        if o == c:
            failures.append(f"mode_a inequivalence failed at x={x}")

    if evaluate(parse_expression("1 + 1", cfg), {}, cfg) != 2:
        failures.append("constant 1+1")
    if evaluate(parse_expression("3", cfg), {}, cfg) != 3:
        failures.append("constant 3")

    cfg4 = mode_b(4)
    for x in range(16):
        o = evaluate(parse_expression("x + 1", cfg4), {"x": x}, cfg4)
        c = evaluate(parse_expression("x", cfg4), {"x": x}, cfg4)
        if o != (x + 1) % 16 or o == c:
            failures.append(f"mode_b wrap at x={x}")

    cfg8 = mode_b(8)
    if evaluate(parse_expression("-1", cfg8), {}, cfg8) != 255:
        failures.append("mode_b unary minus")
    for x in range(0, 256, 17):
        o = evaluate(parse_expression("(x + 200) + 100", cfg8), {"x": x}, cfg8)
        c = evaluate(parse_expression("x + 44", cfg8), {"x": x}, cfg8)
        if o != c:
            failures.append(f"mode_b modular add at x={x}")

    if evaluate(parse_expression("255 + 1", cfg), {}, cfg) != 256:
        failures.append("mode_a no wrap")
    if evaluate(parse_expression("255 + 1", cfg8), {}, cfg8) != 0:
        failures.append("mode_b wrap 255+1")

    for src, dst in (("x + 0", "x"), ("x - 0", "x"), ("x * 1", "x"), ("x * 0", "0")):
        for cfg_i, domain in ((mode_a(), (-3, 0, 7)), (mode_b(8), (0, 1, 127, 255))):
            for x in domain:
                o = evaluate(parse_expression(src, cfg_i), {"x": x}, cfg_i)
                c = evaluate(parse_expression(dst, cfg_i), {"x": x}, cfg_i)
                if o != c:
                    failures.append(f"identity {src}->{dst} mode={cfg_i.mode} x={x}")

    if evaluate(parse_expression("x + y", cfg), {"x": 3, "y": 1}, cfg) == evaluate(
        parse_expression("x - y", cfg), {"x": 3, "y": 1}, cfg
    ):
        failures.append("mutation x+y vs x-y")

    try:
        parse_expression("256", cfg8)
        failures.append("Mode B literal 256 should reject")
    except InvalidLiteralError:
        pass

    # Held-out seed expected outcomes at reference level (not SMT).
    held = [
        ("p + 0", "p", "mode_a", None, "eq", {"p": 1}),
        ("q * 1", "q", "mode_a", None, "eq", {"q": 2}),
        ("m + 3", "m + 5", "mode_a", None, "neq", {"m": 7}),
        ("u - v", "v - u", "mode_a", None, "neq", {"u": 5, "v": 2}),
        ("65535 + 1", "0", "mode_b", 16, "eq", {}),
        ("((r * 1) - 0) + s", "r + s", "mode_a", None, "eq", {"r": 3, "s": 4}),
        ("t - 0", "t", "mode_b", 32, "eq", {"t": 9}),
    ]
    for orig, cand, mode, width, expect, assign in held:
        cfg_h = mode_a() if mode == "mode_a" else mode_b(int(width))
        o = evaluate(parse_expression(orig, cfg_h), assign, cfg_h)
        c = evaluate(parse_expression(cand, cfg_h), assign, cfg_h)
        if expect == "eq" and o != c:
            failures.append(f"held eq fail {orig}")
        if expect == "neq" and o == c:
            failures.append(f"held neq fail {orig}")

    try:
        parse_expression("import os", mode_a())
        failures.append("import should reject")
    except Exception as exc:  # noqa: BLE001 — any rejection is success here
        print(f"import rejected as {type(exc).__name__}")

    # Cross-check Phase 10 report wording vs ledger discipline (no upgrades).
    report_path = ROOT / "experiments/reports/phase10-held-out-evaluation.json"
    if report_path.is_file():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if not report.get("dependency_available"):
            print("NOTE: held-out report dependency_available is false")
        hs = report.get("hypothesis_status") or {}
        h1 = hs.get("H1_verification_detects_incorrect", "")
        h2 = hs.get("H2_verification_introduces_overhead", "")
        h3 = hs.get("H3_varies_by_complexity_and_category", "")
        print("report H1:", h1)
        print("report H2:", h2)
        print("report H3:", h3)
        novelty = report.get("novelty_claim") or ""
        if "no novelty" not in novelty.lower():
            failures.append("report must keep no-novelty claim")
        if "supported_on_this_sample" not in h1:
            failures.append("unexpected H1 status vs warm-host tip")
        if "supported_on_this_sample" not in h2:
            failures.append("unexpected H2 status vs warm-host tip")
        if "inconclusive_on_this_sample" not in h3:
            failures.append("unexpected H3 status vs warm-host tip")

    print(f"FAILURES: {len(failures)}")
    for item in failures:
        print(item)
    if failures:
        return 1
    print("STATUS: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
