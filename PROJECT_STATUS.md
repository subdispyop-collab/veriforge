# PROJECT_STATUS

Status date: 2026-10-09  
Current phase: Phase 2 (formal verification) — implemented  
Phases 3–12: not started

This file records what is in the git checkout and the plan required by the controlling specification. The controlling specification was read and was not modified.

## Current state

Phase 2 is present on top of the preserved Phase 1 semantic foundation: `veriforge.verifier_engine`, verification models, pinned `z3-solver`, Phase 2 unit tests, and updated documentation including TCB notes in `docs/FORMAL_MODEL.md`.

Observed during Phase 2 work:

- Base branch: `cursor/phase-1-semantics-a215`.
- Work branch: `cursor/phase-2-verifier-183e`.
- Host interpreter: Python 3.12.3 at `/usr/bin/python3`.
- Project pin: `requires-python = ">=3.11"`; runtime dependency `z3-solver==5.1.0.0`.
- Test command run: `python3 -m pytest -v` after `python3 -m pip install -e ".[dev]"`.
- Result: **124 passed, 0 failed, 0 skipped** in 0.13s (pytest 9.1.1).

## Implemented features

Phase 1 (preserved):

- Written grammar and fail-closed parser (`veriforge/parser_engine.py`) using Python's `ast` module.
- Semantic configuration with explicit Mode A / Mode B (`veriforge/config.py`, `veriforge/semantics.py`).
- Mode B default width 32; unsigned modular wrap; out-of-range literals rejected.
- Integer literal spellings: decimal, hex, binary, octal, underscores; `True`/`False` rejected.
- Configurable resource limits with locked defaults (source length 4096, AST nodes 256, nesting depth 32, Mode A literal bit length 4096, solver timeout 5s).
- Reference evaluator matching the documented contract (`veriforge/reference_evaluator.py`).

Phase 2:

- IR → Z3 translation: Mode A integer sorts; Mode B bit-vector sorts (`veriforge/verifier_engine.py`).
- Equivalence query: exists input where original and candidate differ.
- Explicit result states: `EQUIVALENT_WITHIN_MODEL`, `COUNTEREXAMPLE_FOUND`, `UNKNOWN`, `TIMEOUT`, `UNSUPPORTED`, `INVALID_INPUT`, `TRANSLATION_ERROR`, `VERIFICATION_ERROR`.
- Counterexample extraction with independent reference-evaluator confirmation; failed validation reported as discrepancy / defect (`VERIFICATION_ERROR`), not as a confirmed counterexample.
- Solver timeout applied from `ResourceLimits.solver_timeout_seconds` (default 5s).
- Typed `VerificationResult` / `Counterexample` models and translation/verification exceptions.
- Unit tests in `tests/unit/test_verifier.py` covering translation, mode selection, boundaries, timeouts, UNKNOWN/unsupported/errors, counterexample reconstruction, constants/variables, and incorrect candidates.
- TCB / formal-model documentation in `docs/FORMAL_MODEL.md` (also reflected in ARCHITECTURE / LIMITATIONS).

## Unimplemented features

Everything from Phase 3 onward, including:

- Conservative rule-based optimizer, transformation traces, and isolated mutation module.
- Property, differential (beyond Phase 1/2 checks), regression of optimizer defects, and end-to-end application tests.
- Versioned datasets, baselines, experiment identifiers, and raw measurement storage.
- Separate timing of parse, optimization, translation, solver, and expression execution as a benchmark product.
- SQLite persistence, configuration fingerprints, export, and replay.
- The six specified Streamlit pages.
- Full security review, threat model, literature review, and research evidence ledger.
- A release checklist satisfied by executed checks for the whole product.

## Known defects

No failing Phase 1 or Phase 2 tests were observed in the recorded Phase 2 run.

Known gaps that are not product defects of implemented code:

- No continuous integration configuration exists.
- Static type checking and Ruff were not run as a project gate in Phase 2.
- Live TIMEOUT/UNKNOWN outcomes on hard SMT instances are rare for the initial arithmetic fragment; those statuses are covered by classification tests and solver mocks in addition to applying the real timeout setting.
- Later-phase modules do not exist; their defects cannot be assessed.

## Current test status

Command: `python3 -m pytest -v`  
Environment: Python 3.12.3, pytest 9.1.1, `z3-solver==5.1.0.0`, editable install of `veriforge` with `[dev]`.

| Metric | Count |
| --- | --- |
| Collected | 124 |
| Passed | 124 |
| Failed | 0 |
| Skipped | 0 |

Coverage was not measured. Coverage is not claimed.

Suites: Phase 1 unit tests plus `tests/unit/test_verifier.py`.

## Immediate next milestone

Phase 3 — Conservative optimizer: small rule set, rule metadata and transformation traces, verify each candidate before acceptance, regression tests.

## Decisions requiring later research

Items resolved in Phase 1 (locked 2026-10-09; written into `docs/SEMANTICS.md`):

1. Mode B unsigned interpretation; modular wrap; literals outside `[0, 2^w-1]` rejected; unary minus is BV negation; default width 32.
2. Integer literal spellings: Python `ast` integer forms including hex/bin/oct/underscores; `True`/`False` rejected.
3. Numeric resource-limit defaults listed under Implemented features.

Still open for later phases:

1. **A fifth experimental baseline.** No external tool selected.
2. **Interpreter pin for the full stack.** Host is 3.12.3; `z3-solver==5.1.0.0` tested in Phase 2; Streamlit and other later deps untested.
3. **Division, remainder, and shift conventions.** Not in the initial grammar; must be defined before any later phase adds them.
4. **Signedness for future Mode B operators.** Not used in the current Mode B contract.
5. **Literature review.** Not done. Phase 10.

Specified choices that already stand: Z3 as the verification engine; Python `ast` with no `eval` or `exec`; separate integer and bit-vector modes; initial bit width 32; conservative default optimization; verification-guided acceptance versus an isolated evaluation-only harness; SQLite as the initial store for experiment metadata; Streamlit for the interface; development cases kept separate from held-out cases.

## Phase-by-phase implementation plan

### Phase 0 — Repository audit and project plan

Status: satisfied (see Phase 0 history in `CHANGELOG.md`).

### Phase 1 — Semantic foundation

Status: satisfied (see Phase 1 history). Acceptance criteria met as previously recorded (84 tests at Phase 1 close; still passing within the Phase 2 suite).

### Phase 2 — Formal verification

Objective: translate the supported IR to Z3, classify solver results, extract and validate counterexamples, and test unsupported, timeout, and UNKNOWN behavior.

Acceptance criteria:

- Supported expressions translate to Z3 using Mode A integer sorts or Mode B bit-vector sorts matching `docs/SEMANTICS.md`: **met**.
- Equivalence query asks whether there exists an input where original and candidate differ: **met**.
- Result states are explicit and never collapsed to a Boolean: **met**.
- Counterexamples are independently validated with the reference evaluator before being labeled confirmed; failed validation is a discrepancy/defect: **met**.
- Solver timeout uses the configurable limit (default 5s): **met**.
- Tests cover translation, mode selection, boundaries, timeouts, UNKNOWN/unsupported/errors, counterexample reconstruction, constants/variables, and incorrect candidates: **met**.
- Trusted computing base assumptions documented: **met** (`docs/FORMAL_MODEL.md`, ARCHITECTURE, LIMITATIONS).
- Tests run with real pass/fail recorded: **met** (124 passed, 0 failed, 0 skipped).
- Phase 1 behavior preserved: **met** (prior unit suites still pass).

### Phases 3–12

Unchanged from the Phase 0 plan in substance; not started. See the controlling specification section 19 and the Phase 0 plan history for full acceptance criteria text.

## Highest-risk technical assumptions

These remain assumptions to test later. They are not findings.

1. **Encoder correctness.** A Z3 result talks about the formula that was submitted. Phase 2 reuses the Phase 1 configuration and grammar; residual risk is translator bugs (mitigated by reference validation of SAT models and unit tests).
2. **Python `int` versus Mode B.** Phase 1 wraps intentionally; Phase 2 uses BV sorts; later modules must not bypass that.
3. **Boolean constants.** Phase 1 rejects `True`/`False`; later parsers must keep that check.
4. **Solver incompleteness.** UNKNOWN, timeout, and interruption must never be treated as equivalence (enforced by `VerificationStatus`).
5. **Mutation isolation.** Production and mutation paths must not share an ungated acceptance function (Phase 3+).
6. **Dependence of observations.** Near-duplicate generated expressions are not independent samples.
7. **Reproducibility limits.** Exact bit-for-bit replay may not hold.
8. **Dependency compatibility.** `z3-solver==5.1.0.0` is pinned and tested; Streamlit, Hypothesis, pandas, Plotly, Ruff, and a type checker remain for later phases.

## Phase 2 acceptance checklist

- Mode A / Mode B Z3 sorts match semantics doc: yes.
- Equivalence query is existential difference: yes.
- Explicit non-Boolean result states: yes.
- Counterexample confirmation via reference evaluator: yes.
- Configurable solver timeout (default 5s): yes.
- Required verifier tests present and run: yes — 124 passed, 0 failed, 0 skipped.
- TCB documented: yes.
- Phase 1 preserved: yes.
