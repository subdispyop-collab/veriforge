# PROJECT_STATUS

Status date: 2026-10-09  
Current phase: Phase 6 (benchmark engine) — implemented  
Phases 7–12: not started

This file records what is in the git checkout and the plan required by the controlling specification. The controlling specification was read and was not modified.

## Current state

Phase 6 is present on top of the preserved Phases 1–5: a benchmark engine that measures parsing, optimization, candidate generation, AST-to-Z3 translation, solver time, end-to-end verification, and original vs optimized execution as **separate** fields; repeated trials with warmup and timeout policy; environment recording; raw observation persistence; medians and variability in reports; reproduction from a saved configuration with nondeterminism disclosure. Development datasets are used for **engine validation only**. **No held-out final evaluation was run as a research conclusion.** No Streamlit UI. No inventing of scientific benchmark conclusions.

Observed during Phase 6 work:

- Base branch: `cursor/phase-5-experiments-0204`.
- Work branch: `cursor/phase-6-benchmarks-1735`.
- Host interpreter: Python 3.12.3 at `/usr/bin/python3`.
- Project pin: `requires-python = ">=3.11"`; runtime dependency `z3-solver==5.1.0.0`; version `0.6.0`.
- Test command intended: `python3 -m pytest -v` after `python3 -m pip install -e ".[dev]"`.
- Dependency install on this Phase 6 host was blocked by restricted egress to `pypi.org` / `files.pythonhosted.org` (TLS EOF). See Current test status.

## Implemented features

Phase 1–5 (preserved): see prior `PROJECT_STATUS` history and `CHANGELOG.md`.

Phase 6:

- `veriforge/benchmark_engine.py`: separated §10 timings; warmups; repeated trials; timeout policy; environment record; raw saves; medians/variability; reproduction from saved configuration; §10.2 speedup-claim guard.
- `verify_equivalence_timed` in `veriforge/verifier_engine.py` exposing translation vs solver times separately.
- Models: `BenchmarkConfiguration`, `BenchmarkMeasurement`, `BenchmarkReport`, `TimingStatistic`, `BenchmarkRateSummary`, `EnvironmentRecord`, `WarmupPolicy`, `TimeoutPolicy`; `ObservationKind.BENCHMARK_TIMING`.
- Script: `scripts/run_benchmarks.py` (development partition engine validation only).
- Docs / status / changelog updated. Phases 1–5 preserved.

## Unimplemented features

Everything from Phase 7 onward, including:

- Full audit export/replay deepening (Phase 7).
- The six specified Streamlit pages (Phase 8).
- Full security review, threat model, literature review, and research evidence ledger.
- Held-out evaluation execution (Phase 10).
- A release checklist satisfied by executed checks for the whole product.

## Known defects

Known gaps that are not product defects of implemented Phase 6 code:

- No continuous integration configuration exists.
- Static type checking and Ruff were not run as a project gate in Phase 6.
- Baseline 5 (external tool) remains not selected.
- On this Phase 6 VM, pip install of `z3-solver` / pytest / hypothesis failed due to egress allowlist (not a VERIFORGE code defect).
- Later-phase modules do not exist; their defects cannot be assessed.

## Current test status

Command attempted: `python3 -m pip install -e ".[dev]"` then `python3 -m pytest -v`.

| Metric | Count |
| --- | --- |
| Passed | unavailable (deps not installable on this host) |
| Failed | unavailable |
| Skipped | unavailable |

Blocker: restricted network egress prevents HTTPS to `pypi.org` and `files.pythonhosted.org` (`SSL_ERROR_SYSCALL` / SSLEOFError). `z3-solver`, `pytest`, and `hypothesis` are not present in the default image. Egress allowlist additions for those domains were requested. Phase 5 previously recorded **245 passed** on a host where deps were available; Phase 6 adds `tests/unit/test_benchmark_engine.py` which has not yet been executed on this host.

## Decisions requiring later research

Locked and approved (Phase 1; do not reopen without asking): Mode B unsigned wrap; Python `ast` integer spellings without bools; numeric resource-limit defaults.

Still open for later phases: external baseline tool; Streamlit/pandas/Plotly stack pin; division/remainder/shift conventions; Mode B signedness for future operators; literature review (Phase 10).

## Phase-by-phase implementation plan

### Phases 0–5

Status: satisfied (see `CHANGELOG.md`).

### Phase 6 — Benchmark engine

Objective: measure solver and expression execution performance separately; repeated trials and timeout handling; save raw observations; test benchmark reproduction.

Acceptance criteria:

- Store §10 measurements separately (parsing, optimization, candidate generation, translation, solver, end-to-end verification, original vs optimized execution): **met** (models + engine).
- Timeout / UNKNOWN / completion / rejection / counterexample rates from those records: **met** (`compute_rate_summary`).
- Trials, seeds, warmup policy, timeout policy, and environment recorded: **met** (`BenchmarkConfiguration` / `EnvironmentRecord`).
- Reports use medians and variability; never claim execution speedup from shorter expression or faster solver alone: **met** (`TimingStatistic`, `speedup_claim_policy`, `assert_no_spurious_execution_speedup_claim`).
- Saved benchmark can be rerun from recorded configuration; nondeterminism disclosed: **met**.
- `benchmark_engine.py` added; Phases 1–5 preserved: **met**.
- Development datasets for engine validation only; not final research findings: **met** (`is_research_conclusion=False`; held-out runs refused).
- Tests run with real pass/fail recorded: **blocked on this host by PyPI egress** (see Current test status). Suite is present under `tests/unit/test_benchmark_engine.py`.

### Phases 7–12

Not started. See the controlling specification section 19.

## Highest-risk technical assumptions

1. Encoder correctness.
2. Modes remain distinct.
3. UNKNOWN/timeout never treated as equivalence.
4. Mutation isolation.
5. Dependence of observations.
6. Reproducibility limits (timing nondeterminism disclosed in Phase 6).
7. Dependency compatibility for Streamlit stack (later).
8. Egress / environment builds must provide `z3-solver` for CI and agents.

## Phase 6 acceptance checklist

- Separated §10 timings: yes.
- Rates from records: yes.
- Trials/seeds/warmup/timeout/environment recorded: yes.
- Medians + variability; no spurious execution-speedup claims: yes.
- Reproduction from saved config + nondeterminism disclosure: yes.
- `benchmark_engine.py` + models/scripts; Phases 1–5 preserved: yes.
- Dev-only engine validation; no held-out research conclusion: yes.
- Tests executed with real pass/fail on this host: **no — egress blocker**.
