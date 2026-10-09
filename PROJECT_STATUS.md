# PROJECT_STATUS

Status date: 2026-10-09  
Current phase: Phase 1 (semantic foundation) — implemented  
Phases 2–12: not started

This file records what is in the git checkout and the plan required by the controlling specification. The controlling specification was read and was not modified.

## Current state

Phase 1 is present: a minimal `veriforge` package, pytest suite, dependency manifests, and updated documentation of the locked semantic contract.

Observed during Phase 1 work:

- Base branch: `cursor/phase-0-audit-5b37` (Phase 0 docs).
- Work branch: `cursor/phase-1-semantics-a215`.
- Host interpreter: Python 3.12.3 at `/usr/bin/python3`.
- Project pin: `requires-python = ">=3.11"` in `pyproject.toml`.
- Test command run: `python3 -m pytest -v` after `python3 -m pip install -e ".[dev]"`.
- Result: **84 passed, 0 failed, 0 skipped** in 0.09s (pytest 9.1.1).

## Implemented features

Phase 1 only:

- Written grammar and fail-closed parser (`veriforge/parser_engine.py`) using Python's `ast` module.
- Semantic configuration with explicit Mode A / Mode B (`veriforge/config.py`, `veriforge/semantics.py`).
- Mode B default width 32; unsigned modular wrap; out-of-range literals rejected.
- Integer literal spellings: decimal, hex, binary, octal, underscores; `True`/`False` rejected.
- Configurable resource limits with locked defaults (source length 4096, AST nodes 256, nesting depth 32, Mode A literal bit length 4096, solver timeout config 5s).
- Reference evaluator matching the documented contract (`veriforge/reference_evaluator.py`).
- Typed models and classified exceptions for Phase 1.
- Hand-checked semantic and parser unit tests under `tests/unit/`.

## Unimplemented features

Everything from Phase 2 onward, including:

- Z3 translation, solver-result classification, and counterexample validation.
- Conservative rule-based optimizer, transformation traces, and isolated mutation module.
- Property, differential (beyond Phase 1 hand-checks), regression of optimizer defects, and end-to-end application tests.
- Versioned datasets, baselines, experiment identifiers, and raw measurement storage.
- Separate timing of parse, optimization, translation, solver, and expression execution beyond what Phase 1 does not measure.
- SQLite persistence, configuration fingerprints, export, and replay.
- The six specified Streamlit pages.
- Full security review, threat model, literature review, and research evidence ledger.
- A release checklist satisfied by executed checks for the whole product.

## Known defects

No failing Phase 1 tests were observed in the recorded run.

Known gaps that are not product defects of implemented code:

- Solver timeout is stored in configuration but not enforced (no solver in Phase 1).
- No continuous integration configuration exists.
- Static type checking and Ruff were not run as a project gate in Phase 1.
- Later-phase modules do not exist; their defects cannot be assessed.

## Current test status

Command: `python3 -m pytest -v`  
Environment: Python 3.12.3, pytest 9.1.1, editable install of `veriforge` with `[dev]`.

| Metric | Count |
| --- | --- |
| Collected | 84 |
| Passed | 84 |
| Failed | 0 |
| Skipped | 0 |

Coverage was not measured. Coverage is not claimed.

Suites: `tests/unit/test_config.py`, `test_no_eval_exec.py`, `test_parser.py`, `test_semantics_mode_a.py`, `test_semantics_mode_b.py`.

## Immediate next milestone

Phase 2 — Formal verification: AST-to-Z3 translation, solver-result classification, counterexample extraction and validation, tests for unsupported / timeout / UNKNOWN behavior.

## Decisions requiring later research

Items resolved in Phase 1 (locked 2026-10-09; written into `docs/SEMANTICS.md`):

1. Mode B unsigned interpretation; modular wrap; literals outside `[0, 2^w-1]` rejected; unary minus is BV negation; default width 32.
2. Integer literal spellings: Python `ast` integer forms including hex/bin/oct/underscores; `True`/`False` rejected.
3. Numeric resource-limit defaults listed under Implemented features.

Still open for later phases:

1. **A fifth experimental baseline.** No external tool selected.
2. **Interpreter pin for the full stack.** Host is 3.12.3; `z3-solver` and Streamlit compatibility untested.
3. **Division, remainder, and shift conventions.** Not in the initial grammar; must be defined before any later phase adds them.
4. **Signedness for future Mode B operators.** Not used in the current Mode B contract.
5. **Literature review.** Not done. Phase 10.

Specified choices that already stand: Z3 as the verification engine; Python `ast` with no `eval` or `exec`; separate integer and bit-vector modes; initial bit width 32; conservative default optimization; verification-guided acceptance versus an isolated evaluation-only harness; SQLite as the initial store for experiment metadata; Streamlit for the interface; development cases kept separate from held-out cases.

## Phase-by-phase implementation plan

### Phase 0 — Repository audit and project plan

Status: satisfied (see Phase 0 history in `CHANGELOG.md`).

### Phase 1 — Semantic foundation

Objective: define the grammar, implement safe parsing, implement semantic configuration, create the reference evaluator, and write hand-checked semantic tests.

Acceptance criteria:

- The written grammar and the parser accept only the initial forms in `docs/SEMANTICS.md`: **met**.
- Parsing uses Python's `ast` module and does not use `eval` or `exec`: **met** (guarded by `test_no_eval_exec.py`).
- Unsupported syntax, unapproved AST nodes, and over-limit inputs fail closed with a classified error: **met**.
- Mode A and Mode B are explicit. Mode B uses a configurable width whose initial value is 32: **met**.
- Mathematical integers and fixed-width bit-vectors are not conflated: **met**.
- The reference evaluator implements the same contract as the documented semantics: **met** (hand-checked Mode A / Mode B tests).
- Hand-checked semantic tests exist and have been run, with the real pass/fail summary recorded: **met** (84 passed, 0 failed, 0 skipped).
- Open decisions that change literal conversion or Mode B interpretation are resolved in the semantics document before Mode B behavior is encoded: **met**.

### Phase 2 — Formal verification

Objective: translate the supported AST to Z3, classify solver results, extract and validate counterexamples, and test unsupported, timeout, and UNKNOWN behavior.

Acceptance criteria: unchanged from the Phase 0 plan; not started.

### Phases 3–12

Unchanged from the Phase 0 plan in substance; not started. See the controlling specification section 19 and the Phase 0 plan history for full acceptance criteria text.

## Highest-risk technical assumptions

These remain assumptions to test later. They are not findings.

1. **Encoder correctness (Phase 2).** A Z3 result talks about the formula that was submitted. Phase 2 must reuse the Phase 1 configuration and grammar.
2. **Python `int` versus Mode B.** Phase 1 wraps intentionally; later modules must not bypass that.
3. **Boolean constants.** Phase 1 rejects `True`/`False`; later parsers must keep that check.
4. **Solver incompleteness.** UNKNOWN, timeout, and interruption must never be treated as equivalence.
5. **Mutation isolation.** Production and mutation paths must not share an ungated acceptance function.
6. **Dependence of observations.** Near-duplicate generated expressions are not independent samples.
7. **Reproducibility limits.** Exact bit-for-bit replay may not hold.
8. **Dependency compatibility.** Full specified stack (`z3-solver`, Streamlit, Hypothesis, pandas, Plotly, Ruff, type checker) is not yet installed or locked beyond pytest for Phase 1.

## Phase 1 acceptance checklist

- Written grammar and parser accept only initial forms: yes.
- `ast` only; no `eval`/`exec`: yes.
- Fail-closed classified errors for unsupported / unapproved / over-limit: yes.
- Mode A and Mode B explicit; Mode B default width 32: yes.
- Integers and bit-vectors not conflated: yes.
- Reference evaluator matches documented semantics: yes.
- Hand-checked tests run with real summary: yes — 84 passed, 0 failed, 0 skipped.
- Locked decisions written into `docs/SEMANTICS.md` before Mode B encoding: yes.
