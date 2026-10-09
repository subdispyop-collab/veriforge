# PROJECT_STATUS

Status date: 2026-10-09  
Current phase: Phase 3 (conservative optimizer) — implemented  
Phases 4–12: not started

This file records what is in the git checkout and the plan required by the controlling specification. The controlling specification was read and was not modified.

## Current state

Phase 3 is present on top of the preserved Phase 1 semantic foundation and Phase 2 verifier: `veriforge.optimizer_engine`, optimization models, unit and regression tests, and updated documentation.

Observed during Phase 3 work:

- Base branch: `cursor/phase-2-verifier-183e`.
- Work branch: `cursor/phase-3-optimizer-8adb`.
- Host interpreter: Python 3.12.3 at `/usr/bin/python3`.
- Project pin: `requires-python = ">=3.11"`; runtime dependency `z3-solver==5.1.0.0`.
- Test command run: `python3 -m pytest -v` after `python3 -m pip install -e ".[dev]"`.
- Result: **181 passed, 0 failed, 0 skipped** in 0.28s (pytest 9.1.1).

## Implemented features

Phase 1 (preserved):

- Written grammar and fail-closed parser (`veriforge/parser_engine.py`) using Python's `ast` module.
- Semantic configuration with explicit Mode A / Mode B (`veriforge/config.py`, `veriforge/semantics.py`).
- Mode B default width 32; unsigned modular wrap; out-of-range literals rejected.
- Integer literal spellings: decimal, hex, binary, octal, underscores; `True`/`False` rejected.
- Configurable resource limits with locked defaults (source length 4096, AST nodes 256, nesting depth 32, Mode A literal bit length 4096, solver timeout 5s).
- Reference evaluator matching the documented contract (`veriforge/reference_evaluator.py`).

Phase 2 (preserved):

- IR → Z3 translation: Mode A integer sorts; Mode B bit-vector sorts (`veriforge/verifier_engine.py`).
- Equivalence query: exists input where original and candidate differ.
- Explicit result states including `EQUIVALENT_WITHIN_MODEL`, `COUNTEREXAMPLE_FOUND`, `UNKNOWN`, `TIMEOUT`, and error statuses.
- Counterexample extraction with independent reference-evaluator confirmation.
- TCB / formal-model documentation in `docs/FORMAL_MODEL.md`.

Phase 3:

- Conservative optimizer (`veriforge/optimizer_engine.py`) following specification §7.1.
- Production rules with metadata (id, name, formal description, preconditions, supported modes, verification policy, implementation): `identity.add_zero`, `identity.sub_zero`, `identity.mul_one`, `identity.mul_zero`.
- Rules validated under Mode A and Mode B separately (not assumed universal across future extensions).
- Transformation traces (`TransformationStep`) recording rule, preconditions, before/after sources, verification result, and accept/reject decision.
- Default `CorrectnessPolicy.VERIFICATION_GUIDED`: accept only on `EQUIVALENT_WITHIN_MODEL`; reject and record `COUNTEREXAMPLE_FOUND`, `UNKNOWN`, `TIMEOUT`, and error statuses.
- `CorrectnessPolicy.EVALUATION_ONLY` modeled for API clarity; `optimize()` rejects it until Phase 4.
- Unit tests in `tests/unit/test_optimizer.py`; regression gate in `tests/regression/test_optimizer_acceptance_gate.py`.

## Unimplemented features

Everything from Phase 4 onward, including:

- Isolated mutation-testing module and evaluation-only harness for deliberately incorrect candidates.
- Property-based tests, broader differential suites, and adversarial fuzzing beyond Phase 3 gating tests.
- Versioned datasets, baselines, experiment identifiers, and raw measurement storage.
- Separate timing of parse, optimization, translation, solver, and expression execution as a benchmark product.
- SQLite persistence, configuration fingerprints, export, and replay.
- The six specified Streamlit pages.
- Full security review, threat model, literature review, and research evidence ledger.
- A release checklist satisfied by executed checks for the whole product.

## Known defects

No failing Phase 1–3 tests were observed in the recorded Phase 3 run.

Known gaps that are not product defects of implemented code:

- No continuous integration configuration exists.
- Static type checking and Ruff were not run as a project gate in Phase 3.
- Live TIMEOUT/UNKNOWN outcomes on hard SMT instances remain uncommon for this fragment; optimizer rejection of those statuses is covered by injected-status tests.
- Later-phase modules do not exist; their defects cannot be assessed.

## Current test status

Command: `python3 -m pytest -v`  
Environment: Python 3.12.3, pytest 9.1.1, `z3-solver==5.1.0.0`, editable install of `veriforge` with `[dev]`.

| Metric | Count |
| --- | --- |
| Collected | 181 |
| Passed | 181 |
| Failed | 0 |
| Skipped | 0 |

Coverage was not measured. Coverage is not claimed.

Suites: Phase 1–2 unit tests, `tests/unit/test_optimizer.py`, and `tests/regression/test_optimizer_acceptance_gate.py`.

## Immediate next milestone

Phase 4 — Adversarial validation: property-based tests, controlled incorrect mutations (isolated module), differential tests with reproducible seeds, fix and preserve every discovered defect.

## Decisions requiring later research

Items resolved in Phase 1 (locked 2026-10-09; written into `docs/SEMANTICS.md`):

1. Mode B unsigned interpretation; modular wrap; literals outside `[0, 2^w-1]` rejected; unary minus is BV negation; default width 32.
2. Integer literal spellings: Python `ast` integer forms including hex/bin/oct/underscores; `True`/`False` rejected.
3. Numeric resource-limit defaults listed under Implemented features.

Still open for later phases:

1. **A fifth experimental baseline.** No external tool selected.
2. **Interpreter pin for the full stack.** Host is 3.12.3; `z3-solver==5.1.0.0` tested; Streamlit and other later deps untested.
3. **Division, remainder, and shift conventions.** Not in the initial grammar; must be defined before any later phase adds them.
4. **Signedness for future Mode B operators.** Not used in the current Mode B contract.
5. **Literature review.** Not done. Phase 10.

Specified choices that already stand: Z3 as the verification engine; Python `ast` with no `eval` or `exec`; separate integer and bit-vector modes; initial bit width 32; conservative default optimization; verification-guided acceptance versus an isolated evaluation-only harness; SQLite as the initial store for experiment metadata; Streamlit for the interface; development cases kept separate from held-out cases.

## Phase-by-phase implementation plan

### Phase 0 — Repository audit and project plan

Status: satisfied (see Phase 0 history in `CHANGELOG.md`).

### Phase 1 — Semantic foundation

Status: satisfied. Acceptance criteria met as previously recorded.

### Phase 2 — Formal verification

Status: satisfied. Acceptance criteria met as previously recorded (124 tests at Phase 2 close; still passing within the Phase 3 suite).

### Phase 3 — Conservative optimizer

Objective: small rule set, rule metadata and transformation traces, verify each candidate before acceptance, regression tests.

Acceptance criteria:

- Identity-preserving rules implemented with unique ids, names, formal descriptions, preconditions, supported modes, implementations, positive/negative tests, verification policy, and trace records: **met**.
- Rules validated under Mode A and Mode B separately: **met**.
- Pipeline follows specification §7.1: **met**.
- Default mode is verification-guided; non-equivalent and inconclusive statuses never silently accepted: **met**.
- Evaluation-only / mutation path not mixed into production acceptance: **met** (`EVALUATION_ONLY` rejected; mutation module not started).
- Regression tests for the acceptance gate: **met**.
- Phases 1–2 preserved: **met**.
- Tests run with real pass/fail recorded: **met** (181 passed, 0 failed, 0 skipped).

### Phases 4–12

Unchanged from the Phase 0 plan in substance; not started. See the controlling specification section 19 and the Phase 0 plan history for full acceptance criteria text.

## Highest-risk technical assumptions

These remain assumptions to test later. They are not findings.

1. **Encoder correctness.** A Z3 result talks about the formula that was submitted. Residual risk is translator bugs (mitigated by reference validation of SAT models and unit tests).
2. **Python `int` versus Mode B.** Phase 1 wraps intentionally; Phase 2 uses BV sorts; the optimizer must not bypass that (it reuses the same configuration and verifier).
3. **Boolean constants.** Phase 1 rejects `True`/`False`; later parsers must keep that check.
4. **Solver incompleteness.** UNKNOWN, timeout, and interruption must never be treated as equivalence (enforced by verifier statuses and optimizer rejection).
5. **Mutation isolation.** Production and mutation paths must not share an ungated acceptance function (Phase 4 must preserve this).
6. **Dependence of observations.** Near-duplicate generated expressions are not independent samples.
7. **Reproducibility limits.** Exact bit-for-bit replay may not hold.
8. **Dependency compatibility.** `z3-solver==5.1.0.0` is pinned and tested; Streamlit, Hypothesis, pandas, Plotly, Ruff, and a type checker remain for later phases.

## Phase 3 acceptance checklist

- Small identity-preserving rule set with full metadata: yes.
- Mode A and Mode B validated separately: yes.
- Transformation traces complete: yes.
- Verification before acceptance; inconclusive/error statuses rejected: yes.
- Evaluation-only path not production-accepted: yes.
- Regression tests present and run: yes — 181 passed, 0 failed, 0 skipped.
- Phases 1–2 preserved: yes.
- Phase 4 not started: yes.
