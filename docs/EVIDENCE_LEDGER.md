# Evidence ledger

Controlling specification §17. Every important claim maps to evidence with an explicit status. Do not promote a claim without supporting evidence.

Software version for Phase 10 rows: see each row (target `0.10.0`).  
Dataset: `datasets/held_out/` version `0.5.0` unless noted.  
Statuses used: `PROPOSED` · `IMPLEMENTED` · `TESTED` · `EXPERIMENTALLY_SUPPORTED` · `INDEPENDENTLY_REVIEWED` · `NOT_SUPPORTED` · `UNRESOLVED` · `UNAVAILABLE`

---

## Design claims

| ID | Claim | Type | Supporting evidence | Artifact | Version | Dataset / config | Status | Limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D1 | Mode A uses unbounded mathematical integers; Mode B uses unsigned modular bit-vectors | design | `docs/SEMANTICS.md`; Phase 1 decisions | `docs/SEMANTICS.md`, `veriforge/semantics.py` | ≥0.1.0 | n/a | IMPLEMENTED | Signed Mode B not in contract |
| D2 | Unsupported syntax fails closed; no `eval`/`exec` on user input | design / correctness | parser + security tests | `veriforge/parser_engine.py`, `tests/unit/test_no_eval_exec.py` | ≥0.9.0 | n/a | TESTED | Full suite may be unavailable on egress-blocked hosts |
| D3 | Production optimizer accepts only `EQUIVALENT_WITHIN_MODEL` | design / correctness | optimizer + verifier | `veriforge/optimizer_engine.py` | ≥0.3.0 | n/a | IMPLEMENTED | Encoding correctness is TCB-dependent |
| D4 | Development and held-out partitions are separated with near-duplicate leakage checks | design | dataset engine | `datasets/`, `veriforge/dataset_engine.py` | 0.5.0 datasets | seed `20261009` | IMPLEMENTED | Keys are syntactic, not semantic independence proofs |
| D5 | Phase 10 evaluation protocol is frozen before scoring held-out | design | protocol docs + config fingerprint | `docs/EXPERIMENT_PROTOCOL.md`, `experiments/protocols/phase10-held-out-protocol.md` | eval protocol 1.0.0 | held_out | IMPLEMENTED | Small seed partition |

## Correctness claims

| ID | Claim | Type | Supporting evidence | Artifact | Version | Dataset / config | Status | Limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | Identity rules preserve Mode A/B semantics when verifier returns equivalent | correctness | unit/property tests; verifier | `tests/unit/test_optimizer.py`, `tests/unit/test_verifier.py` | prior phases | development / fixtures | TESTED | Not a proof of encoder correctness |
| C2 | H1: Verification identifies incorrect candidates within the supported model when encoding/solver are correct | correctness | held-out SMT baselines (Phase 5 warm host, 2026-10-09): 4/4 incorrect held-out cases detected under verification-enabled path | `experiments/reports/phase10-held-out-evaluation.json` fingerprint `1b5a4a76…` | 0.10.0 | held_out n=8 / seed `20261009` | EXPERIMENTALLY_SUPPORTED | **Sample only** — report status `supported_on_this_sample`; not a general proof; seed partition is small |
| C3 | Artificial mutations are isolated from production rules | correctness | fuzzer isolation tests | `veriforge/fuzzer_suite.py` | ≥0.4.0 | n/a | TESTED | Mutations ≠ real defect prevalence |

## Performance claims

| ID | Claim | Type | Supporting evidence | Artifact | Version | Dataset / config | Status | Limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | H2: Verification introduces measurable computational overhead | performance | held-out SMT baselines: positive `solver_seconds` observed (n=14 solver samples across verification-enabled + testing-only) | `experiments/reports/phase10-held-out-evaluation.json` | 0.10.0 | held_out | EXPERIMENTALLY_SUPPORTED | Report status `supported_on_this_sample`; magnitude is host-specific; not bit-reproducible |
| P2 | Solver latency and expression execution are reported separately | performance / design | evaluation + benchmark engines | `veriforge/evaluation_engine.py`, `veriforge/benchmark_engine.py` | ≥0.6.0 / 0.10.0 | held_out / development | IMPLEMENTED | Separation is instrumentation, not a speedup claim |
| P3 | Optimization improves execution speed | performance | — | — | — | — | NOT_SUPPORTED | Forbidden without direct execution measurements showing improvement; shorter AST/solver time insufficient (§10.2) |

## Usability claims

| ID | Claim | Type | Supporting evidence | Artifact | Version | Dataset / config | Status | Limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| U1 | UI never fabricates research results; UNKNOWN/timeout not labeled equivalent | usability / correctness | UI presentation tests | `veriforge/ui/presentation.py`, `tests/unit/test_ui_presentation.py` | ≥0.8.0 | n/a | TESTED | Pytest may be unavailable on egress-blocked hosts |
| U2 | User-facing errors are classified and secret-safe | usability / security | security module tests | `veriforge/security.py` | ≥0.9.0 | n/a | TESTED | Pattern redaction can miss novel secrets |

## Novelty claims

| ID | Claim | Type | Supporting evidence | Artifact | Version | Dataset / config | Status | Limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N1 | VERIFORGE invents a new formal verification technique | novelty | literature review | `docs/LITERATURE_REVIEW.md` | 0.10.0 | n/a | NOT_SUPPORTED | Assembles established methods; no novelty claim |
| N2 | Confirmed novel empirical scientific finding from held-out evaluation | novelty | held-out report + literature review | `experiments/reports/phase10-held-out-evaluation.json`, `docs/LITERATURE_REVIEW.md` | 0.10.0 | held_out | NOT_SUPPORTED | Report novelty claim: none; small n; situates among established methods |

## Hypothesis rows (preregistered; not findings)

| ID | Hypothesis | Evidence pointer | Status |
| --- | --- | --- | --- |
| H1 | Verification identifies incorrect candidates within the supported model when encoding and solver are correct | Phase 10 report `hypothesis_status.H1_*` | `supported_on_this_sample` (4/4 incorrect cases; n small; not a general proof) |
| H2 | Verification introduces measurable computational overhead | Phase 10 report `hypothesis_status.H2_*` | `supported_on_this_sample` (positive solver_seconds, n=14; host-specific) |
| H3 | Overhead and success rates vary by expression complexity and transformation category | Phase 10 report `hypothesis_status.H3_*` | `inconclusive_on_this_sample` (categories present; n too small) → ledger status UNRESOLVED |

## How to update

1. Run `python3 scripts/run_held_out_evaluation.py` on a host with `z3-solver` installed.  
2. Commit/update `experiments/reports/phase10-held-out-evaluation.json` and `.md`.  
3. Promote C2/P1/H1–H3 only to match the report’s actual wording; never invent counts.  
4. Independent review (Phase 11) is required before `INDEPENDENTLY_REVIEWED`.
