# Independent review (Phase 11)

Adversarial technical review of VERIFORGE against controlling specification Phase 11 objectives and claim discipline (§17, §20 items 16–18).

- **Reviewer role:** independent technical reviewer (find weaknesses; do not approve prematurely).
- **Base evidence tip:** `cursor/phase-10-research-evaluation-ab19` @ `bdfb533` (warm-host held-out + ledger).
- **Software under review:** package version `0.11.0` (Phase 11 docs/review on top of Phase 10 `0.10.0` engines).
- **Review date (UTC):** 2026-10-09.
- **Held-out numerical results:** **available** in-tree (`dependency_available=true`; fingerprint `1b5a4a762b6485eca8668cc6e7dba93cd829246479cbeee00caf977c8fea5464`).
- **Warm-host pytest (Phase 10 tip):** **359 passed, 0 failed, 0 skipped** (historical attestation on that tip; not re-run on this Phase 11 authoring host).
- **Novelty:** **no novelty claim** (report + literature + ledger N1/N2).

This document does **not** certify release readiness. Phase 12 is not started. **Statuses are not strengthened beyond the Phase 10 ledger** for experimental claims.

---

## 1. Objectives and method

| Objective | Method |
| --- | --- |
| Challenge semantic assumptions | Re-read contract + code; Mode A/B spot checks |
| Inspect trusted computing base | Enumerate residual risks; extend `docs/FORMAL_MODEL.md` / `docs/SECURITY.md` |
| Recheck counterexamples | Reference-evaluator rechecks; design review of SAT validation path; live Z3 blocked on this host |
| Review experimental design | Protocol, partitions, n=8, baselines, H1–H3 wording vs artifacts |
| Audit every major research claim | Walk `docs/EVIDENCE_LEDGER.md` against report JSON/MD |

---

## 2. Semantic assumptions challenged

### 2.1 Documented and consistent

| Assumption | Finding |
| --- | --- |
| Mode A unbounded ℤ vs Mode B unsigned wrap | Explicit; modes not inferred from text |
| Mode B out-of-range literals fail closed | Parser rejects; matches locked decisions |
| Mode B unary minus = modular/BV negation | Matches `(2^w - x) mod 2^w` |
| Precedence = Python `ast` | Documented CPython grammar dependency |
| Production accept only `EQUIVALENT_WITHIN_MODEL` | Fail-closed for UNKNOWN/TIMEOUT/errors/CEX |
| Identity rules are right-literal forms only | Conservative incompleteness, not silent wrongness |

### 2.2 Residual risks (not eliminated by Phase 10 numbers)

| ID | Risk | Status |
| --- | --- | --- |
| S1 | Correlated encoder/evaluator bug can yield false `EQUIVALENT_WITHIN_MODEL` (UNSAT). SAT validation does not catch this. | **UNRESOLVED** residual TCB |
| S2 | Reference evaluator shares `semantics.py` / written contract; not a second separately authored semantics impl (§6.2 partial). | **UNRESOLVED** |
| S3 | Near-duplicate keys are syntactic, not semantic independence proofs. | Documented limitation |
| S4 | Held-out `n=8` cannot support population inference or stable category effects (aligns with H3 inconclusive). | **NOT_SUPPORTED** for population claims |
| S5 | H1 “4/4” counts NON_EQUIVALENT cases under **both** SMT baselines (`verification_enabled` + `testing_only_validation`) → 2 unique held-out non-equivalent cases × 2 baselines. Ledger sample-only wording remains correct; “verification-enabled path” alone would be **2/2**. | Clarification; **not** a status upgrade |
| S6 | Warm-host 359 pytest passes certify that tip, not a mathematical proof of the encoder. | Do not upgrade C1 beyond TESTED |

### 2.3 Reference-level spot checks (this host, no Z3)

`scripts/phase11_static_review_checks.py`: Mode A/B non-conflation, identity samples, wrap boundaries, held-out seed eq/neq expectations, fail-closed literal/`import` — **PASS**. These do not re-prove Z3 translation on this host.

---

## 3. Trusted computing base

Written TCB (extended in Phase 11): `docs/FORMAL_MODEL.md` and `docs/SECURITY.md`.

**In-TCB for equivalence:** CPython + `ast`; fail-closed parser; Mode A/B contract; Z3 translator; pinned `z3-solver`; reference evaluator for SAT confirmation; resource limits; plus optimizer matching/policy for accepted rewrites.

**Out of TCB:** UI/charts; dataset authorship quality; experiment orchestration (except verifier calls); audit persistence; pytest/Hypothesis as oracles; wall-clock nondeterminism.

**Verdict:** TCB is written down. Solver UNSAT remains **not** a proof of the implementation (S1).

---

## 4. Counterexample recheck

### 4.1 Design

`verifier_engine._validate_counterexample` confirms only when reference outputs differ; UNVALIDATABLE/DISCREPANCY → `VERIFICATION_ERROR`. Matches §6.1.

### 4.2 Artifact cross-check (warm-host held-out)

Under `baseline.verification_enabled` (n=8):

- `incorrect_rewrite`: counterexample_count=1, detected=1
- `artificial_mutation`: counterexample_count=1, detected=1
- `identity_preserving` / `boundary_value` / `nested_expression`: equivalent as expected
- `unsupported_or_malformed`: detected without counterexample (reject path)
- timeout_count=0, unknown_count=0 on this run

Live end-to-end Z3 re-execution was **not** possible on this Phase 11 authoring host (PyPI egress). Warm-host report is the measurement source of record.

---

## 5. Experimental design review

| Element | Assessment |
| --- | --- |
| Protocol freeze | Met (`1.0.0`; config fingerprint recorded) |
| Partition separation | Met; syntactic near-duplicate keys (S3) |
| Baselines 1–4 | Completed on warm host |
| Baseline 5 | **not_selected** |
| Latency separation | Present in report (`latency_separation`) |
| Sample size | n=8 — inadequate for population / H3 category effects |
| H1/H2/H3 labels | Match report: `supported_on_this_sample` / `supported_on_this_sample` / `inconclusive_on_this_sample` |
| Novelty | Explicitly none |
| Post-hoc tuning vs held-out | No evidence of rule retuning against held-out in reviewed tip |

---

## 6. Claim-by-claim audit

**Rule for Phase 11:** do **not** strengthen experimental statuses beyond the Phase 10 ledger at `bdfb533`. Independent review may promote **design** rows to `INDEPENDENTLY_REVIEWED` where code/docs review supports that, and may add residual-risk rows as `UNRESOLVED` / `NOT_SUPPORTED`.

| ID | Ledger status (Phase 10 tip) | Phase 11 disposition |
| --- | --- | --- |
| D1 | IMPLEMENTED | **INDEPENDENTLY_REVIEWED** |
| D2 | TESTED | **INDEPENDENTLY_REVIEWED** (warm-host suite + static; authoring host no pytest) |
| D3 | IMPLEMENTED | **INDEPENDENTLY_REVIEWED** |
| D4 | IMPLEMENTED | **INDEPENDENTLY_REVIEWED** (syntactic-key limit retained) |
| D5 | IMPLEMENTED | **INDEPENDENTLY_REVIEWED** |
| C1 | TESTED | **TESTED** — reviewed; **not upgraded** (not encoder proof) |
| C2 | EXPERIMENTALLY_SUPPORTED (`supported_on_this_sample`) | **EXPERIMENTALLY_SUPPORTED** — reviewed; **not upgraded**; see S5 clarification |
| C3 | TESTED | **TESTED** — reviewed; not upgraded |
| P1 | EXPERIMENTALLY_SUPPORTED (`supported_on_this_sample`) | **EXPERIMENTALLY_SUPPORTED** — reviewed; **not upgraded** |
| P2 | IMPLEMENTED | **INDEPENDENTLY_REVIEWED** |
| P3 | NOT_SUPPORTED | **NOT_SUPPORTED** |
| U1 | TESTED | **TESTED** — reviewed; not upgraded |
| U2 | TESTED | **TESTED** — reviewed; not upgraded |
| N1 | NOT_SUPPORTED | **NOT_SUPPORTED** |
| N2 | NOT_SUPPORTED | **NOT_SUPPORTED** |
| H1 | `supported_on_this_sample` | unchanged |
| H2 | `supported_on_this_sample` | unchanged |
| H3 | `inconclusive_on_this_sample` → ledger **UNRESOLVED** | **UNRESOLVED** — not upgraded |

### Review-only finding rows

| ID | Finding | Status |
| --- | --- | --- |
| R1 | Correlated encoder/evaluator residual risk (S1) | **UNRESOLVED** |
| R2 | No second fully independent semantics implementation (S2) | **UNRESOLVED** |
| R3 | Held-out n=8 supports population-level inference | **NOT_SUPPORTED** |
| R4 | Warm-host pytest passes prove implementation correctness / novelty | **NOT_SUPPORTED** |

---

## 7. Tests and checks actually run

### 7.1 This Phase 11 authoring host

| Check | Result |
| --- | --- |
| `pip install -e ".[dev]"` | **Failed** — SSL EOF to `pypi.org` |
| `pytest` | **unavailable** (deps missing) |
| Live held-out re-run | **not executed** here (Z3 missing); warm-host artifacts used |
| `scripts/phase11_static_review_checks.py` | **PASS** |
| `ast.parse` over Python tree | **OK** |

No invented local pytest counts.

### 7.2 Incorporated warm-host evidence (tip `bdfb533`)

| Check | Result |
| --- | --- |
| `python3 -m pytest -v` | **359 passed, 0 failed, 0 skipped** |
| `run_held_out_evaluation.py --seed 20261009` | `dependency_available=true`; four baselines completed |

---

## 8. Strengths

- Explicit Mode A/B separation and fail-closed parsing.
- Counterexample confirmation path matches §6.1.
- Verification-guided production acceptance.
- Literature + ledger refuse novelty; H3 stays inconclusive/UNRESOLVED.
- Phase 10 report separates solver vs execution latency.
- Sample-limited wording on H1/H2 is appropriate.

## 9. Weaknesses / gaps

1. Residual TCB correlation risk S1 remains.
2. §6.2 second independent semantics implementation incomplete.
3. Held-out seed too small for H3 / population claims.
4. Baseline 5 absent.
5. H1 “4/4” is baseline-duplicated case counts (S5) — easy to overread as four distinct bugs.
6. No CI; Ruff/typecheck ungated.
7. Package `__init__` imports Z3-dependent modules (egress-blocked friction).
8. Definition of Done §20 met at `1.0.0` after warm-host clean-venv attestation; residual research disclosures remain (small n, TCB, baseline 5, H3).

---

## 10. Phase 11 acceptance

| Criterion | Status |
| --- | --- |
| Challenge semantic assumptions | **met** |
| TCB written down | **met** |
| Counterexamples rechecked where possible | **met** (reference + artifact review; live Z3 blocked here) |
| Experimental design reviewed | **met** |
| Claims audited; status ≤ evidence; no strengthening beyond ledger for C2/P1/H*/N* | **met** |
| NOT_SUPPORTED / UNRESOLVED recorded | **met** |
| `docs/INDEPENDENT_REVIEW.md` produced | **met** |
| Prior phases preserved | **met** |
| Phase 12 not started | **met** |

Overall: Phase 11 review deliverables **met**. Project is **not** release-complete.

## 11. Next phase

Phase 12 — Release (coordinator-gated). Do not start from this review alone.
