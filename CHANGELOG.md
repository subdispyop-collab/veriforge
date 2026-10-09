# Changelog

## Phase 10 — Research evaluation

Date: 2026-10-09

- Literature review with real sources only (`docs/LITERATURE_REVIEW.md`); no novelty claim; §16 bibliographic fields recorded (access date 2026-10-09).
- Evidence ledger (`docs/EVIDENCE_LEDGER.md`) with claim statuses; hypotheses remain hypotheses until held-out evidence supports them.
- Held-out evaluation harness: `veriforge/evaluation_engine.py`, protocol `veriforge-phase10-held-out-evaluation` v`1.0.0`, runner `scripts/run_held_out_evaluation.py`.
- Implemented baselines 1–4 runnable against `datasets/held_out/` with recorded seeds/config; baseline 5 remains not_selected.
- Reports separate solver latency from expression execution and include by-class sample sizes.
- Phase 5 `create_experiment_run` still forbids held-out execution under protocol `0.5.0`; Phase 10 protocol versions may set `execute_held_out_evaluation=True`.
- Docs: `PROJECT_STATUS.md`, `docs/RESEARCH_PLAN.md`, `docs/EXPERIMENT_PROTOCOL.md`, `docs/LIMITATIONS.md`, `docs/ARCHITECTURE.md`, `datasets/README.md`, `README.md`, `experiments/protocols/phase10-held-out-protocol.md`.
- Tests: `tests/unit/test_evaluation_engine.py`.
- Version `0.10.0`. Phases 1–9 preserved. Phase 11 not started.
- On this Phase 10 host, PyPI egress blocked Z3/pytest install; held-out measurements labeled **unavailable** (no fabricated numbers). Egress allowlist for `pypi.org`, `files.pythonhosted.org`, and `pypi.python.org` requested again.

## Phase 9 — Security and resilience

Date: 2026-10-09

- Added `veriforge/security.py`: error classification (`ErrorClass` / `classify_error`), secret-safe `user_facing_error` / `sanitize_error_text`, controlled export path confinement (`controlled_export_path` / `resolve_under_root`), `dependency_review_snapshot` for locked pins.
- Hardened audit export destinations to stay under `experiments/exports/`; derived summaries reject path-traversal names; optional `controlled_root` for benchmark config saves.
- UI actions and audit/benchmark pages surface classified, secret-safe errors (including unexpected exceptions) without raw tracebacks.
- Docs: `docs/SECURITY.md` (threat model, §15 controls, dependency review, remaining limits — does **not** claim resistance to every attack); updated `docs/LIMITATIONS.md`, `docs/ARCHITECTURE.md`.
- Tests: `tests/unit/test_security.py`, `tests/adversarial/test_security_resilience.py`; audit export path test updated for confinement.
- Version `0.9.0`. Phases 1–8 preserved. Phase 10 not started.
- Full suite execution on this Phase 9 host was blocked by PyPI egress (`UNEXPECTED_EOF_WHILE_READING` / `SSLEOFError` to `pypi.org`). No invented pass/fail counts. Egress allowlist for `pypi.org`, `files.pythonhosted.org`, and `pypi.python.org` requested.

## Phase 8 — Streamlit interface

Date: 2026-10-09

- Added Streamlit research UI: `veriforge/app.py` entry; `veriforge/ui/` with `catalog.py`, `presentation.py` (no Streamlit), `actions.py` (engine orchestration, no Streamlit), `components.py`, `visualizations.py`, `pages.py`.
- Six pages per §14: Expression Workbench; Verification Explorer; Fuzzing and Mutation Lab; Benchmark Lab; Research Dashboard; Audit and Reproducibility.
- Honesty rules encoded in presentation helpers: UNKNOWN/timeout never labeled equivalent; charts require completed-run measurements; unavailable features show explicit unavailable states; synthetic mutations labeled as artificial.
- Launch helper: `scripts/run_ui.py` (default port 8513).
- Dependencies: `streamlit==1.41.1`, `plotly==5.24.1`, `pandas==2.2.3` pinned in `pyproject.toml` / `requirements.lock` (transitive resolution not refreshed on this host due to PyPI egress).
- Tests: `tests/unit/test_ui_presentation.py`, `tests/unit/test_ui_actions.py`.
- Version `0.8.0`. Docs / `PROJECT_STATUS.md` / `README.md` updated. Phases 1–7 preserved. Phase 9 not started.
- Full suite execution on this Phase 8 host was blocked by PyPI egress (`SSLEOFError` to `pypi.org`). No invented pass/fail counts.

## Phase 7 — Audit and storage

Date: 2026-10-09

- Added `veriforge/audit_engine.py`: §13 optimization-run records (original input, normalized representation, semantic configuration, applicable rules, accepted/rejected transformations, verification query artifacts, solver status, counterexamples, timings, errors, run id, software/configuration versions); configuration fingerprints; run history; JSON/CSV audit export with `result_link`; secret and unnecessary personal-data redaction; replay from recorded configuration; storage integrity checks; derived summaries written under `experiments/reports/` only.
- Extended `veriforge/storage/`: `repositories.py` (`AuditRepository`), `migrations/phase7.py` (SQLite `optimization_runs`, `audit_events`, `schema_migrations`).
- Models: `AuditEvent`, `AuditEventKind`, `OptimizationRunRecord`, `ExportFormat`, `IntegrityReport`, `IntegrityIssue`, `IntegrityStatus`, `AuditExportResult`; `ObservationKind.OPTIMIZATION_RUN` / `AUDIT_EVENT`; `AuditError`.
- Tests: `tests/unit/test_audit_engine.py` (integrity, export, redaction, replay, raw/derived separation).
- Version `0.7.0`. Docs / `PROJECT_STATUS.md` / `README.md` updated. Phases 1–6 preserved. No Streamlit UI. Phase 8 not started.
- Phase 6 warm-host evidence recorded in `PROJECT_STATUS.md`: **256 passed, 0 failed, 0 skipped**.
- Full suite execution on this Phase 7 host was blocked by PyPI egress (`SSLEOFError` to `pypi.org`); `pip install -e . --no-deps` installed the package but `pytest`/`z3`/`hypothesis` are absent. No invented pass/fail counts.

## Phase 6 — Benchmark engine

Date: 2026-10-09

- Added `veriforge/benchmark_engine.py`: independent §10 timings (parse, optimize, candidate generation, translation, solver, end-to-end verification, original vs optimized execution); warmups; repeated trials; fixed seeds; timeout policy; environment recording; raw observation persistence; medians and variability; reproduction from saved configuration with nondeterminism disclosure.
- Added `verify_equivalence_timed` / `TimedVerificationResult` so translation and solver times are never collapsed into one duration field.
- Models: `BenchmarkConfiguration`, `BenchmarkMeasurement`, `BenchmarkReport`, `TimingStatistic`, `BenchmarkRateSummary`, `EnvironmentRecord`, `WarmupPolicy`, `TimeoutPolicy`; `ObservationKind.BENCHMARK_TIMING`.
- Script: `scripts/run_benchmarks.py` (development partition engine validation only; not a research conclusion).
- §10.2 guard: `assert_no_spurious_execution_speedup_claim` rejects claims that infer execution speedup from shorter expressions or faster solver returns alone.
- Held-out final evaluation as a research conclusion is refused by `run_benchmark`.
- Version `0.6.0`. Docs / `PROJECT_STATUS.md` / `README.md` updated. Phases 1–5 preserved. No Streamlit UI.
- Tests added: `tests/unit/test_benchmark_engine.py`. Full suite execution on the Phase 6 host was blocked by PyPI egress; an explicit retry still failed (`SSL_ERROR_SYSCALL` to `pypi.org`; see `PROJECT_STATUS.md`). No invented pass/fail counts.

## Phase 5 — Experimental framework

Date: 2026-10-09

- Froze the initial research protocol: `docs/RESEARCH_PLAN.md` (hypotheses remain hypotheses) and `docs/EXPERIMENT_PROTOCOL.md` (protocol `0.5.0`).
- Added `veriforge/dataset_engine.py`: versioned partitions, §9.4 metadata, near-duplicate leakage controls, controlled-mix labeling.
- Seed datasets under `datasets/development/` and `datasets/held_out/` (version `0.5.0`); `datasets/README.md`; generator `scripts/seed_phase5_datasets.py`.
- Artificial 90/10 mix recorded as a controlled configuration (`ARTIFICIAL_90_10_MIX`), not real-world prevalence.
- Added `veriforge/experiment_engine.py`: run identifiers, configuration fingerprints, baseline catalog (§9.3), metric calculations with results-by-class.
- Added `veriforge/storage/`: SQLite experiment-run index + filesystem raw observation JSON under `experiments/raw/`.
- Models: `DatasetMetadata`, `DatasetCase`, `ExperimentRun`, `RawObservation`, `MetricSummary`, baselines, controlled mix, and related enums.
- Tests: `tests/unit/test_dataset_engine.py`, `tests/unit/test_experiment_engine.py` (including known-case metric fixtures).
- **No held-out evaluation run.** No Streamlit UI. No Phase 6 benchmark engine.
- Tests run: **245 passed, 0 failed, 0 skipped** (`python3 -m pytest -v`).
- Phases 6–12 not started.

## Phase 4 — Adversarial validation

Date: 2026-10-09

- Added isolated mutation module `veriforge/fuzzer_suite.py` (§7.2): labeled artificial mutations, fixed seeds (`DEFAULT_MUTATION_SEED`), `mutation_id` + `generation_method`, never mixed into production rules, never bypasses verification.
- EVALUATION_ONLY harness (`analyze_mutation` / `mutate_and_analyze`) may inspect deliberately incorrect candidates; `accepted_into_production` is always False. Production `optimize()` still rejects `EVALUATION_ONLY`.
- Models: `MutationCategory`, `MutationRecord`, `MutationAnalysisResult`.
- Hypothesis property tests under `tests/properties/` (parser, semantics, verifier, optimizer).
- Differential tests against the reference evaluator (`tests/properties/test_differential.py`).
- Adversarial / isolation / regression suites: `tests/adversarial/`, `tests/regression/test_mutation_gate.py`, `tests/unit/test_fuzzer_suite.py`.
- Dev dependency: `hypothesis` (pinned in `requirements.lock`).
- Updated `docs/SEMANTICS.md`, `docs/ARCHITECTURE.md`, `docs/FORMAL_MODEL.md`, `docs/LIMITATIONS.md`, `README.md`, and `PROJECT_STATUS.md`.
- Tests run: **230 passed, 0 failed, 0 skipped** (`python3 -m pytest -v`).
- Phases 5–12 not started. No Streamlit UI, benchmarks, experiment framework, or research datasets beyond Phase 4 test needs.

## Phase 3 — Conservative optimizer

Date: 2026-10-09

- Added `veriforge/optimizer_engine.py`: verification-guided pipeline (parse → IR → select rules → candidate → record preconditions → verify vs original → accept/reject → full trace).
- Initial identity-preserving production rules, each validated under Mode A and Mode B: `x+0→x`, `x-0→x`, `x*1→x`, `x*0→0`.
- Extended models with `OptimizationRule`, `TransformationStep`, `OptimizationResult`, `CorrectnessPolicy`, `VerificationPolicy`, and `CandidateDecision`.
- Added `OptimizerError`; `EVALUATION_ONLY` is modeled but rejected by `optimize()` until the Phase 4 mutation harness exists.
- Acceptance gated on `EQUIVALENT_WITHIN_MODEL` only; `COUNTEREXAMPLE_FOUND`, `UNKNOWN`, `TIMEOUT`, and error statuses are recorded as rejections.
- Tests: `tests/unit/test_optimizer.py` and `tests/regression/test_optimizer_acceptance_gate.py`.
- Updated `docs/SEMANTICS.md`, `docs/ARCHITECTURE.md`, `docs/FORMAL_MODEL.md`, `docs/LIMITATIONS.md`, `README.md`, and `PROJECT_STATUS.md`.
- Tests run: **181 passed, 0 failed, 0 skipped** (`python3 -m pytest -v`).
- Phases 4–12 not started. No Streamlit UI, mutation module, benchmarks, or datasets.

## Phase 2 — Formal verification

Date: 2026-10-09

- Added `veriforge/verifier_engine.py`: IR → Z3 translation (Mode A `Int`, Mode B `BitVec`), existential difference query, explicit result classification, counterexample extraction and reference-evaluator validation.
- Extended `models` / `exceptions` with `VerificationStatus`, `VerificationResult`, `Counterexample`, `TranslationError`, and `VerificationEngineError`.
- Pinned runtime dependency `z3-solver==5.1.0.0` in `pyproject.toml` and `requirements.lock` (clean install path: `pip install -e ".[dev]"`).
- Added `tests/unit/test_verifier.py` for translation, mode selection, boundaries, timeouts, UNKNOWN/unsupported/errors, counterexample reconstruction, constants/variables, and incorrect candidates.
- Documented the encoded query and TCB in `docs/FORMAL_MODEL.md`; updated `docs/SEMANTICS.md`, `docs/ARCHITECTURE.md`, `docs/LIMITATIONS.md`, `README.md`, and `PROJECT_STATUS.md`.
- Tests run: **124 passed, 0 failed, 0 skipped** (`python3 -m pytest -v`).
- Phases 3–12 not started at Phase 2 close. No Streamlit UI, optimizer production path, benchmarks, datasets, or mutation modules.

## Phase 1 — Semantic foundation

Date: 2026-10-09

- Locked Mode B, literal, and resource-limit decisions into `docs/SEMANTICS.md`.
- Implemented package `veriforge` with `config`, `models`, `exceptions`, `parser_engine`, `semantics`, and `reference_evaluator`.
- Safe parsing via Python's `ast` module; no `eval`/`exec` on user input.
- Mode A (unbounded integers) and Mode B (unsigned modular wrap, default width 32) with fail-closed out-of-range literals.
- Added `pyproject.toml`, `requirements.lock`, `README.md`, and pytest suite under `tests/unit/`.
- Hand-checked semantic and parser tests run: **84 passed, 0 failed, 0 skipped** (`python3 -m pytest -v`).
- Updated `PROJECT_STATUS.md`, `docs/ARCHITECTURE.md`, `docs/LIMITATIONS.md`, and this changelog.
- Phases 2–12 not started at Phase 1 close.

## Phase 0 — Repository audit and implementation plan

Date: 2026-10-09

- Inspected the repository at commit `3d40c700c971e2da2e65f8a08e7b05afeeceeed3` (`Initialize project`). The commit tree `4b825dc642cb6eb9a060e54bf8d69288fbee4904` was empty. No source, configuration, tests, or dependency manifest was present.
- Recorded baseline test status from that inspection. No tests were run, because no test suite or test configuration exists and `pytest` is not installed for the host interpreter.
- Added the Phase 0 audit and the specified contracts for later phases: `PROJECT_STATUS.md`, `docs/ARCHITECTURE.md`, `docs/SEMANTICS.md`, `docs/RESEARCH_PLAN.md`, and `docs/LIMITATIONS.md`.
- No application code was added. Phases 1–12 have not started. No experimental results, citations, or completeness claims are included.
