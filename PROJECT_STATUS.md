# PROJECT_STATUS

Status date: 2026-10-09  
Current phase: Phase 9 (security and resilience) — implemented  
Phases 10–12: not started

This file records what is in the git checkout and the plan required by the controlling specification. The controlling specification was read and was not modified.

## Current state

Phase 9 is present on top of the preserved Phases 1–8: §15 controls enforced and tested (AST validation, resource limits, solver timeouts, safe/controlled file handling, input-size restrictions, no arbitrary code execution); errors classified with secret-safe user-facing messages; threat model and remaining limitations in `docs/SECURITY.md` and `docs/LIMITATIONS.md`; dependency review against locked pins. **Does not claim resistance to every attack. Phase 10 not started. No held-out evaluation as a research conclusion.**

Observed during Phase 9 work:

- Base branch: `cursor/phase-8-streamlit-ui-6fd4`.
- Work branch: `cursor/phase-9-security-resilience-6104`.
- Host interpreter: Python 3.12.3 at `/usr/bin/python3`.
- Project pin: `requires-python = ">=3.11"`; runtime deps unchanged (`z3-solver==5.1.0.0`, `streamlit==1.41.1`, `plotly==5.24.1`, `pandas==2.2.3`); version `0.9.0`.
- Test command intended: `python3 -m pytest -v` after `python3 -m pip install -e ".[dev]"`.
- On this Phase 9 host, PyPI egress remains blocked (`UNEXPECTED_EOF_WHILE_READING` / `SSLEOFError` to `pypi.org`). Egress allowlist additions for `pypi.org`, `files.pythonhosted.org`, and `pypi.python.org` were requested again. See Current test status.

## Implemented features

Phase 1–8 (preserved): see prior `PROJECT_STATUS` history and `CHANGELOG.md`.

Phase 6 warm-host evidence (recorded for continuity; not re-run on this Phase 9 VM):

- Agent `bc-97807782-c342-5e4d-8c5d-f29ef6070204` on a Phase 5 warm host.
- Result: **256 passed, 0 failed, 0 skipped** in 3.34s (Phase 6 tip `e86f158`).

Phase 9:

- `veriforge/security.py` — `ErrorClass`, `classify_error`, `user_facing_error` / `sanitize_error_text`, `controlled_export_path` / `resolve_under_root`, `dependency_review_snapshot`.
- Audit exports confined under `experiments/exports/`; derived summaries reject path traversal; UI actions use classified secret-safe errors.
- Docs: `docs/SECURITY.md` (threat model, controls, dependency review, remaining limits); `docs/LIMITATIONS.md` / `docs/ARCHITECTURE.md` updated.
- Tests: `tests/unit/test_security.py`, `tests/adversarial/test_security_resilience.py`; audit export test updated for controlled paths.
- Version `0.9.0`. Phases 1–8 preserved.

## Unimplemented features

Everything from Phase 10 onward, including:

- Literature review and held-out evaluation execution (Phase 10).
- Independent review (Phase 11) and release checklist (Phase 12).
- Research evidence ledger (section 17) as a completed product.

## Known defects

Known gaps that are not product defects of implemented Phase 9 code:

- No continuous integration configuration exists.
- Static type checking and Ruff were not run as a project gate in Phase 9.
- Baseline 5 (external tool) remains not selected.
- On this Phase 9 VM, `pytest` / `z3-solver` / `hypothesis` / `streamlit` / `plotly` / `pandas` are unavailable without PyPI egress (not a VERIFORGE code defect).
- Streamlit/plotly/pandas transitive dependency pins were not re-resolved on this host (same as Phase 8).
- Secret redaction is pattern-based; novel formats may slip through (documented).
- Later-phase modules do not exist; their defects cannot be assessed.

## Current test status

### Phase 6 warm-host suite (historical evidence for prior phase)

| Metric | Count |
| --- | --- |
| Passed | 256 |
| Failed | 0 |
| Skipped | 0 |

### Phase 9 on this host

Commands attempted:

```text
python3 -m pip install -e ".[dev]"   # blocked: SSL EOF / UNEXPECTED_EOF to pypi.org
python3 -c "import urllib.request; urllib.request.urlopen('https://pypi.org/simple/pytest/')"
# PYPI_BLOCKED
```

| Metric | Count |
| --- | --- |
| Passed | unavailable (deps not installable on this host) |
| Failed | unavailable |
| Skipped | unavailable |

Blocker: restricted network egress prevents HTTPS to `pypi.org` and `files.pythonhosted.org`. No pytest pass/fail counts were invented for Phase 9 on this host. Suites added: `tests/unit/test_security.py`, `tests/adversarial/test_security_resilience.py`. Security helpers that do not import z3 are smoke-checked where the import graph allows.

## Decisions requiring later research

Locked and approved (Phase 1; do not reopen without asking): Mode B unsigned wrap; Python `ast` integer spellings without bools; numeric resource-limit defaults.

Still open for later phases: external baseline tool; division/remainder/shift conventions; Mode B signedness for future operators; literature review (Phase 10). Streamlit/plotly/pandas direct pins are recorded; transitive lock refresh awaits egress.

## Phase-by-phase implementation plan

### Phases 0–8

Status: satisfied for implementation (see `CHANGELOG.md`). Phase 6 warm-host tests **256 passed**. Phase 7–8 code acceptance met; pytest on fresh VMs was egress-blocked (documented).

### Phase 9 — Security and resilience

Objective: enforce and test §15 controls; classify errors without secret leakage; document threat model and remaining limitations; review locked dependencies.

Acceptance criteria:

- §15 controls in scope enforced and tested: **met** (code + authored tests; pytest execution on this host blocked by egress).
- Errors classified; no secret leakage: **met** (`ErrorClass` / `user_facing_error`; audit redaction preserved).
- Threat model + remaining limitations documented: **met** (`docs/SECURITY.md`, `docs/LIMITATIONS.md`).
- Do not claim resistance to every attack: **met** (explicit in SECURITY.md / LIMITATIONS.md / this status).
- Dependency review on locked versions; note if PyPI blocked: **met**.
- Preserve Phases 1–8; update status/docs/changelog: **met**.
- Run tests with real pass/fail on this host: **not met on this host** (PyPI egress).

### Phases 10–12

Not started. See the controlling specification section 19.

## Highest-risk technical assumptions

1. Encoder correctness.
2. Modes remain distinct.
3. UNKNOWN/timeout never treated as equivalence.
4. Mutation isolation.
5. Dependence of observations.
6. Reproducibility limits (timing nondeterminism disclosed).
7. Dependency compatibility for the Streamlit stack (pins recorded; clean install not verified on this host).
8. Egress / environment builds must provide `z3-solver`, `pytest`, `hypothesis`, `streamlit`, `plotly`, and `pandas` for CI and agents.
9. Streamlit pages must continue to call engines via `actions` / presentation helpers rather than invoking the solver ad hoc.
10. Pattern-based secret redaction and path confinement cover the intended UI/audit surfaces, not every possible caller bypass.

## Phase 9 acceptance checklist

- AST validation / resource limits / timeouts / controlled exports / no eval-exec: yes (enforced; tests authored).
- Errors classified; secret-safe messages: yes.
- Threat model + limitations docs: yes.
- No claim of total attack resistance: yes.
- Dependency review from lock pins; egress blocker recorded: yes.
- Docs / status / changelog updated; Phases 1–8 preserved: yes.
- Tests executed with real pass/fail on this host: **no — PyPI egress blocked**.
