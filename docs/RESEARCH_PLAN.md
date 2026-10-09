# Research plan

This file pre-registers the research design from the controlling specification. Every hypothesis below is a hypothesis to investigate. None is a finding until held-out evidence supports it.

Literature review: see `docs/LITERATURE_REVIEW.md` (real sources only; access date 2026-10-09). **No novelty claim.**

Protocol freeze: Phase 5 details remain in `docs/EXPERIMENT_PROTOCOL.md` (protocol version `0.5.0`). Phase 10 held-out execution uses protocol id `veriforge-phase10-held-out-evaluation` version `1.0.0` (`experiments/protocols/phase10-held-out-protocol.md`).

## Research question

Specified question, section 9.1:

> Does SMT-based equivalence checking improve the detection and rejection of incorrect arithmetic rewrites, and what computational overhead does it introduce under a defined, restricted arithmetic model?

The question is not a conclusion. Experiments may show benefits, limitations, or mixed results.

## Hypotheses

Specified in section 9.2. Status is recorded after held-out runs in `experiments/reports/phase10-held-out-evaluation.json` and `docs/EVIDENCE_LEDGER.md`. Until those runs succeed on a host with Z3, status remains **unavailable** (not “confirmed”).

1. Verification identifies incorrect candidates within the supported model when the encoding and solver are correct.
2. Verification introduces measurable computational overhead.
3. The overhead and success rates vary by expression complexity and transformation category.

These sentences are not advance reports of what VERIFORGE will find.

## Baselines

Specified in section 9.3. Defined in code by `veriforge.experiment_engine.baseline_catalog()`. Phase 10 harness: `veriforge.evaluation_engine`.

1. Original expression without optimization (`baseline.original_no_optimization`).
2. Rule-based optimizer without SMT verification (`baseline.rule_based_without_smt`) — evaluation harness only; production `optimize()` stays verification-guided.
3. Verification-enabled optimizer (`baseline.verification_enabled`).
4. Testing-only candidate validation (`baseline.testing_only_validation`) — EVALUATION_ONLY / SMT check of candidates; never production acceptance.
5. An existing relevant tool or method (`baseline.external_tool`) — **not selected** (Alive/Alive2/CompCert not integrated under equal workload/semantics).

## Specified outcomes

- Detection and rejection of incorrect arithmetic rewrites (error-detection effectiveness), under the defined restricted model.
- Computational overhead of SMT-based equivalence checking.
- Correctness of accepted rewrites under that model.
- Execution-performance trade-offs of the conservative optimizer, measured separately from verification overhead.

Report by class/category with sample sizes. Separate solver latency from expression execution. Do not claim execution speedup from shorter expressions or faster solver returns alone (§10.2).

## Method constraints

- Freeze the question, hypotheses, methods, and outcomes before held-out scoring (this file + protocol docs).
- Keep development cases separate from held-out cases.
- Prevent near-duplicate leakage across partitions.
- Record dataset provenance fields required by §9.4.
- Artificial 90/10 mix is a controlled configuration only — not real-world prevalence.
- Fixed recorded seeds, raw measurement storage, configuration fingerprints.
- The benchmark/evaluation must not be tuned against the held-out set.
- Every reported numerical claim needs traceable experimental evidence.
- If exact bit-for-bit reproduction is not guaranteed, document that limitation.

Dataset version for seed partitions: `0.5.0`. Random seed: `20261009`.

## Phase 10 execution

```bash
python3 scripts/run_held_out_evaluation.py --seed 20261009
```

If dependencies cannot be installed (PyPI egress), label results **unavailable** and do not fabricate numbers. Evidence ledger: `docs/EVIDENCE_LEDGER.md`.

## What this plan still does not contain

- No confirmed novel scientific contribution.
- No external-tool baseline measurement.
- Definition of Done (section 20) is met at `1.0.0` after Phase 5 warm-host clean-venv attestation of criterion 14. Residual research limitations remain disclosed. See `docs/RELEASE_CHECKLIST.md` and `docs/FINAL_RESEARCH_REPORT.md`.
- Phase 11/12 do not upgrade H1/H2 beyond `supported_on_this_sample` or H3 beyond inconclusive/UNRESOLVED.
