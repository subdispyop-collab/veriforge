# VERIFORGE

Formal-verification-guided arithmetic expression optimization and research platform.

**Current phase:** Phase 8 — Streamlit interface (six research pages).

Phases 9–12 are not implemented. **No held-out evaluation has been run as a research conclusion.**

## Requirements

- Python 3.11 or newer (developed on 3.12)
- Runtime: `z3-solver==5.1.0.0`, `streamlit==1.41.1`, `plotly==5.24.1`, `pandas==2.2.3` (pinned in `pyproject.toml` / `requirements.lock`)
- Dev: `pytest`, `hypothesis` (see `requirements.lock`)

## Setup

```bash
python3 -m pip install -e ".[dev]"
```

If site-packages already provide the pinned packages but PyPI is unreachable:

```bash
python3 -m pip install -e . --no-deps
```

## Run the Streamlit interface

```bash
python3 scripts/run_ui.py --port 8513
# equivalent:
# streamlit run veriforge/app.py --server.port 8513 --server.address 127.0.0.1
```

Default bind is `127.0.0.1:8513` (uncommon port; Streamlit’s default 8501 is also acceptable if documented). Requires `streamlit` (and optionally `plotly`/`pandas` for charts).

Pages:

1. Expression Workbench
2. Verification Explorer
3. Fuzzing and Mutation Lab
4. Benchmark Lab
5. Research Dashboard
6. Audit and Reproducibility

Application logic stays in engine modules and `veriforge/ui/actions.py` / `presentation.py`. Streamlit is presentation only. UNKNOWN and timeout are never labeled equivalent. Charts show only completed-run measurements.

## Run tests

```bash
python3 -m pytest
```

## Semantic modes

- **Mode A:** unbounded mathematical integers (Z3 `Int` sorts)
- **Mode B:** unsigned fixed-width bit-vectors (default width 32; Z3 `BitVec` sorts), modular wrap for `+`, `-`, `*`; literals outside `[0, 2^w-1]` are rejected

See `docs/SEMANTICS.md` for the full contract and `docs/FORMAL_MODEL.md` for the encoded equivalence query and TCB assumptions.

## Audit and storage (Phase 7)

Optimization runs persist the fields required by specification §13. Audit events export to JSON or CSV and link to the results they describe. Secrets and unnecessary personal data are redacted. Replay uses the recorded configuration. Raw records stay under `experiments/raw/`; derived summaries under `experiments/reports/`.

## Benchmark engine (Phase 6)

Measures section-10 quantities **separately** (solver latency is not expression execution time). Reports use medians and variability. Never claims execution speedup from a shorter expression or a faster solver alone.

```bash
python3 scripts/run_benchmarks.py --case-id dev-hand-001 --trials 2 --warmup 1 \
  --save-config /tmp/veriforge-bench-config.json --json-summary /tmp/veriforge-bench-summary.json
```

Development datasets validate the engine only. Timing nondeterminism is disclosed on every configuration and report.

## Research protocol (Phase 5, still frozen)

- Preregistered plan: `docs/RESEARCH_PLAN.md` (hypotheses are not findings)
- Frozen protocol: `docs/EXPERIMENT_PROTOCOL.md` (version `0.5.0`)
- Benchmark protocol id: `veriforge-phase6-benchmark-protocol` (version `0.6.0`)
- Audit protocol id: `veriforge-phase7-audit-protocol` (version `0.7.0`)
- Datasets: `datasets/development/`, `datasets/held_out/` — see `datasets/README.md`

Creating a run does not execute held-out evaluation. An artificial 90/10 mix, if used, is a controlled configuration — not real-world prevalence.

## Optimization (verification-guided)

```python
from veriforge import SemanticConfiguration, SemanticMode, optimize

cfg = SemanticConfiguration(mode=SemanticMode.MODE_A)
result = optimize("(x + 0) * 1", cfg)
print(result.accepted.source)  # x
```

Default policy is conservative: each candidate must receive `EQUIVALENT_WITHIN_MODEL` before acceptance.

## Adversarial validation (EVALUATION_ONLY harness)

Artificial mutations live only in `veriforge.fuzzer_suite`. They are labeled, seeded, and never mixed into production rules.

## Verification

```python
from veriforge import SemanticConfiguration, SemanticMode, verify_equivalence

cfg = SemanticConfiguration(mode=SemanticMode.MODE_A)
result = verify_equivalence("x + 1", "x + 2", cfg)
print(result.status)  # VerificationStatus.COUNTEREXAMPLE_FOUND
```

Result states are explicit and never collapsed to a Boolean.

## Safety

User input is parsed with Python’s `ast` module only. `eval` and `exec` are never used on user input.
