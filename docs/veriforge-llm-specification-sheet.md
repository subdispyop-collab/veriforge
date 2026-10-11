# VERIFORGE 1.0.0 — LLM Project Specification Sheet

**Version:** `1.0.0`  
**Release branch:** `cursor/phase-12-release-b430`  
**Date (UTC):** 2026-10-09  
**Audience:** Another LLM (ChatGPT / Gemini) that must understand the project without repository access  
**Honesty rule:** Never invent citations, measurements, users, or novelty. Prefer recorded evidence; label gaps **UNAVAILABLE**.

---

## 1. What VERIFORGE is (one paragraph)

VERIFORGE is a formal-verification-guided arithmetic expression optimization and research platform written in Python. It parses a restricted arithmetic expression safely (Python `ast`, never `eval`/`exec`), interprets it under an explicit semantic mode (Mode A: unbounded mathematical integers; Mode B: unsigned fixed-width bit-vectors), applies a small set of conservative identity-preserving rewrite rules, and accepts candidates only after Z3 SMT-based equivalence checking reports `EQUIVALENT_WITHIN_MODEL`. The project is a research prototype that experimentally evaluates correctness, error-detection effectiveness, verification overhead, and execution-performance trade-offs under that restricted model—not a claim of a new formal method or a universal correctness proof.

---

## 2. Research question and hypotheses

### Research question (§9.1)

> Does SMT-based equivalence checking improve the detection and rejection of incorrect arithmetic rewrites, and what computational overhead does it introduce under a defined, restricted arithmetic model?

This is a question to investigate, not a predetermined conclusion.

### Hypotheses (actual statuses from Phase 10 warm-host held-out report)

Source: `experiments/reports/phase10-held-out-evaluation.json` / `.md`  
Fingerprint: `1b5a4a762b6485eca8668cc6e7dba93cd829246479cbeee00caf977c8fea5464`  
Seed: `20261009` · Held-out n=8 · Phase 11/12 **did not upgrade** these statuses

| ID | Hypothesis | Status | Evidence note |
| --- | --- | --- | --- |
| **H1** | Verification identifies incorrect candidates within the supported model when encoding and solver are correct | `supported_on_this_sample` | 4/4 incorrect held-out case×baseline detections under verification-enabled **and** testing-only SMT paths (2 unique NON_EQUIVALENT cases × 2 baselines). **Not a general proof.** Ledger C2: `EXPERIMENTALLY_SUPPORTED` (sample only). |
| **H2** | Verification introduces measurable computational overhead | `supported_on_this_sample` | Positive `solver_seconds` observed (n=14 across verification-enabled + testing-only). Magnitude host-specific. Ledger P1: `EXPERIMENTALLY_SUPPORTED` (sample only). |
| **H3** | Overhead and success rates vary by expression complexity and transformation category | `inconclusive_on_this_sample` | Multiple categories present; sample sizes too small for a stable category-effect claim. Ledger: **UNRESOLVED**. |

**Novelty:** none (ledger N1/N2 `NOT_SUPPORTED`).

---

## 3. Full specification summary

### 3.1 Core design principles

| Principle | Meaning in VERIFORGE |
| --- | --- |
| Correctness over rewrite count | Prefer few validated rules over aggressive unvalidated ones |
| Fail closed | Unsupported syntax is rejected, never silently rewritten |
| Mode separation | Mathematical integers and fixed-width bit-vectors are never silently conflated |
| Solver honesty | UNKNOWN / TIMEOUT / errors are never labeled as equivalence |
| Counterexample validation | SAT models must be confirmed by a separate reference evaluator before “confirmed” |
| Auditable rules | Each rule has id, name, preconditions, modes, verification policy, tests, trace |
| No arbitrary code execution | Optimizer / parser never run user Python via `eval`/`exec` |
| Held-out hygiene | Benchmarks must not be tuned against the held-out set |
| Traceable numbers | Every reported numerical claim needs experimental evidence |
| Evidence before claims | Passing tests ≠ novelty; UNSAT ≠ application proof |

### 3.2 Semantic modes

| Mode | Domain | Z3 sort | Arithmetic | Notes |
| --- | --- | --- | --- | --- |
| **A** | Unbounded mathematical integers | `Int` | Mathematical `+`, `-`, `*` | No fixed-width overflow |
| **B** | Unsigned `[0, 2^w − 1]` | `BitVec(w)` | Modular wrap; default **w=32** | Literals outside range **rejected** (not reduced mod 2^w). Unsigned only; signed Mode B not in contract. Unary minus = bit-vector negation after conversion into width. |

Modes are explicitly selected. Results from one mode are not claims about the other. A rule validated in one mode is not thereby validated in the other.

### 3.3 Supported grammar (initial)

Accepted only:

- Integer literals (Python `ast` spellings: decimal / hex / binary / octal / underscores; **`True`/`False` rejected**)
- Named symbolic variables (no Python object lookup)
- Parentheses (grouping only; trailing-comma tuples rejected)
- Binary `+`, `-`, `*`
- Unary `+`, `-`

**Rejected (fail closed; not silently rewritten):** function calls, attributes, imports, comprehensions, assignments, statements, subscripts, comparisons, Booleans, division/remainder, bitwise ops, shifts, casts, exponentiation, floats/strings/`None`, and any unapproved AST node.

Precedence/associativity follow Python for these operators.

### 3.4 Parser safety

- Parse with Python’s `ast` module only; **never** `eval`/`exec` on user input.
- Allowlisted node types; names are symbolic variables.
- Resource limits (locked Phase 1 defaults; configurable):

| Limit | Default |
| --- | --- |
| Source length | 4096 characters |
| AST node count | 256 |
| Nesting depth | 32 |
| Mode A integer-literal bit length | 4096 |
| Solver timeout | 5 seconds |

### 3.5 Verifier result states

Encoded query: `exists x in Domain: [[E_o]](x) ≠ [[E_c]](x)` under the active mode.

| Solver / condition | Reported status | Claim allowed |
| --- | --- | --- |
| UNSAT | `EQUIVALENT_WITHIN_MODEL` | Equivalent **within the encoded model and assumptions** |
| SAT + reference evaluator confirms differing outputs | `COUNTEREXAMPLE_FOUND` | Counterexample within the encoded model |
| SAT but validation fails / impossible | `VERIFICATION_ERROR` | Not a confirmed counterexample |
| UNKNOWN (non-timeout) | `UNKNOWN` | Equivalence undetermined |
| Timeout / interruption | `TIMEOUT` | Verification incomplete |
| Unsupported expression | `UNSUPPORTED` | No verification claim |
| Bad input | `INVALID_INPUT` | No verification claim |
| Translation failure | `TRANSLATION_ERROR` | Verification not performed |
| Other engine failure | `VERIFICATION_ERROR` | No equivalence claim |

These states must **never** collapse to a Boolean success flag. UNSAT does **not** prove the parser/translator/optimizer/application correct.

### 3.6 Optimizer rules and policy

Production rules (each validated under Mode A and Mode B separately):

| Rule id | Rewrite |
| --- | --- |
| `identity.add_zero` | `x + 0 → x` |
| `identity.sub_zero` | `x - 0 → x` |
| `identity.mul_one` | `x * 1 → x` |
| `identity.mul_zero` | `x * 0 → 0` |

Pipeline: parse → IR → select applicable rules → generate candidate → record preconditions → verify vs **original** → accept/reject → full transformation trace.

| Policy | Behavior |
| --- | --- |
| `VERIFICATION_GUIDED` (default / production) | Accept only on `EQUIVALENT_WITHIN_MODEL` |
| `EVALUATION_ONLY` | Allowed in mutation harness; **rejected** by production `optimize()` |

Rejected statuses (`COUNTEREXAMPLE_FOUND`, `UNKNOWN`, `TIMEOUT`, errors) are recorded with reasons; never silently accepted.

### 3.7 Mutation isolation (§7.2)

- Module: `veriforge/fuzzer_suite.py` only.
- Artificial categories (examples): `mutation.literal_plus_one`, `mutation.add_to_sub`, `mutation.mul_to_add`, `mutation.swap_sub_operands`, `mutation.drop_right_of_add`, `mutation.zero_to_one`.
- Fixed seed (`DEFAULT_MUTATION_SEED`); each record has `mutation_id`, `generation_method`, `artificial=True`.
- Never mixed into production rules; never bypasses verification; `accepted_into_production` always False.
- Not estimates of real-world defect prevalence.

### 3.8 Testing strategy

Layered suites under `tests/`:

| Suite | Role |
| --- | --- |
| `unit/` | Parser, semantics, verifier, optimizer, fuzzer, datasets, experiments, benchmarks, audit, UI, security, evaluation |
| `properties/` | Hypothesis property tests + differential vs reference evaluator |
| `adversarial/` | Mutation isolation/detection; security resilience |
| `regression/` | Acceptance gate; mutation gate |

Also: boundary tests, metamorphic where applicable, resource-limit tests, end-to-end where present. Coverage is diagnostic, not a correctness proof. Passing randomized tests is not a mathematical proof of equivalence.

**Release suite evidence (warm host):** **359 passed, 0 failed, 0 skipped** (see §6).

### 3.9 Research / baselines / datasets

| Item | Status |
| --- | --- |
| Protocol freeze (Phase 5) | `docs/EXPERIMENT_PROTOCOL.md` v`0.5.0` |
| Held-out protocol (Phase 10) | `veriforge-phase10-held-out-evaluation` v`1.0.0` |
| Dataset version | `0.5.0`; seed `20261009` |
| Development partition | `datasets/development/` (12 seed cases) |
| Held-out partition | `datasets/held_out/` (**n=8**) |
| Near-duplicate leakage controls | Syntactic keys; not a semantic independence proof |
| Artificial 90/10 mix | Controlled configuration only — **not** real-world prevalence |

**Baselines (§9.3):**

| Baseline id | Status |
| --- | --- |
| `baseline.original_no_optimization` | Implemented; run on warm host |
| `baseline.rule_based_without_smt` | Implemented (evaluation harness); production `optimize()` stays verification-guided |
| `baseline.verification_enabled` | Implemented; run on warm host |
| `baseline.testing_only_validation` | Implemented (EVALUATION_ONLY); run on warm host |
| `baseline.external_tool` | **not_selected** |

### 3.10 Benchmarking metrics (§10)

Measured **separately** (never one merged duration):

- Parsing time, optimization time, candidate-generation time
- AST-to-Z3 translation time, solver time, end-to-end verification latency
- Original vs optimized expression execution time
- Timeout rate, UNKNOWN rate, verification completion rate, rejection / counterexample rates

Controls: fixed seeds, repeated trials, warmups, documented timeout policy, environment recording, raw storage, medians + variability. Timing nondeterminism disclosed. §10.2: never claim execution speedup from shorter expression / smaller AST / faster solver alone.

### 3.11 Architecture modules

| Module | Path | Role |
| --- | --- | --- |
| Parser | `veriforge/parser_engine.py` | Fail-closed `ast` parse + limits |
| Config / semantics | `veriforge/config.py`, `semantics.py` | Mode, width, limits |
| Reference evaluator | `veriforge/reference_evaluator.py` | Z3-independent evaluation under contract |
| Verifier | `veriforge/verifier_engine.py` | IR→Z3, classify, validate counterexamples |
| Optimizer | `veriforge/optimizer_engine.py` | Verification-guided conservative rules |
| Fuzzer / mutations | `veriforge/fuzzer_suite.py` | EVALUATION_ONLY artificial mutations |
| Datasets | `veriforge/dataset_engine.py` | Partitions, metadata, leakage checks |
| Experiments | `veriforge/experiment_engine.py` | Runs, fingerprints, baselines, metrics |
| Benchmarks | `veriforge/benchmark_engine.py` | Separated timings |
| Audit | `veriforge/audit_engine.py` | §13 records, export, replay, integrity |
| Evaluation | `veriforge/evaluation_engine.py` | Held-out baselines |
| Security | `veriforge/security.py` | Classified errors, redaction, path confinement |
| Storage | `veriforge/storage/` | SQLite + filesystem raw JSON |
| UI | `veriforge/app.py`, `veriforge/ui/` | Streamlit presentation only |
| Models / exceptions | `veriforge/models.py`, `exceptions.py` | Typed states |

### 3.12 Streamlit pages (§14)

Launch: `python3 scripts/run_ui.py --port 8513` (bind `127.0.0.1:8513`).

| # | Page | Honesty constraints |
| --- | --- | --- |
| 1 | Expression Workbench | Shows mode, width, assumptions, parse, candidate, trace, verification status |
| 2 | Verification Explorer | Counterexamples + validation; UNKNOWN/TIMEOUT never “equivalent” |
| 3 | Fuzzing and Mutation Lab | Synthetic mutations labeled artificial |
| 4 | Benchmark Lab | Charts from completed-run measurements only |
| 5 | Research Dashboard | No fabricated scientific charts; unavailable when no completed runs |
| 6 | Audit and Reproducibility | History, fingerprints, export, replay |

Logic lives in `ui/actions.py` / `presentation.py`; Streamlit is presentation only.

### 3.13 Security (§15)

- Untrusted: expression text, imported datasets/payloads.
- Controls: AST allowlist, resource limits, solver timeouts, no `eval`/`exec`, controlled exports under `experiments/exports/`, classified secret-safe errors, lockfile dependency awareness.
- **Does not claim resistance to every attack.** Local Streamlit is not a hardened multi-tenant service. Pattern-based secret redaction can miss novel formats.

### 3.14 Audit / reproducibility (§13)

Each optimization run preserves: original input, normalized representation, semantic configuration, applicable rules, accepted/rejected transforms, verification artifacts, solver status, counterexamples/validation, timings, errors, run id, software/configuration versions. Research runs also preserve dataset/protocol versions, seeds, baselines, raw observations, analysis config. Raw under `experiments/raw/`; derived under `experiments/reports/`. Exact bit-for-bit timing reproduction is **not** guaranteed.

### 3.15 Evidence ledger statuses (§17)

Statuses in use: `PROPOSED` · `IMPLEMENTED` · `TESTED` · `EXPERIMENTALLY_SUPPORTED` · `INDEPENDENTLY_REVIEWED` · `NOT_SUPPORTED` · `UNRESOLVED` · `UNAVAILABLE`.

Selected ledger snapshot (Phase 12 / `1.0.0`):

| ID | Claim (short) | Status |
| --- | --- | --- |
| D1–D5 | Design (modes, fail-closed, acceptance gate, partitions, protocol freeze) | `INDEPENDENTLY_REVIEWED` |
| C1 | Identity rules preserve semantics when verifier reports equivalent | `TESTED` |
| C2 / H1 | Verification detects incorrect candidates (sample) | `EXPERIMENTALLY_SUPPORTED` / `supported_on_this_sample` |
| C3 | Mutations isolated from production | `TESTED` |
| P1 / H2 | Measurable verification overhead (sample) | `EXPERIMENTALLY_SUPPORTED` / `supported_on_this_sample` |
| P2 | Solver vs execution reported separately | `INDEPENDENTLY_REVIEWED` |
| P3 | Optimization improves execution speed | `NOT_SUPPORTED` |
| U1–U2 | UI honesty / secret-safe errors | `TESTED` |
| N1–N2 | Novelty | `NOT_SUPPORTED` |
| H3 | Category/complexity variation | `UNRESOLVED` |
| R1–R2 | Correlated TCB / second semantics | `UNRESOLVED` |
| R3 | Population inference from n=8 | `NOT_SUPPORTED` |
| R4 | Pytest counts prove correctness or novelty | `NOT_SUPPORTED` |
| Rel1 | Warm-host suite 359/0/0 | `TESTED` |
| Rel2 | Clean install on Phase 12 authoring host | `UNAVAILABLE` / failed (egress); **met** on Phase 5 warm host |
| Rel3 | Held-out reproducible | `TESTED` (prior warm host) / `UNAVAILABLE` (authoring host without z3) |

---

## 4. Feature inventory

| Feature / module | Status | Result / evidence pointer |
| --- | --- | --- |
| Fail-closed AST parser + limits | **Implemented** | `parser_engine.py`; unit + adversarial tests; ledger D2 |
| Mode A / Mode B semantics + reference evaluator | **Implemented** | `semantics.py`, `reference_evaluator.py`; `docs/SEMANTICS.md`; Phase 1 decisions |
| Z3 equivalence verifier + counterexample validation | **Implemented** | `verifier_engine.py`; `docs/FORMAL_MODEL.md`; suite includes verifier tests |
| Verification-guided optimizer (4 identity rules) | **Implemented** | `optimizer_engine.py`; accept only `EQUIVALENT_WITHIN_MODEL` |
| EVALUATION_ONLY mutation harness | **Implemented** | `fuzzer_suite.py`; isolation tests |
| Hypothesis / differential / adversarial tests | **Implemented** | `tests/properties/`, `tests/adversarial/` |
| Dataset engine + seed partitions | **Implemented** | `dataset_engine.py`; n_dev=12, n_held_out=8, v`0.5.0` |
| Experiment engine + SQLite/raw storage | **Implemented** | `experiment_engine.py`, `storage/` |
| Benchmark engine (separated timings) | **Implemented** | `benchmark_engine.py`; §10.2 speedup-claim guard |
| Audit engine (export/replay/integrity) | **Implemented** | `audit_engine.py` |
| Streamlit 6-page UI | **Implemented** | `app.py`, `ui/`; honesty helpers tested |
| Security helpers + threat model doc | **Implemented** | `security.py`, `docs/SECURITY.md` |
| Held-out evaluation harness | **Implemented** | `evaluation_engine.py`, `scripts/run_held_out_evaluation.py` |
| Literature review | **Implemented** | `docs/LITERATURE_REVIEW.md`; no novelty claim |
| Evidence ledger | **Implemented** | `docs/EVIDENCE_LEDGER.md` |
| Independent review | **Implemented** | `docs/INDEPENDENT_REVIEW.md` |
| Release checklist + final research report | **Implemented** | `docs/RELEASE_CHECKLIST.md`, `docs/FINAL_RESEARCH_REPORT.md` |
| Baseline 5 (external tool) | **Not implemented** | `not_selected` |
| Second fully independent semantics impl (§6.2) | **Partial** | Reference evaluator is Z3-independent but shares contract/`semantics.py` (R2 UNRESOLVED) |
| Division / remainder / bitwise / shifts / casts | **Not implemented** | Rejected by grammar |
| Signed Mode B | **Not implemented** | Locked out of Phase 1 contract |
| Aggressive / non-identity rewrites | **Not implemented** | Intentionally absent |
| CI / Ruff / typecheck gates | **Not implemented** | Documented gap |
| Continuous multi-tenant hosting / auth | **Not implemented** | Out of scope |

---

## 5. Phase 0–12 table

| Phase | Objective | Delivered | Tests (known) | Branch |
| --- | --- | --- | --- | --- |
| **0** | Repo audit + plan | Empty-repo audit; `PROJECT_STATUS.md`, architecture/semantics/research/limitations stubs; no app code | No suite yet (UNAVAILABLE) | `cursor/phase-0-audit-5b37` |
| **1** | Semantic foundation | Grammar, safe parse, Mode A/B, reference evaluator, locked decisions | **84** passed / 0 / 0 | `cursor/phase-1-semantics-a215` |
| **2** | Formal verification | IR→Z3, classification, counterexample validation, TCB doc | **124** passed / 0 / 0 | `cursor/phase-2-verifier-183e` |
| **3** | Conservative optimizer | 4 identity rules, verification-guided gate, traces | **181** passed / 0 / 0 | `cursor/phase-3-optimizer-8adb` |
| **4** | Adversarial validation | Isolated mutations, Hypothesis, differential tests | **230** passed / 0 / 0 | `cursor/phase-4-adversarial-c33b` |
| **5** | Experimental framework | Protocol freeze, datasets, experiment engine, storage | **245** passed / 0 / 0 | `cursor/phase-5-experiments-0204` |
| **6** | Benchmark engine | Separated §10 timings, reproduction, §10.2 guard | Authoring host: UNAVAILABLE; warm host **256** passed / 0 / 0 | `cursor/phase-6-benchmarks-1735` |
| **7** | Audit and storage | §13 records, export/replay/integrity | Authoring: UNAVAILABLE; warm host **271** passed / 0 / 0 | `cursor/phase-7-audit-storage-67ba` |
| **8** | Streamlit UI | Six pages; honesty helpers | Authoring: UNAVAILABLE; warm host **305** passed / 0 / 0 | `cursor/phase-8-streamlit-ui-6fd4` |
| **9** | Security & resilience | `security.py`, threat model, path confinement | Authoring: UNAVAILABLE; warm host **350** passed / 0 / 0 | `cursor/phase-9-security-resilience-6104` |
| **10** | Research evaluation | Literature, ledger, held-out harness; warm-host held-out run | Authoring: UNAVAILABLE; warm host **359** passed / 0 / 0 + held-out `dependency_available=true` | `cursor/phase-10-research-evaluation-ab19` |
| **11** | Independent review | Adversarial review; TCB extension; claim audit (no claim upgrades) | Authoring: UNAVAILABLE; warm host **359** passed / 0 / 0 @ `6848fd4` | `cursor/phase-11-independent-review-0667` |
| **12** | Release | §20 checklist, §22 report, version `1.0.0` after warm-host clean-venv attestation | Clean venv + suite **359** / 0 / 0 on Phase 5 warm host; authoring-host clean install failed (egress) | `cursor/phase-12-release-b430` |

**Phase 13:** none (final phase complete).

---

## 6. Quantitative results (recorded only)

| Quantity | Value | Source |
| --- | --- | --- |
| Software version | `1.0.0` | `pyproject.toml` / release docs |
| Release branch | `cursor/phase-12-release-b430` | PROJECT_STATUS / RELEASE_CHECKLIST |
| Base tip for Phase 12 | `cursor/phase-11-independent-review-0667` @ `6848fd4` | PROJECT_STATUS |
| Warm-host / clean-venv pytest | **359 passed, 0 failed, 0 skipped** | Phase 10–12 warm host; Phase 12 clean venv attestation |
| Held-out n | **8** | `datasets/held_out/` v`0.5.0` |
| Held-out config fingerprint | `1b5a4a762b6485eca8668cc6e7dba93cd829246479cbeee00caf977c8fea5464` | Phase 10 report |
| Held-out seed | `20261009` | Protocol / report |
| Baselines completed (warm host) | **4** (`external_tool` not_selected) | Phase 10 report |
| H1 | `supported_on_this_sample` | Phase 10 report |
| H2 | `supported_on_this_sample` | Phase 10 report |
| H3 | `inconclusive_on_this_sample` → ledger **UNRESOLVED** | Phase 10 / ledger |
| Novelty | **none** | Literature + ledger N1/N2 |
| Detection_rate overall (verification-enabled) | **1.0** (sample_count=8) | Held-out MD |
| Detection_rate overall (testing-only) | **0.375** (n=8) | Held-out MD |
| Detection_rate overall (original / rule-based-without-SMT) | **≈0.333…** (n=8; driven by unsupported/malformed handling) | Held-out MD |
| Incorrect unique NON_EQUIVALENT held-out cases | **2**; SMT path detections **4/4** case×baseline | Final report / Phase 11 S5 |
| Solver median (verification-enabled) | ~4.76e-05 s (n=7); host-specific | Held-out MD |
| Solver median (testing-only) | ~4.31e-05 s (n=7); host-specific | Held-out MD |
| Clean install (Phase 5 warm host) | **SUCCEEDED** → DoD #14 met; version promoted to `1.0.0` | RELEASE_CHECKLIST / phase-12-end-report |
| Clean install (Phase 12 authoring host) | **FAILED** (SSL EOF to `pypi.org`) | RELEASE_CHECKLIST |
| Authoring-host pytest / held-out re-run | **UNAVAILABLE** (no z3/pytest without PyPI egress) | PROJECT_STATUS |
| Coverage % | **UNAVAILABLE** (not recorded as a release claim) | — |
| Users / deployments / production traffic | **UNAVAILABLE** (none claimed) | — |
| External-tool baseline numbers | **UNAVAILABLE** (`not_selected`) | RESEARCH_PLAN |
| Bit-identical timing reproduction | **Not guaranteed** (disclosed) | LIMITATIONS / held-out report |

---

## 7. What this project does NOT claim

1. **No novelty claim** — does not invent a new formal verification technique; assembles established translation-validation / equivalence-checking / rewriting / testing methods (ledger N1/N2 `NOT_SUPPORTED`).
2. **No universal correctness proof** — UNSAT is equivalence within the encoded model, not a proof that the application TCB is correct.
3. **No population inference from n=8** — held-out sample statuses are not population estimates (R3 `NOT_SUPPORTED`).
4. **H1/H2 are sample-limited** — `supported_on_this_sample` is not a general proof; Phase 11/12 did not upgrade them.
5. **H3 is unresolved** — category/complexity variation not established on this sample.
6. **No execution-speedup claim for optimization** — ledger P3 `NOT_SUPPORTED`; shorter AST / faster solver alone are insufficient (§10.2).
7. **No resistance to every attack** — research-prototype threat model with disclosed residual limits.
8. **No claim that pytest pass counts prove correctness or novelty** (R4 `NOT_SUPPORTED`).
9. **No signed Mode B; no division/bitwise/shifts/casts** until separately specified and implemented.
10. **No external-tool comparison** — baseline 5 not selected.
11. **Artificial mutations / 90/10 mixes are not real-world defect prevalence**.
12. **No fabricated users, citations, or unrun experiment results**.

---

## 8. How to run

### Requirements

- Python ≥ 3.11 (developed on 3.12)
- Runtime pins (see `pyproject.toml` / `requirements.lock`): `z3-solver==5.1.0.0`, `streamlit==1.41.1`, `plotly==5.24.1`, `pandas==2.2.3`
- Dev: `pytest`, `hypothesis` (locked)

### Clean install + tests

```bash
python3 -m venv /tmp/veriforge-rc
source /tmp/veriforge-rc/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
python -m pytest -v
```

Expected when successful (warm-host attestation): **359 passed, 0 failed, 0 skipped**.  
If PyPI egress fails, label measurements **UNAVAILABLE**; do not fabricate.

### Streamlit UI

```bash
python3 scripts/run_ui.py --port 8513
# equivalent:
# streamlit run veriforge/app.py --server.port 8513 --server.address 127.0.0.1
```

### Held-out evaluation (reproduce saved experiment)

```bash
python3 scripts/run_held_out_evaluation.py --seed 20261009 --timeout 5.0 \
  --execution-iterations 50 --trials 1
```

Prior successful warm-host fingerprint: `1b5a4a762b6485eca8668cc6e7dba93cd829246479cbeee00caf977c8fea5464`.

### Minimal API examples

```python
from veriforge import SemanticConfiguration, SemanticMode, optimize, verify_equivalence

cfg = SemanticConfiguration(mode=SemanticMode.MODE_A)
print(optimize("(x + 0) * 1", cfg).accepted.source)  # x
print(verify_equivalence("x + 1", "x + 2", cfg).status)  # COUNTEREXAMPLE_FOUND
```

---

## 9. Trusted computing base and key limitations

### In-TCB (for equivalence / accepted-rewrite claims)

1. CPython + Python `ast`
2. VERIFORGE fail-closed parser + resource limits
3. Mode A/B contract (`docs/SEMANTICS.md` + locked Phase 1 decisions)
4. Shared semantic helpers (`semantics.py`)
5. Z3 translation in `verifier_engine` matching that contract
6. Pinned `z3-solver==5.1.0.0`
7. Reference evaluator confirming SAT models
8. Configured limits including solver timeout (default 5s)
9. For accepted production rewrites: optimizer matching + verification-guided acceptance policy

### Out of TCB for equivalence claims

UI/Plotly/Pandas; dataset authorship quality; experiment/benchmark orchestration (except when calling the verifier); audit persistence; mutation harness; pytest/Hypothesis; OS scheduling / wall-clock timers.

### Residual risks (disclosed)

| Risk | Status |
| --- | --- |
| Correlated encoder/evaluator mis-encoding → false `EQUIVALENT_WITHIN_MODEL` | **UNRESOLVED** (R1) |
| No second separately authored semantics implementation | **UNRESOLVED** (R2) |
| Small held-out n=8 | Sample only; no population inference |
| Timing / Z3 nondeterminism | Bit-identical durations not guaranteed |
| Baseline 5 absent | Fair external comparison unavailable |
| Pattern-based secret redaction gaps | Documented |
| Some hosts cannot clean-install (PyPI egress) | Environment limit; warm-host attestation used for DoD #14 |
| No CI / Ruff / typecheck gates | Documented gap |

---

## 10. Suggested prompts for ChatGPT / Gemini

Paste this sheet first, then ask one of:

1. **Explain the acceptance gate:** “Using only this sheet, explain when VERIFORGE may accept an optimized expression, which verification statuses block acceptance, and why UNSAT is not an application correctness proof.”

2. **Compare Mode A vs Mode B:** “Contrast Mode A and Mode B for the expression `-1` and for a literal that equals `2^32`. What must the parser/evaluator do in each mode?”

3. **Audit the research claims:** “List H1–H3 with their exact statuses and sample sizes. Flag any statement that would overclaim beyond `supported_on_this_sample` or that would invent novelty.”

4. **Design a fair baseline extension:** “Propose how to add baseline 5 (external tool) under equal semantics/workload without breaking held-out hygiene or the Mode A/B contract. Do not invent that it is already implemented.”

5. **Reproduce locally:** “Give a step-by-step clean-venv install, pytest, Streamlit launch, and held-out reproduction command from this sheet, and state what to report if z3 cannot be installed.”

---

## Document provenance (for the human / coordinator)

This sheet was synthesized from:

- Controlling spec (unaltered): store `internal/veriforge-master-spec.md`
- Locked decisions: store `internal/phase-1-decisions.md`
- Checkout docs: `PROJECT_STATUS.md`, `README.md`, `CHANGELOG.md`, `docs/SEMANTICS.md`, `ARCHITECTURE.md`, `FORMAL_MODEL.md`, `RESEARCH_PLAN.md`, `EXPERIMENT_PROTOCOL.md`, `SECURITY.md`, `LIMITATIONS.md`, `LITERATURE_REVIEW.md`, `EVIDENCE_LEDGER.md`, `INDEPENDENT_REVIEW.md`, `RELEASE_CHECKLIST.md`, `FINAL_RESEARCH_REPORT.md`
- Phase end reports: store `internal/phase-*-end-report.md`
- Held-out report: checkout `experiments/reports/phase10-held-out-evaluation.md` / `.json`

No measurements or citations beyond those sources were invented.
