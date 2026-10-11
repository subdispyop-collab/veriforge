#!/usr/bin/env python3
"""Run CVC5 and Bitwuzla on the frozen 463-pair set.

Same pairs, recorded mode and width, and 5s timeout as the production Z3
census. Counterexamples are counted only after the reference evaluator
confirms them. Bitwuzla has no integer sort; Mode A queries are still
submitted and the solver's own error is recorded.
"""

from __future__ import annotations

import json
import platform
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CASES = ROOT / "datasets" / "assurance_v1" / "cases.jsonl"
OUT_DIR = ROOT / "experiments" / "reports" / "assurance-v1-smt"
LOADER = Path("/home/ubuntu/solvers/usr/lib64/ld-linux-x86-64.so.2")
LIB = ":".join(
    [
        "/home/ubuntu/solvers/usr/lib/x86_64-linux-gnu",
        "/home/ubuntu/solvers/lib/x86_64-linux-gnu",
        "/home/ubuntu/solvers/usr/lib64",
    ]
)
SOLVERS = {
    "cvc5": {
        "binary": "/home/ubuntu/solvers/usr/bin/cvc5",
        "args": ["-m", "--tlimit-per=5000"],
    },
    "bitwuzla": {
        "binary": "/home/ubuntu/solvers/usr/bin/bitwuzla",
        "args": ["-m", "--time-limit-per=5000"],
    },
}

_MODEL_FUN = re.compile(
    r"\(define-fun\s+\|?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\|?\s+\(\)\s+"
    r"(?P<sort>Int|\(_\s+BitVec\s+\d+\))\s+(?P<value>[^)]+)\)",
    re.DOTALL,
)


def _run(binary: str, args: list[str], text: str | None = None) -> subprocess.CompletedProcess[str]:
    cmd = [str(LOADER), "--library-path", LIB, binary, *args]
    return subprocess.run(
        cmd,
        input=text,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


def _version(binary: str) -> str:
    completed = _run(binary, ["--version"])
    text = (completed.stdout or "") + (completed.stderr or "")
    line = next((row.strip() for row in text.splitlines() if row.strip()), "")
    return line


def _smt_term(node, mode_b: bool, width: int) -> str:
    from veriforge.models import BinaryOp, BinaryOperator, IntLiteral, UnaryOp, UnaryOperator, Variable

    if isinstance(node, IntLiteral):
        if mode_b:
            return f"(_ bv{node.value} {width})"
        return str(node.value)
    if isinstance(node, Variable):
        return f"|{node.name}|"
    if isinstance(node, UnaryOp):
        inner = _smt_term(node.operand, mode_b, width)
        if node.op is UnaryOperator.PLUS:
            return inner
        if node.op is UnaryOperator.MINUS:
            return f"(bvneg {inner})" if mode_b else f"(- {inner})"
        raise ValueError(node.op)
    if isinstance(node, BinaryOp):
        left = _smt_term(node.left, mode_b, width)
        right = _smt_term(node.right, mode_b, width)
        if mode_b:
            table = {
                BinaryOperator.ADD: "bvadd",
                BinaryOperator.SUB: "bvsub",
                BinaryOperator.MUL: "bvmul",
            }
        else:
            table = {
                BinaryOperator.ADD: "+",
                BinaryOperator.SUB: "-",
                BinaryOperator.MUL: "*",
            }
        return f"({table[node.op]} {left} {right})"
    raise ValueError(type(node).__name__)


def _script(original, candidate, mode_b: bool, width: int) -> str:
    names = sorted(set(original.variables) | set(candidate.variables))
    if mode_b:
        logic = "QF_BV"
        sort = f"(_ BitVec {width})"
    else:
        logic = "QF_NIA"
        sort = "Int"
    lines = [
        "(set-option :produce-models true)",
        f"(set-logic {logic})",
    ]
    for name in names:
        lines.append(f"(declare-fun |{name}| () {sort})")
    left = _smt_term(original.root, mode_b, width)
    right = _smt_term(candidate.root, mode_b, width)
    lines.append(f"(assert (distinct {left} {right}))")
    lines.append("(check-sat)")
    lines.append("(get-model)")
    return "\n".join(lines) + "\n"


def _parse_value(raw: str, mode_b: bool, width: int) -> int:
    text = " ".join(raw.split())
    if text.startswith("(-"):
        inner = text[2:].strip().rstrip(")")
        return -int(inner)
    if text.startswith("#b"):
        return int(text[2:], 2)
    if text.startswith("#x"):
        return int(text[2:], 16)
    if text.startswith("(_ bv"):
        parts = text.replace("(", " ").replace(")", " ").split()
        return int(parts[2])
    return int(text)


def _parse_model(text: str, mode_b: bool, width: int) -> dict[str, int]:
    found: dict[str, int] = {}
    for match in _MODEL_FUN.finditer(text):
        found[match.group("name")] = _parse_value(match.group("value"), mode_b, width)
    return found


def _classify_solver(stdout: str, stderr: str, returncode: int) -> tuple[str, str]:
    combined = f"{stdout}\n{stderr}"
    lowered = combined.lower()
    first = next((line.strip() for line in stdout.splitlines() if line.strip()), "")
    if first == "unsat":
        return "unsat", first
    if first == "sat":
        return "sat", first
    if "timeout" in lowered or "interrupted" in lowered or "time limit" in lowered:
        return "timeout", first or "timeout"
    if first == "unknown":
        return "unknown", first
    if returncode != 0 or "[error]" in lowered or "(error" in lowered:
        detail = next((line.strip() for line in combined.splitlines() if "error" in line.lower()), first)
        return "solver_error", detail[:500]
    return "unknown", first or "empty solver output"


def _count(rows: list[dict]) -> dict[str, int]:
    return dict(sorted(Counter(row["status"] for row in rows).items()))


def main() -> int:
    from veriforge.config import SemanticConfiguration
    from veriforge.exceptions import (
        InvalidLiteralError,
        ParseError,
        ResourceLimitError,
        UnapprovedASTNodeError,
        UnsupportedSyntaxError,
    )
    from veriforge.models import SemanticMode
    from veriforge.parser_engine import parse_expression
    from veriforge.reference_evaluator import evaluate

    cases = [
        json.loads(line)
        for line in CASES.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(cases) != 463:
        raise SystemExit(f"expected 463 pairs, found {len(cases)}")

    versions = {name: _version(spec["binary"]) for name, spec in SOLVERS.items()}
    rows: list[dict] = []
    started = time.perf_counter()
    for case in cases:
        mode_b = case["semantic_mode"] == "mode_b"
        mode = SemanticMode.MODE_B if mode_b else SemanticMode.MODE_A
        width = case["bit_width"] or 32
        config = SemanticConfiguration(mode=mode, bit_width=width)
        parsed_status = None
        reason = None
        original = candidate = None
        try:
            original = parse_expression(case["original_source"], config)
            candidate = parse_expression(case["candidate_source"], config)
        except (UnsupportedSyntaxError, UnapprovedASTNodeError) as exc:
            parsed_status = "unsupported"
            reason = str(exc)
        except (ResourceLimitError, InvalidLiteralError, ParseError) as exc:
            parsed_status = "invalid_input"
            reason = str(exc)
        script = None
        if parsed_status is None:
            script = _script(original, candidate, mode_b, width)
        for solver_name, spec in SOLVERS.items():
            row = {
                "case_id": case["case_id"],
                "solver": solver_name,
                "partition": case["partition"],
                "semantic_mode": case["semantic_mode"],
                "bit_width": case["bit_width"],
                "category": case["category"],
                "family": case["family"],
                "solver_seconds": None,
                "solver_status": None,
                "validation_status": None,
                "reason": reason,
            }
            if parsed_status is not None:
                row["status"] = parsed_status
                rows.append(row)
                continue
            t0 = time.perf_counter()
            try:
                completed = _run(spec["binary"], spec["args"], script)
            except subprocess.TimeoutExpired:
                row["solver_seconds"] = time.perf_counter() - t0
                row["status"] = "timeout"
                row["solver_status"] = "process_timeout"
                row["reason"] = "solver process exceeded 30s"
                rows.append(row)
                continue
            row["solver_seconds"] = time.perf_counter() - t0
            kind, detail = _classify_solver(completed.stdout, completed.stderr, completed.returncode)
            row["solver_status"] = kind
            if kind == "unsat":
                row["status"] = "equivalent_within_model"
                row["reason"] = "solver returned unsat"
            elif kind == "timeout":
                row["status"] = "timeout"
                row["reason"] = detail
            elif kind == "unknown":
                row["status"] = "unknown"
                row["reason"] = detail
            elif kind == "solver_error":
                row["status"] = "solver_error"
                row["reason"] = detail
            elif kind == "sat":
                assignment = _parse_model(completed.stdout, mode_b, width)
                try:
                    original_value = evaluate(original, assignment, config)
                    candidate_value = evaluate(candidate, assignment, config)
                except Exception as exc:  # noqa: BLE001
                    row["status"] = "counterexample_validation_failed"
                    row["validation_status"] = "unvalidatable"
                    row["reason"] = f"reference evaluator rejected model: {exc}"
                else:
                    if original_value != candidate_value:
                        row["status"] = "counterexample_found"
                        row["validation_status"] = "confirmed"
                        row["reason"] = "reference evaluator confirmed the model"
                    else:
                        row["status"] = "counterexample_validation_failed"
                        row["validation_status"] = "not_a_difference"
                        row["reason"] = "model did not distinguish the expressions"
            else:
                row["status"] = "unknown"
                row["reason"] = detail
            rows.append(row)
        print(f"{case['case_id']} {len(rows)}", flush=True)

    def subset(solver: str, mode: str | None = None) -> list[dict]:
        chosen = [row for row in rows if row["solver"] == solver]
        if mode is not None:
            chosen = [row for row in chosen if row["semantic_mode"] == mode]
        return chosen

    summary = {
        "dataset": str(CASES.relative_to(ROOT)),
        "pair_count": 463,
        "solver_timeout_seconds": 5.0,
        "semantics": "Mode A mathematical integers (QF_NIA); Mode B unsigned wrap (QF_BV)",
        "counterexample_rule": "COUNTEREXAMPLE_FOUND only after reference_evaluator.evaluate disagrees",
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "wall_seconds": time.perf_counter() - started,
        "solvers": {},
    }
    for name in SOLVERS:
        summary["solvers"][name] = {
            "version_line": versions[name],
            "binary": SOLVERS[name]["binary"],
            "args": SOLVERS[name]["args"],
            "status_counts": _count(subset(name)),
            "by_mode": {
                "mode_a": {"n": len(subset(name, "mode_a")), "status_counts": _count(subset(name, "mode_a"))},
                "mode_b": {"n": len(subset(name, "mode_b")), "status_counts": _count(subset(name, "mode_b"))},
            },
        }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "second_solver.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    with (OUT_DIR / "second_solver_cases.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps(summary["solvers"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
