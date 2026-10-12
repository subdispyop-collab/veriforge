# VERIFORGE

Formal-verification-guided arithmetic expression optimization and research platform.

## Measured results

Recorded counts from `research/PART15_AUDIT.md`, `research/FINAL_RESEARCH_REPORT.md`, `research/RESULTS.md`, `research/METHOD_DISCOVERY_REPORT.md`, and `research/CANONICAL_WIDE_RESULTS.md`.

The pytest record in `research/PART15_AUDIT.md` is pytest 9.1.1 on Python 3.12.3: 383 tests, 0 failures, 0 errors, 0 skipped, exit 0. That audit and `research/FINAL_RESEARCH_REPORT.md` state that this suite was not rerun. The recorded run used Hypothesis 6.155.7 and Z3 4.8.17.

The assurance set has 463 unique pairs and 27 families. Testing false equivalences on the held-out labels were 0/54 at budgets 10, 100, 1,000, and 10,000. Against the labeling oracle, false equivalence was 0/96 for Z3 4.8.17, CVC5 1.3.2, and Bitwuzla 0.8.2. On all 463 pairs, timeout 5 seconds, the Z3 census was 318 `equivalent_within_model`, 96 `counterexample_found`, 8 `invalid_input`, 41 `unsupported`, 0 `unknown`, and 0 `timeout`. CVC5 matched those counts.

The confirmatory set has 72 pairs in 12 families. Oracle labels were equivalent 32, non_equivalent 33, and not_computed 7. Z3 4.8.17 and CVC5 1.3.2 false equivalence was 0/33 pairs, 0/12 in Mode A, and 0/21 in Mode B. Correct acceptance was 32/32 and correct rejection was 33/33. The recorded H3 verdict is unresolved.

On `datasets/canonical_form_v1/cases.jsonl` (57 lines), the canonical checker returned `EQUIVALENT` on 9/9 width-1 pairs where integer coefficient comparison was the wrong semantics. False equivalence was 0/27 for that checker, for Z3 4.8.17, and for cvc5 1.3.2. Each was decisive on 57/57 pairs.

`research/CANONICAL_WIDE_RESULTS.md` records `veriforge-canonical-wide-v1` on `datasets/canonical_wide_v1/cases.jsonl` (105 lines), term cap 256. The record states that this wider study is not a new theorem and that the 57-pair study was not rewritten. False equivalence for the canonical checker, Z3 4.8.17, and cvc5 1.3.2 is 0/4 at width 1, 0/13 at width 2, 0/13 at width 4, 0/13 at width 8, and 0/13 at width 32. The control (widths 1, 2, and 4) is 0/30. The wide arm (widths 8 and 32) is 0/26. The full set is 0/56. The printed all-set Wilson lower endpoint `6.938893903907228e-18` is a floating-point residue of a zero numerator.

False rejection in that wider study is 0/17 at width 1, 0/8 at width 2, 0/7 at width 4, and 0/6 at width 8. Width 32 is 0/0, an empty denominator, not a zero rate. The control is 0/32, the wide arm is 0/6, and the full set is 0/38. Width 32 has no exhaustive `equivalent` label. Eight width-32 rows are `not_computed`, including seven on which the canonical checker returned `EQUIVALENT`. Those seven are not scored as correct acceptances and are not in the false-rejection denominator.

The decisive rate uses every row. The canonical checker is 19/21 at each width, 57/63 on the control, 38/42 on the wide arm, and 95/105 overall. Z3 and cvc5 are 21/21 at each width, 63/63 on the control, 42/42 on the wide arm, and 105/105 overall. Ten rows are canonical `UNKNOWN` with detail `term count 462 exceeds 256`. `UNKNOWN` is not equivalence. The degree-6 self-comparisons at widths 1 and 2 are ground-truth `equivalent` and canonical `UNKNOWN`. They are non-decisive.

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
