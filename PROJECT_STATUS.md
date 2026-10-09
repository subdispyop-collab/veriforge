# PROJECT_STATUS

Status date: 2026-10-09  
Current phase: Phase 8 (Streamlit interface) — implemented  
Phases 9–12: not started

This file records what is in the git checkout and the plan required by the controlling specification. The controlling specification was read and was not modified.

## Current state

Phase 8 is present on top of the preserved Phases 1–7: six Streamlit pages (Expression Workbench, Verification Explorer, Fuzzing and Mutation Lab, Benchmark Lab, Research Dashboard, Audit and Reproducibility). Application logic stays outside Streamlit presentation (`veriforge/ui/` helpers + `veriforge/app.py` entry). Active semantic mode, bit width where applicable, and assumptions are shown. UNKNOWN and timeout are never labeled equivalent. Charts show only completed-run measurements; missing features show unavailable states. **No held-out final evaluation as a research conclusion. Phase 9 not started.**

Observed during Phase 8 work:

- Base branch: `cursor/phase-7-audit-storage-67ba`.
- Work branch: `cursor/phase-8-streamlit-ui-6fd4`.
- Host interpreter: Python 3.12.3 at `/usr/bin/python3`.
- Project pin: `requires-python = ">=3.11"`; runtime deps `z3-solver==5.1.0.0`, `streamlit==1.41.1`, `plotly==5.24.1`, `pandas==2.2.3`; version `0.8.0`.
- Test command intended: `python3 -m pytest -v` after `python3 -m pip install -e ".[dev]"`.
- On this Phase 8 host, PyPI egress remains blocked (`SSLEOFError` to `pypi.org`). Egress allowlist additions for `pypi.org`, `files.pythonhosted.org`, and `pypi.python.org` were requested. See Current test status.

## Implemented features

Phase 1–7 (preserved): see prior `PROJECT_STATUS` history and `CHANGELOG.md`.

Phase 6 warm-host evidence (recorded for continuity; not re-run on this Phase 8 VM):

- Agent `bc-97807782-c342-5e4d-8c5d-f29ef6070204` on a Phase 5 warm host.
- Result: **256 passed, 0 failed, 0 skipped** in 3.34s (Phase 6 tip `e86f158`).

Phase 8:

- `veriforge/app.py` — Streamlit entry.
- `veriforge/ui/` — `catalog.py`, `presentation.py` (honesty helpers, no Streamlit), `actions.py` (engine orchestration, no Streamlit), `components.py`, `visualizations.py`, `pages.py` (six pages).
- `scripts/run_ui.py` — launch helper (default port **8513**).
- Interface tests: `tests/unit/test_ui_presentation.py`, `tests/unit/test_ui_actions.py`.
- Dependencies pinned in `pyproject.toml` / `requirements.lock` (streamlit/plotly/pandas pins intended; transitive resolution blocked by egress on this host).
- Docs / status / changelog / README updated. Phases 1–7 preserved.

## Unimplemented features

Everything from Phase 9 onward, including:

- Full security review, threat model, literature review, and research evidence ledger.
- Held-out evaluation execution (Phase 10).
- A release checklist satisfied by executed checks for the whole product.

## Known defects

Known gaps that are not product defects of implemented Phase 8 code:

- No continuous integration configuration exists.
- Static type checking and Ruff were not run as a project gate in Phase 8.
- Baseline 5 (external tool) remains not selected.
- On this Phase 8 VM, `pytest` / `z3-solver` / `hypothesis` / `streamlit` / `plotly` / `pandas` are unavailable without PyPI egress (not a VERIFORGE code defect).
- Streamlit/plotly/pandas transitive dependency pins were not re-resolved on this host.
- Later-phase modules do not exist; their defects cannot be assessed.

## Current test status

### Phase 6 warm-host suite (historical evidence for prior phase)

| Metric | Count |
| --- | --- |
| Passed | 256 |
| Failed | 0 |
| Skipped | 0 |

### Phase 8 on this host

Commands attempted:

```text
python3 -m pip install -e ".[dev]"   # blocked: SSLEOFError to pypi.org
python3 -m pip install streamlit plotly pandas  # blocked: same
python3 -m pip install -e . --no-deps  # used when possible for editable package only
```

| Metric | Count |
| --- | --- |
| Passed | unavailable (deps not installable on this host) |
| Failed | unavailable |
| Skipped | unavailable |

Blocker: restricted network egress prevents HTTPS to `pypi.org` and `files.pythonhosted.org`. No pytest pass/fail counts were invented for Phase 8 on this host. Suites added: `tests/unit/test_ui_presentation.py`, `tests/unit/test_ui_actions.py`. Presentation helpers are independently smoke-checked without Streamlit where the import graph allows.

## Decisions requiring later research

Locked and approved (Phase 1; do not reopen without asking): Mode B unsigned wrap; Python `ast` integer spellings without bools; numeric resource-limit defaults.

Still open for later phases: external baseline tool; division/remainder/shift conventions; Mode B signedness for future operators; literature review (Phase 10). Streamlit/plotly/pandas direct pins are recorded; transitive lock refresh awaits egress.

## Phase-by-phase implementation plan

### Phases 0–7

Status: satisfied for implementation (see `CHANGELOG.md`). Phase 6 warm-host tests **256 passed**. Phase 7 code acceptance met; Phase 7 pytest on fresh VM was egress-blocked (documented).

### Phase 8 — Streamlit interface

Objective: six research pages; logic outside Streamlit; honest labels; no fabricated charts.

Acceptance criteria:

- Application logic outside Streamlit presentation: **met** (`presentation.py` / `actions.py` + engines; Streamlit only in app/components/pages/visualizations).
- Six pages exist: **met**.
- Active semantic mode, width where applicable, assumptions visible: **met**.
- UNKNOWN and timeout never labeled equivalent: **met** (presentation helpers + tests).
- Pages show only measurements from completed runs; missing features show unavailable: **met**.
- Interface tests for those behaviors: **authored**; **not executed via pytest on this host** (egress).
- streamlit/plotly/pandas added with pins: **met** (direct pins; network install not verified here).
- Phases 1–7 preserved; docs/status/changelog/README updated: **met**.

### Phases 9–12

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

## Phase 8 acceptance checklist

- Logic outside Streamlit: yes.
- Six pages: yes.
- Semantic mode / width / assumptions visible: yes.
- UNKNOWN/timeout ≠ equivalent: yes (helpers + tests authored).
- No fabricated charts; unavailable states: yes.
- Interface tests authored: yes.
- Dependencies pinned: yes (install blocked by egress).
- Docs / status / changelog updated; Phases 1–7 preserved: yes.
- Tests executed with real pass/fail on this host: **no — PyPI egress blocked**.
