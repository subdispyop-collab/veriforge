# VERIFORGE — Final research report (§22)

Software version: **`1.0.0rc1`**  
Report date (UTC): 2026-10-09  
Branch: `cursor/phase-12-release-b430`  
Base: `cursor/phase-11-independent-review-0667` @ `6848fd4`  
Companion: `docs/RELEASE_CHECKLIST.md` (§20), `docs/EVIDENCE_LEDGER.md` (§17)

Honesty: only results actually produced are reported. Unavailable items are labeled **unavailable**. Unsupported hypotheses are stated as such. **No novelty claim.**

---

## 1. Research question and hypotheses

**Question (§9.1):** Does SMT-based equivalence checking improve the detection and rejection of incorrect arithmetic rewrites, and what computational overhead does it introduce under a defined, restricted arithmetic model?

**Hypotheses (§9.2)** — statuses from warm-host held-out report (`experiments/reports/phase10-held-out-evaluation.json`, fingerprint `1b5a4a762b6485eca8668cc6e7dba93cd829246479cbeee00caf977c8fea5464`):

| ID | Hypothesis | Status |
| --- | --- | --- |
| H1 | Verification identifies incorrect candidates within the supported model when encoding and solver are correct | `supported_on_this_sample` (4/4 incorrect held-out case×baseline detections under verification-enabled **and** testing-only SMT paths; 2 unique NON_EQUIVALENT cases × 2 baselines; **not** a general proof) |
| H2 | Verification introduces measurable computational overhead | `supported_on_this_sample` (positive `solver_seconds`, n=14; host-specific magnitude) |
| H3 | Overhead and success rates vary by expression complexity and transformation category | `inconclusive_on_this_sample` → ledger **UNRESOLVED** |

Phase 12 authoring-host re-run of held-out evaluation: **unavailable** (`z3` not importable).

---

## 2. Implemented architecture

Modular Python package `veriforge/` with fail-closed parser, Mode A/B semantics, reference evaluator, Z3 verifier, verification-guided optimizer, EVALUATION_ONLY fuzzer, datasets/experiments/benchmarks/audit/evaluation engines, Streamlit UI (presentation separate from engines), and security helpers. See `docs/ARCHITECTURE.md`.

Phases 0–12 delivered as sequential research engineering milestones; Phase 12 is release attestation and documentation from actual behavior.

---

## 3. Supported grammar and semantic models

Documented in `docs/SEMANTICS.md` and locked Phase 1 decisions:

- Grammar (initial): integer literals (Python `ast` spellings; no bools), named variables, parentheses, `+` `-` `*`, unary `+/-`.
- **Mode A:** unbounded mathematical integers (Z3 `Int`).
- **Mode B:** unsigned modular bit-vectors, default width 32; literals outside `[0, 2^w-1]` rejected; unsigned only.
- Unsupported syntax fails closed. No `eval`/`exec` on user input.
- Resource limits: source 4096, AST nodes 256, nesting 32, Mode A literal bits 4096, solver timeout 5s (configurable).

---

## 4. Formal verification method

Encoded query (`docs/FORMAL_MODEL.md`): seek an assignment where original and candidate differ under the active mode. Classify Z3 outcomes as `EQUIVALENT_WITHIN_MODEL`, `COUNTEREXAMPLE_FOUND` (after reference-evaluator confirmation), `UNKNOWN`, `TIMEOUT`, or error. UNSAT is equivalence **within the encoded model**, not a proof of the application TCB.

---

## 5. Optimizer rules and preconditions

Four identity-preserving production rules (each mode-validated):

| Rule id | Rewrite |
| --- | --- |
| `identity.add_zero` | `x + 0 → x` |
| `identity.sub_zero` | `x - 0 → x` |
| `identity.mul_one` | `x * 1 → x` |
| `identity.mul_zero` | `x * 0 → 0` |

Default policy accepts a candidate only after `EQUIVALENT_WITHIN_MODEL`. Artificial mutations live only in `veriforge.fuzzer_suite` (EVALUATION_ONLY).

---

## 6. Testing and verifier-validation results

### Warm-host full suite (executed evidence)

| Item | Value |
| --- | --- |
| Branch / commit | `cursor/phase-11-independent-review-0667` @ `6848fd4` |
| Command | `python3 -m pytest` (warm host with deps) |
| Passed | **359** |
| Failed | **0** |
| Skipped | **0** |

Coverage includes unit, property, adversarial, and regression tests under `tests/`.

### Phase 12 authoring host

| Check | Result |
| --- | --- |
| `pip install -e ".[dev]"` | **failed** (SSL EOF to `pypi.org`) |
| pytest | **unavailable** |
| `scripts/phase11_static_review_checks.py` | **PASS** (0 failures) |
| `ast.parse` Python tree | **OK** |

No invented local pytest counts.

---

## 7. Dataset construction and held-out evaluation method

- Partitions: `datasets/development/`, `datasets/held_out/` (version `0.5.0`).
- Near-duplicate leakage controls; provenance metadata per §9.4.
- Phase 10 protocol: `veriforge-phase10-held-out-evaluation` v`1.0.0` (`experiments/protocols/phase10-held-out-protocol.md`).
- Seed: `20261009`. Held-out seed partition size: **n=8** (not a population estimate).
- Runner: `scripts/run_held_out_evaluation.py`.

---

## 8. Baselines and experimental configurations

| Baseline | Status |
| --- | --- |
| `baseline.original_no_optimization` | implemented; run on warm host |
| `baseline.rule_based_without_smt` | implemented (evaluation harness); run on warm host |
| `baseline.verification_enabled` | implemented; run on warm host |
| `baseline.testing_only_validation` | implemented (EVALUATION_ONLY); run on warm host |
| `baseline.external_tool` | **not_selected** |

Prior warm-host configuration fields: `solver_timeout_seconds=5.0`, `execution_iterations=50`, `trials_per_case=1`, fingerprint `1b5a4a762b6485eca8668cc6e7dba93cd829246479cbeee00caf977c8fea5464`.

---

## 9. Actual measured results (with sample sizes and uncertainty)

Source of record: `experiments/reports/phase10-held-out-evaluation.md` / `.json` (warm host; `dependency_available=true`).

High-level (do not over-generalize; n=8):

- Verification-enabled detection_rate overall: **1.0** (sample_count=8).
- Testing-only detection_rate overall: **0.375** (sample_count=8).
- Original / rule-based-without-SMT detection_rate overall: **0.333…** (sample_count=8) — driven by unsupported/malformed handling, not SMT counterexamples on incorrect rewrites.
- Incorrect held-out cases under SMT paths: **2 unique** NON_EQUIVALENT cases; **4/4** detections across verification-enabled + testing-only (see Phase 11 review S5).
- Solver median (verification-enabled): ~4.76e-05 s (n=7 solver samples on that baseline); testing-only solver median ~4.31e-05 s (n=7). Magnitudes are **host-specific**.
- Exact bit-for-bit timing reproduction is **not** guaranteed.

Phase 12 local re-run: **unavailable** — see `experiments/reports/phase12-release-attempt/`.

---

## 10. Performance and correctness trade-offs

On this sample, SMT verification paths detected the held-out incorrect rewrites that non-SMT baselines did not, at the cost of measurable solver time (H2 `supported_on_this_sample`). No claim that optimization improves expression execution speed (ledger P3 **NOT_SUPPORTED**). Solver latency and expression execution remain separately instrumented.

---

## 11. Failure cases and counterexamples

Held-out classes include `incorrect_rewrite` and `artificial_mutation` with counterexamples under SMT baselines (counts in the Phase 10 JSON). Counterexamples are validated against the reference evaluator where possible. Residual risk: correlated encoder/evaluator error can yield false `EQUIVALENT_WITHIN_MODEL` (ledger **R1**, UNRESOLVED).

---

## 12. Reproducibility instructions

```bash
# Clean install (requires PyPI egress)
python3 -m pip install -e ".[dev]"

# Full suite
python3 -m pytest

# Reproduce saved held-out experiment
python3 scripts/run_held_out_evaluation.py --seed 20261009 --timeout 5.0 \
  --execution-iterations 50 --trials 1
```

UI (optional): `python3 scripts/run_ui.py --port 8513`

If install fails, label measurements **unavailable**; do not fabricate. Pins: `requirements.lock` / `pyproject.toml`.

---

## 13. Literature review and novelty assessment

`docs/LITERATURE_REVIEW.md` (real sources; access date 2026-10-09). VERIFORGE assembles established translation-validation / equivalence-checking / rewriting / testing methods under an explicit dual semantic contract.

**Novelty:** **NOT_SUPPORTED** (ledger N1/N2). No confirmed novel formal method or novel empirical scientific finding is claimed.

---

## 14. Limitations and threats to validity

See `docs/LIMITATIONS.md` and Phase 11 `docs/INDEPENDENT_REVIEW.md`. Principal threats:

- Small held-out n=8; no population inference (R3 **NOT_SUPPORTED**).
- Timing nondeterminism.
- Single TCB encoding path (R1/R2 UNRESOLVED).
- Baseline 5 absent.
- Passing tests ≠ proof / novelty (R4 **NOT_SUPPORTED**).
- Some agent hosts cannot install dependencies (egress).

---

## 15. Remaining defects and future work

- Re-attest clean install after PyPI egress allowlist.
- Optional: second independently authored semantics implementation.
- Optional: larger held-out partition without near-duplicate leakage.
- Optional: select and integrate baseline 5 under equal semantics/workload.
- Optional: CI, Ruff, and typecheck gates (currently ungated).
- Do not promote H3 beyond inconclusive without more evidence.

---

## 16. Evidence ledger

Authoritative table: `docs/EVIDENCE_LEDGER.md`.

Summary statuses (unchanged by Phase 12 strengthening):

| Area | Status |
| --- | --- |
| Design D1–D5 | `INDEPENDENTLY_REVIEWED` |
| C2 / P1 | `EXPERIMENTALLY_SUPPORTED` (sample only) |
| H1 / H2 | `supported_on_this_sample` |
| H3 | `UNRESOLVED` |
| N1 / N2 | `NOT_SUPPORTED` |
| R1 / R2 | `UNRESOLVED` |
| R3 / R4 | `NOT_SUPPORTED` |

---

## 17. Release acceptance checklist

See `docs/RELEASE_CHECKLIST.md`.

**Verdict:** Definition of Done is **not fully met** (criterion 14 fails on this host). Release candidate version **`1.0.0rc1`**. Do **not** label the project fully complete or ship as `1.0.0` until clean-install attestation succeeds on a representative host and remaining disclosed gaps are accepted or closed.
