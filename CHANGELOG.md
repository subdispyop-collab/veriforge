# Changelog

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
