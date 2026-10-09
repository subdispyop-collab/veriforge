# Changelog

## Phase 1 — Semantic foundation

Date: 2026-10-09

- Locked Mode B, literal, and resource-limit decisions into `docs/SEMANTICS.md`.
- Implemented package `veriforge` with `config`, `models`, `exceptions`, `parser_engine`, `semantics`, and `reference_evaluator`.
- Safe parsing via Python's `ast` module; no `eval`/`exec` on user input.
- Mode A (unbounded integers) and Mode B (unsigned modular wrap, default width 32) with fail-closed out-of-range literals.
- Added `pyproject.toml`, `requirements.lock`, `README.md`, and pytest suite under `tests/unit/`.
- Hand-checked semantic and parser tests run: **84 passed, 0 failed, 0 skipped** (`python3 -m pytest -v`).
- Updated `PROJECT_STATUS.md`, `docs/ARCHITECTURE.md`, `docs/LIMITATIONS.md`, and this changelog.
- Phases 2–12 not started. No Streamlit, Z3 verifier, optimizer, benchmarks, datasets, or mutation modules.

## Phase 0 — Repository audit and implementation plan

Date: 2026-10-09

- Inspected the repository at commit `3d40c700c971e2da2e65f8a08e7b05afeeceeed3` (`Initialize project`). The commit tree `4b825dc642cb6eb9a060e54bf8d69288fbee4904` was empty. No source, configuration, tests, or dependency manifest was present.
- Recorded baseline test status from that inspection. No tests were run, because no test suite or test configuration exists and `pytest` is not installed for the host interpreter.
- Added the Phase 0 audit and the specified contracts for later phases: `PROJECT_STATUS.md`, `docs/ARCHITECTURE.md`, `docs/SEMANTICS.md`, `docs/RESEARCH_PLAN.md`, and `docs/LIMITATIONS.md`.
- No application code was added. Phases 1–12 have not started. No experimental results, citations, or completeness claims are included.
