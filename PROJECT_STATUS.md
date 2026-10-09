# PROJECT_STATUS

Status date: 2026-10-09  
Current phase: Phase 5 (experimental framework) — implemented  
Phases 6–12: not started

This file records what is in the git checkout and the plan required by the controlling specification. The controlling specification was read and was not modified.

## Current state

Phase 5 is present on top of the preserved Phases 1–4: frozen research protocol, versioned development/held-out datasets with §9.4 metadata and near-duplicate leakage controls, experiment run identifiers and configuration fingerprints, filesystem + SQLite raw-observation persistence, and metric calculations validated against known fixture cases. **No held-out evaluation was run.**

Observed during Phase 5 work:

- Base branch: `cursor/phase-4-adversarial-c33b`.
- Work branch: `cursor/phase-5-experiments-0204`.
- Host interpreter: Python 3.12.3 at `/usr/bin/python3`.
- Project pin: `requires-python = ">=3.11"`; runtime dependency `z3-solver==5.1.0.0`; dev `hypothesis==6.168.5`.
- Test command run: `python3 -m pytest -v` after `python3 -m pip install -e ".[dev]"`.
- Result: **245 passed, 0 failed, 0 skipped** in 3.69s (pytest 9.1.1).

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

Phase 4 (preserved):

- Isolated mutation module (`veriforge/fuzzer_suite.py`) per §7.2.
- Hypothesis property tests, differential tests, adversarial / isolation / regression suites.

Phase 5:

- Research protocol freeze: `docs/RESEARCH_PLAN.md` (hypotheses remain hypotheses) and `docs/EXPERIMENT_PROTOCOL.md` (protocol `0.5.0`).
- Baselines defined in `veriforge.experiment_engine.baseline_catalog()`; none measured; external tool not selected.
- Versioned seed datasets under `datasets/development/` and `datasets/held_out/` with §9.4 metadata (`veriforge/dataset_engine.py`).
- Near-duplicate leakage controls via `near_duplicate_key` / `assert_no_cross_partition_leakage`.
- Artificial 90/10 mix labeled as controlled configuration, not real-world prevalence (`ARTIFICIAL_90_10_MIX`).
- Experiment run identifiers, configuration fingerprints, raw observation storage (filesystem JSON + SQLite index): `veriforge/experiment_engine.py`, `veriforge/storage/`.
- Metric calculations with results-by-class; unit-tested against known fixture observations (not research findings).
- Models: `DatasetMetadata`, `DatasetCase`, `ExperimentRun`, `RawObservation`, `MetricSummary`, baselines, controlled mix, and related enums.

## Unimplemented features

Everything from Phase 6 onward, including:

- Full benchmark engine with separate timing of parse, optimization, translation, solver, and expression execution (Phase 6).
- Full audit export/replay deepening (Phase 7).
- The six specified Streamlit pages.
- Full security review, threat model, literature review, and research evidence ledger.
- Held-out evaluation execution (Phase 10).
- A release checklist satisfied by executed checks for the whole product.

## Known defects

No failing Phase 1–5 tests were observed in the recorded Phase 5 run.

Known gaps that are not product defects of implemented code:

- No continuous integration configuration exists.
- Static type checking and Ruff were not run as a project gate in Phase 5.
- Live TIMEOUT/UNKNOWN outcomes on hard SMT instances remain uncommon for this fragment; optimizer rejection of those statuses is covered by injected-status unit/regression tests.
- Baseline 5 (external tool) remains not selected.
- Later-phase modules do not exist; their defects cannot be assessed.

## Current test status

Command: `python3 -m pytest -v`  
Environment: Python 3.12.3, pytest 9.1.1, hypothesis 6.168.5, `z3-solver==5.1.0.0`, editable install of `veriforge` with `[dev]`.

| Metric | Count |
| --- | --- |
| Passed | 245 |
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

Status: satisfied.

### Phase 2 — Formal verification

Status: satisfied.

### Phase 3 — Conservative optimizer

Status: satisfied.

### Phase 4 — Adversarial validation

Status: satisfied (230 tests at Phase 4 close; still passing within the Phase 5 suite).

### Phase 5 — Experimental framework

Objective: freeze the initial research protocol; define baselines and datasets; add experiment identifiers and raw-data persistence; validate metric calculations.

Acceptance criteria:

- Research question, hypotheses, baselines, and primary outcomes in `docs/RESEARCH_PLAN.md` stay as preregistered hypotheses (not findings): **met**.
- Protocol freeze details in `docs/EXPERIMENT_PROTOCOL.md`: **met**.
- Versioned datasets with §9.4 metadata; development vs held_out; near-duplicate leakage controls: **met**.
- Artificial 90/10 mix labeled as controlled configuration, not real-world prevalence: **met**.
- Experiment run identifiers, configuration fingerprints, raw observation storage (filesystem + SQLite): **met**.
- Metric calculations tested against known cases; results-by-class from stored raw observations: **met**.
- No held-out evaluation run: **met**.
- Modules with real responsibility (`dataset_engine.py`, `experiment_engine.py`, models, storage): **met**.
- Phases 1–4 preserved: **met**.
- Tests run with real pass/fail recorded: **met** (245 passed, 0 failed, 0 skipped).
- Phase 6 not started: **met**.

### Phases 6–12

Not started. See the controlling specification section 19 for full acceptance criteria text.

## Highest-risk technical assumptions

These remain assumptions to test later. They are not findings.

1. **Encoder correctness.** A Z3 result talks about the formula that was submitted.
2. **Python `int` versus Mode B.** Modes remain distinct.
3. **Boolean constants.** `True`/`False` stay rejected.
4. **Solver incompleteness.** UNKNOWN/timeout never treated as equivalence.
5. **Mutation isolation.** Production and mutation paths remain structurally separated.
6. **Dependence of observations.** Near-duplicate generated expressions are not independent samples (leakage controls address partition contamination; dependence remains a statistical threat).
7. **Reproducibility limits.** Exact bit-for-bit replay may not hold.
8. **Dependency compatibility.** Streamlit, pandas, Plotly, Ruff, and a type checker remain for later phases.

## Phase 5 acceptance checklist

- Protocol frozen; hypotheses not treated as findings: yes.
- Baselines defined (not measured): yes.
- Versioned development / held_out datasets with §9.4 metadata: yes.
- Near-duplicate leakage controls: yes.
- Artificial 90/10 labeled as controlled configuration: yes.
- Run ids + configuration fingerprints + raw persistence: yes.
- Metric calculations tested against known cases; by-class support: yes.
- No held-out evaluation: yes.
- Phases 1–4 preserved: yes.
- Phase 6 not started: yes.
- Tests: 245 passed, 0 failed, 0 skipped.
