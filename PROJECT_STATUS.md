# PROJECT_STATUS

Status date: 2026-10-09  
Current phase: Phase 4 (adversarial validation) — implemented  
Phases 5–12: not started

This file records what is in the git checkout and the plan required by the controlling specification. The controlling specification was read and was not modified.

## Current state

Phase 4 is present on top of the preserved Phases 1–3: isolated mutation module, Hypothesis property tests, differential tests against the reference evaluator, reproducible seeds, and updated documentation.

Observed during Phase 4 work:

- Base branch: `cursor/phase-3-optimizer-8adb`.
- Work branch: `cursor/phase-4-adversarial-c33b`.
- Host interpreter: Python 3.12.3 at `/usr/bin/python3`.
- Project pin: `requires-python = ">=3.11"`; runtime dependency `z3-solver==5.1.0.0`; dev `hypothesis==6.168.5`.
- Test command run: `python3 -m pytest -v` after `python3 -m pip install -e ".[dev]"`.
- Result: **230 passed, 0 failed, 0 skipped** in 4.18s (pytest 9.1.1).

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

Phase 3 (preserved):

- Conservative optimizer (`veriforge/optimizer_engine.py`) following specification §7.1.
- Production rules: `identity.add_zero`, `identity.sub_zero`, `identity.mul_one`, `identity.mul_zero`.
- Default `CorrectnessPolicy.VERIFICATION_GUIDED`: accept only on `EQUIVALENT_WITHIN_MODEL`.
- Transformation traces and regression acceptance-gate tests.

Phase 4:

- Isolated mutation module (`veriforge/fuzzer_suite.py`) per §7.2.
- Artificial mutation categories under `mutation.*` prefix, disjoint from production rules.
- Each `MutationRecord` stores `mutation_id`, `generation_method`, `seed`, and `artificial=True`.
- Reproducible generation via `DEFAULT_MUTATION_SEED` and per-call seeds.
- EVALUATION_ONLY harness (`analyze_mutation` / `mutate_and_analyze`) analyzes deliberate incorrect candidates; `accepted_into_production` is always False.
- Production `optimize()` continues to reject `EVALUATION_ONLY`.
- Hypothesis property tests: `tests/properties/` (parser, semantics, verifier, optimizer).
- Differential tests vs reference evaluator: `tests/properties/test_differential.py`.
- Adversarial / isolation / regression suites: `tests/adversarial/`, `tests/regression/test_mutation_gate.py`, `tests/unit/test_fuzzer_suite.py`.

## Unimplemented features

Everything from Phase 5 onward, including:

- Versioned research datasets, baselines, experiment identifiers, and raw measurement storage.
- Separate timing of parse, optimization, translation, solver, and expression execution as a benchmark product.
- SQLite persistence, configuration fingerprints, export, and replay.
- The six specified Streamlit pages.
- Full security review, threat model, literature review, and research evidence ledger.
- A release checklist satisfied by executed checks for the whole product.

## Known defects

No failing Phase 1–4 tests were observed in the recorded Phase 4 run. No production defect requiring a new regression case was discovered by the Phase 4 campaign; the mutation and differential suites passed as written.

Known gaps that are not product defects of implemented code:

- No continuous integration configuration exists.
- Static type checking and Ruff were not run as a project gate in Phase 4.
- Live TIMEOUT/UNKNOWN outcomes on hard SMT instances remain uncommon for this fragment; optimizer rejection of those statuses is covered by injected-status unit/regression tests.
- Later-phase modules do not exist; their defects cannot be assessed.

## Current test status

Command: `python3 -m pytest -v`  
Environment: Python 3.12.3, pytest 9.1.1, hypothesis 6.168.5, `z3-solver==5.1.0.0`, editable install of `veriforge` with `[dev]`.

| Metric | Count |
| --- | --- |
| Passed | 230 |
| Failed | 0 |
| Skipped | 0 |

## Decisions requiring later research

Locked and approved (Phase 1; do not reopen without asking):

1. Mode B: unsigned modular wrap; configurable width; default 32; out-of-range literals rejected (not reduced).
2. Integer literal spellings: Python `ast` integer forms including hex/bin/oct/underscores; `True`/`False` rejected.
3. Numeric resource-limit defaults listed under Implemented features.

Still open for later phases:

1. **A fifth experimental baseline.** No external tool selected.
2. **Interpreter pin for the full stack.** Host is 3.12.3; `z3-solver==5.1.0.0` and `hypothesis==6.168.5` tested; Streamlit and other later deps untested.
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

Status: satisfied. Acceptance criteria met as previously recorded.

### Phase 3 — Conservative optimizer

Status: satisfied. Acceptance criteria met as previously recorded (181 tests at Phase 3 close; still passing within the Phase 4 suite).

### Phase 4 — Adversarial validation

Objective: property-based tests; controlled incorrect mutations; differential tests; reproducible seeds; fix and preserve every discovered defect.

Acceptance criteria:

- Isolated, explicitly labeled mutation-testing module: **met** (`veriforge/fuzzer_suite.py`).
- Artificial mutations clearly marked; never mixed into production rules; never bypass verification gate: **met**.
- Mutation id + generation method stored; reproducible via fixed seeds: **met**.
- Hypothesis property tests for parser/semantics/verifier/optimizer under the locked contract: **met**.
- Differential testing against the reference evaluator: **met**.
- EVALUATION_ONLY harness may analyze incorrect candidates but does not silently accept them into production: **met**.
- Regression coverage for mutation gate / isolation: **met**.
- Phases 1–3 preserved: **met**.
- Tests run with real pass/fail recorded: **met** (230 passed, 0 failed, 0 skipped).
- Phase 5 not started: **met**.

### Phases 5–12

Unchanged from the Phase 0 plan in substance; not started. See the controlling specification section 19 and the Phase 0 plan history for full acceptance criteria text.

## Highest-risk technical assumptions

These remain assumptions to test later. They are not findings.

1. **Encoder correctness.** A Z3 result talks about the formula that was submitted. Residual risk is translator bugs (mitigated by reference validation of SAT models, unit tests, and Phase 4 differential/property suites).
2. **Python `int` versus Mode B.** Phase 1 wraps intentionally; Phase 2 uses BV sorts; the optimizer must not bypass that (it reuses the same configuration and verifier).
3. **Boolean constants.** Phase 1 rejects `True`/`False`; later parsers must keep that check.
4. **Solver incompleteness.** UNKNOWN, timeout, and interruption must never be treated as equivalence (enforced by verifier statuses and optimizer rejection).
5. **Mutation isolation.** Production and mutation paths must not share an ungated acceptance function (structural isolation in `fuzzer_suite` vs `optimize()`).
6. **Dependence of observations.** Near-duplicate generated expressions are not independent samples.
7. **Reproducibility limits.** Exact bit-for-bit replay may not hold.
8. **Dependency compatibility.** `z3-solver==5.1.0.0` and `hypothesis==6.168.5` are pinned and tested; Streamlit, pandas, Plotly, Ruff, and a type checker remain for later phases.

## Phase 4 acceptance checklist

- Property-based tests present and run: yes.
- Controlled incorrect mutations isolated and labeled: yes.
- Differential tests against reference evaluator: yes.
- Reproducible seeds: yes.
- EVALUATION_ONLY harness does not accept into production: yes.
- Defects found by the campaign: none requiring a new production fix in this run; suites passed.
- Regression tests for mutation gate: yes.
- Phases 1–3 preserved: yes.
- Phase 5 not started: yes.
- Tests: 230 passed, 0 failed, 0 skipped.
