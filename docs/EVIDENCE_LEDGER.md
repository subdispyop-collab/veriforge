# Evidence ledger

Controlling specification §17. Every important claim maps to evidence with an explicit status. Do not promote a claim without supporting evidence.

Software version: Phase 10 measurement rows use `0.10.0`; Phase 11 review rows note `0.11.0` documentation; Phase 12 release candidate is `1.0.0rc1`.  
Dataset: `datasets/held_out/` version `0.5.0` unless noted.  
Held-out report fingerprint: `1b5a4a762b6485eca8668cc6e7dba93cd829246479cbeee00caf977c8fea5464`.  
Statuses used: `PROPOSED` · `IMPLEMENTED` · `TESTED` · `EXPERIMENTALLY_SUPPORTED` · `INDEPENDENTLY_REVIEWED` · `NOT_SUPPORTED` · `UNRESOLVED` · `UNAVAILABLE`

Phase 11/12 rule: **do not strengthen C2/P1/H1–H3/N\* beyond the warm-host Phase 10 ledger**. Design rows may become `INDEPENDENTLY_REVIEWED` after adversarial review. Phase 12 does not invent measurements. See `docs/INDEPENDENT_REVIEW.md`, `docs/RELEASE_CHECKLIST.md`, `docs/FINAL_RESEARCH_REPORT.md`.

---

## Design claims

| ID | Claim | Type | Supporting evidence | Artifact | Version | Dataset / config | Status | Limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D1 | Mode A uses unbounded mathematical integers; Mode B uses unsigned modular bit-vectors | design | `docs/SEMANTICS.md`; Phase 1 decisions; Phase 11 review | `docs/SEMANTICS.md`, `veriforge/semantics.py` | ≥0.1.0 / review 0.11.0 | n/a | INDEPENDENTLY_REVIEWED | Signed Mode B not in contract |
| D2 | Unsupported syntax fails closed; no `eval`/`exec` on user input | design / correctness | parser + security tests; warm-host suite; Phase 11 static review | `veriforge/parser_engine.py`, `tests/unit/test_no_eval_exec.py` | ≥0.9.0 | n/a | INDEPENDENTLY_REVIEWED | Authoring hosts may lack pytest egress |
| D3 | Production optimizer accepts only `EQUIVALENT_WITHIN_MODEL` | design / correctness | optimizer + verifier; Phase 11 review | `veriforge/optimizer_engine.py` | ≥0.3.0 | n/a | INDEPENDENTLY_REVIEWED | Encoding correctness is TCB-dependent |
| D4 | Development and held-out partitions are separated with near-duplicate leakage checks | design | dataset engine; Phase 11 review | `datasets/`, `veriforge/dataset_engine.py` | 0.5.0 datasets | seed `20261009` | INDEPENDENTLY_REVIEWED | Keys are syntactic, not semantic independence proofs |
| D5 | Phase 10 evaluation protocol is frozen before scoring held-out | design | protocol docs + config fingerprint; Phase 11 review | `docs/EXPERIMENT_PROTOCOL.md`, `experiments/protocols/phase10-held-out-protocol.md` | eval protocol 1.0.0 | held_out | INDEPENDENTLY_REVIEWED | Small seed partition |

## Correctness claims

| ID | Claim | Type | Supporting evidence | Artifact | Version | Dataset / config | Status | Limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | Identity rules preserve Mode A/B semantics when verifier returns equivalent | correctness | unit/property tests; verifier; Phase 11 reviewed (not upgraded) | `tests/unit/test_optimizer.py`, `tests/unit/test_verifier.py` | prior phases | development / fixtures | TESTED | Not a proof of encoder correctness |
| C2 | H1: Verification identifies incorrect candidates within the supported model when encoding/solver are correct | correctness | held-out SMT baselines (warm host, 2026-10-09): report `supported_on_this_sample` — 4/4 NON_EQUIVALENT case×baseline detections under verification-enabled **and** testing-only SMT paths (2 unique held-out non-equivalent cases × 2 baselines) | `experiments/reports/phase10-held-out-evaluation.json` fingerprint `1b5a4a76…` | 0.10.0 | held_out n=8 / seed `20261009` | EXPERIMENTALLY_SUPPORTED | **Sample only** — not a general proof; Phase 11 reviewed and **did not upgrade**; see review S5 |
| C3 | Artificial mutations are isolated from production rules | correctness | fuzzer isolation tests; Phase 11 reviewed (not upgraded) | `veriforge/fuzzer_suite.py` | ≥0.4.0 | n/a | TESTED | Mutations ≠ real defect prevalence |

## Performance claims

| ID | Claim | Type | Supporting evidence | Artifact | Version | Dataset / config | Status | Limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | H2: Verification introduces measurable computational overhead | performance | held-out SMT baselines: positive `solver_seconds` observed (n=14 solver samples across verification-enabled + testing-only) | `experiments/reports/phase10-held-out-evaluation.json` | 0.10.0 | held_out | EXPERIMENTALLY_SUPPORTED | Report status `supported_on_this_sample`; magnitude is host-specific; not bit-reproducible; Phase 11 reviewed and **did not upgrade** |
| P2 | Solver latency and expression execution are reported separately | performance / design | evaluation + benchmark engines; Phase 11 review | `veriforge/evaluation_engine.py`, `veriforge/benchmark_engine.py` | ≥0.6.0 / 0.10.0 | held_out / development | INDEPENDENTLY_REVIEWED | Separation is instrumentation, not a speedup claim |
| P3 | Optimization improves execution speed | performance | — | — | — | — | NOT_SUPPORTED | Forbidden without direct execution measurements showing improvement; shorter AST/solver time insufficient (§10.2) |

## Usability claims

| ID | Claim | Type | Supporting evidence | Artifact | Version | Dataset / config | Status | Limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| U1 | UI never fabricates research results; UNKNOWN/timeout not labeled equivalent | usability / correctness | UI presentation tests; Phase 11 reviewed (not upgraded) | `veriforge/ui/presentation.py`, `tests/unit/test_ui_presentation.py` | ≥0.8.0 | n/a | TESTED | Authoring hosts may lack pytest |
| U2 | User-facing errors are classified and secret-safe | usability / security | security module tests; Phase 11 reviewed (not upgraded) | `veriforge/security.py` | ≥0.9.0 | n/a | TESTED | Pattern redaction can miss novel secrets |

## Novelty claims

| ID | Claim | Type | Supporting evidence | Artifact | Version | Dataset / config | Status | Limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N1 | VERIFORGE invents a new formal verification technique | novelty | literature review; Phase 11 review | `docs/LITERATURE_REVIEW.md` | 0.10.0 | n/a | NOT_SUPPORTED | Assembles established methods; no novelty claim |
| N2 | Confirmed novel empirical scientific finding from held-out evaluation | novelty | held-out report + literature review; Phase 11 review | `experiments/reports/phase10-held-out-evaluation.json`, `docs/LITERATURE_REVIEW.md` | 0.10.0 | held_out | NOT_SUPPORTED | Report novelty claim: none; small n; situates among established methods |

## Hypothesis rows (preregistered; not findings)

| ID | Hypothesis | Evidence pointer | Status |
| --- | --- | --- | --- |
| H1 | Verification identifies incorrect candidates within the supported model when encoding and solver are correct | Phase 10 report `hypothesis_status.H1_*` | `supported_on_this_sample` (4/4 case×baseline detections; 2 unique non-equivalent cases; n small; not a general proof) — Phase 11 **not upgraded** |
| H2 | Verification introduces measurable computational overhead | Phase 10 report `hypothesis_status.H2_*` | `supported_on_this_sample` (positive solver_seconds, n=14; host-specific) — Phase 11 **not upgraded** |
| H3 | Overhead and success rates vary by expression complexity and transformation category | Phase 10 report `hypothesis_status.H3_*` | `inconclusive_on_this_sample` → ledger **UNRESOLVED** — Phase 11 **not upgraded** |

## Phase 11 review findings

| ID | Finding | Type | Supporting evidence | Status | Limitations |
| --- | --- | --- | --- | --- | --- |
| R1 | Correlated encoder/evaluator residual risk can yield false EQUIVALENT_WITHIN_MODEL | correctness / TCB | `docs/FORMAL_MODEL.md`, `docs/INDEPENDENT_REVIEW.md` | UNRESOLVED | Inherent to single-encoding + SAT-only validation architecture |
| R2 | Second fully independent semantics implementation (§6.2) is not present | design | reference evaluator shares contract/`semantics.py` | UNRESOLVED | Z3-independence ≠ separately authored semantics |
| R3 | Held-out n=8 supports population-level inference | performance / correctness | held-out metadata + report limitations | NOT_SUPPORTED | Seed partition only |
| R4 | Warm-host pytest pass counts prove implementation correctness or novelty | correctness / novelty | Phase 10 warm-host 359 passed | NOT_SUPPORTED | Suite evidence ≠ proof / novelty |

## Phase 12 release attestation

| ID | Claim | Type | Supporting evidence | Status | Limitations |
| --- | --- | --- | --- | --- | --- |
| Rel1 | Required unit/property/regression suite passes on warm host @ `6848fd4` | correctness / release | Warm-host pytest **359 passed / 0 failed / 0 skipped** | TESTED | Authoring-host pytest unavailable without PyPI egress |
| Rel2 | Clean installation works on Phase 12 authoring host | release | `pip install -e ".[dev]"` SSL EOF to pypi.org | UNAVAILABLE / failed | Egress allowlist required; do not claim `1.0.0` DoD complete |
| Rel3 | Held-out evaluation reproducible via documented command | release | Command in README / RELEASE_CHECKLIST; prior warm-host run; Phase 12 local attempt unavailable | TESTED (prior) / UNAVAILABLE (this host) | Fresh SMT re-run needs Z3 |

## How to update

1. Run `python3 scripts/run_held_out_evaluation.py` on a host with `z3-solver` installed.  
2. Commit/update `experiments/reports/phase10-held-out-evaluation.json` and `.md`.  
3. Promote C2/P1/H1–H3 only to match the report’s actual wording; never invent counts.  
4. Phase 11 review (`docs/INDEPENDENT_REVIEW.md`) records adversarial findings; do not use review to invent stronger experimental claims than the report supports.
5. Phase 12 release docs must keep §20 criterion 14 honest until clean install is re-attested.
