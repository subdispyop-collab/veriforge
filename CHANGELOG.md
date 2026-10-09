# Changelog

## Phase 2 — Formal verification

Date: 2026-10-09

- Added `veriforge/verifier_engine.py`: IR → Z3 translation (Mode A `Int`, Mode B `BitVec`), existential difference query, explicit result classification, counterexample extraction and reference-evaluator validation.
- Extended `models` / `exceptions` with `VerificationStatus`, `VerificationResult`, `Counterexample`, `TranslationError`, and `VerificationEngineError`.
- Pinned runtime dependency `z3-solver==5.1.0.0` in `pyproject.toml` and `requirements.lock` (clean install path: `pip install -e ".[dev]"`).
- Added `tests/unit/test_verifier.py` for translation, mode selection, boundaries, timeouts, UNKNOWN/unsupported/errors, counterexample reconstruction, constants/variables, and incorrect candidates.
- Documented the encoded query and TCB in `docs/FORMAL_MODEL.md`; updated `docs/SEMANTICS.md`, `docs/ARCHITECTURE.md`, `docs/LIMITATIONS.md`, `README.md`, and `PROJECT_STATUS.md`.
- Tests run: **124 passed, 0 failed, 0 skipped** (`python3 -m pytest -v`).
- Phases 3–12 not started. No Streamlit UI, optimizer production path, benchmarks, datasets, or mutation modules.

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
