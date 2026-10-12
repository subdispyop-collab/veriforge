# VERIFORGE

Formal-verification-guided arithmetic expression optimization and research platform.

## Measured results

- pytest 9.1.1: 383 tests, 0 failures, 0 errors, 0 skipped (`research/PART15_AUDIT.md`).
- Assurance set: 463 pairs, false equivalence 0/96. Testing false equivalences 0/54 at budgets 10, 100, 1,000, and 10,000.
- Confirmatory v2: false equivalence 0/33, correct acceptance 32/32, correct rejection 33/33.
- Canonical 57-pair study: 9/9 width-1 cases decided `EQUIVALENT` where integer comparison was the wrong semantics; false equivalence 0/27 for the checker, Z3, and cvc5; decisive 57/57.
- Time, n=57 (`research/RESULTS.md`): canonical wall sum `0.007584139995742589` seconds, Z3 wall sum `0.3974383819877403` seconds, and cvc5 wall sum `0.2561598999782291` seconds. The canonical sum is about 52 times smaller than the Z3 wall sum on this set; these are small expressions, syntactic degree at most 2 and at most 3 variables, and no superiority test was preregistered.
- Wider study: false equivalence 0/56 overall and 0/26 on widths 8 and 32 (`research/CANONICAL_WIDE_RESULTS.md`).

Digests that match the hashes printed in the research reports are listed in `dataset_hashes.txt`.

**Version:** `1.0.0`.  
**Phase:** 12 — Release (final). §20 Definition of Done **met** via Phase 5 warm-host clean-venv attestation; see `docs/RELEASE_CHECKLIST.md`.  
**Final report:** `docs/FINAL_RESEARCH_REPORT.md`.

Held-out warm-host measurements are in `experiments/reports/phase10-held-out-evaluation.*`. On egress-blocked hosts a local re-run may be **unavailable** (never fabricate). VERIFORGE does **not** claim a novel formal method; see `docs/LITERATURE_REVIEW.md`. VERIFORGE does **not** claim resistance to every attack; see `docs/SECURITY.md`. Sample-limited H1/H2 support is **not** a general proof; see `docs/EVIDENCE_LEDGER.md`.

## Requirements

- Python 3.11 or newer (developed on 3.12)
- Runtime: `z3-solver==5.1.0.0`, `streamlit==1.41.1`, `plotly==5.24.1`, `pandas==2.2.3` (pinned in `pyproject.toml` / `requirements.lock`)
- Dev: `pytest`, `hypothesis` (see `requirements.lock`)

## Setup

```bash
python3 -m venv /tmp/veriforge-rc
source /tmp/veriforge-rc/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
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

Warm-host evidence used for release (§20 criterion 8): **359 passed, 0 failed, 0 skipped** on commit `6848fd4`. Authoring hosts without PyPI egress cannot re-run the suite until dependencies install.

## Reproduce the saved held-out experiment

```bash
python3 scripts/run_held_out_evaluation.py --seed 20261009 --timeout 5.0 \
  --execution-iterations 50 --trials 1
```

Prior successful warm-host fingerprint: `1b5a4a762b6485eca8668cc6e7dba93cd829246479cbeee00caf977c8fea5464`. Release docs: `docs/RELEASE_CHECKLIST.md`, `docs/FINAL_RESEARCH_REPORT.md`.

## Assurance experiment (research hardening)

Version stays `1.0.0`. The historical held-out file is unchanged. The new dataset, protocol hash, and scored run are under `research/` and `experiments/reports/assurance-v1/`.

```bash
python3 -m unittest tests.unit.test_research_hardening -v
python3 scripts/run_assurance_experiment.py
python3 scripts/judge_safety_demo.py
```

The experiment refuses to score held-out pairs unless `research/protocol_preregistration.json` matches the SHA-256 of `research/EXPERIMENT_PROTOCOL.md`. If `z3` is not installed, solver baselines are recorded as unavailable. This authoring host could not reach PyPI.

## Semantic modes

- **Mode A:** unbounded mathematical integers (Z3 `Int` sorts)
- **Mode B:** unsigned fixed-width bit-vectors (default width 32; Z3 `BitVec` sorts), modular wrap for `+`, `-`, `*`; literals outside `[0, 2^w-1]` are rejected

See `docs/SEMANTICS.md` for the full contract and `docs/FORMAL_MODEL.md` for the encoded equivalence query and TCB assumptions.

## Security (Phase 9)

- Threat model, enforced controls, dependency review, and remaining limits: `docs/SECURITY.md`
- Standing scientific/semantic limits: `docs/LIMITATIONS.md`
- Helpers: `veriforge/security.py` (classified errors, secret-safe messages, controlled export paths)
- User input and datasets are untrusted. Unsupported syntax fails closed. No `eval`/`exec` on user input.

## Audit and storage (Phase 7)

Optimization runs persist the fields required by specification §13. Audit events export to JSON or CSV and link to the results they describe. Secrets and unnecessary personal data are redacted. Export paths are confined under `experiments/exports/`. Replay uses the recorded configuration. Raw records stay under `experiments/raw/`; derived summaries under `experiments/reports/`.

## Benchmark engine (Phase 6)

Measures section-10 quantities **separately** (solver latency is not expression execution time). Reports use medians and variability. Never claims execution speedup from a shorter expression or a faster solver alone.

```bash
python3 scripts/run_benchmarks.py --case-id dev-hand-001 --trials 2 --warmup 1 \
  --save-config /tmp/veriforge-bench-config.json --json-summary /tmp/veriforge-bench-summary.json
```

Development datasets validate the engine only. Timing nondeterminism is disclosed on every configuration and report.

## Research protocol and Phase 10 evaluation

- Preregistered plan: `docs/RESEARCH_PLAN.md` (hypotheses are not findings)
- Frozen Phase 5 protocol: `docs/EXPERIMENT_PROTOCOL.md` (version `0.5.0`)
- Phase 10 held-out protocol: `experiments/protocols/phase10-held-out-protocol.md` (version `1.0.0`)
- Literature review: `docs/LITERATURE_REVIEW.md` (no novelty claim)
- Evidence ledger: `docs/EVIDENCE_LEDGER.md`
- Benchmark protocol id: `veriforge-phase6-benchmark-protocol` (version `0.6.0`)
- Audit protocol id: `veriforge-phase7-audit-protocol` (version `0.7.0`)
- Datasets: `datasets/development/`, `datasets/held_out/` — see `datasets/README.md`

```bash
python3 scripts/run_held_out_evaluation.py --seed 20261009
```

An artificial 90/10 mix, if used, is a controlled configuration — not real-world prevalence.

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
