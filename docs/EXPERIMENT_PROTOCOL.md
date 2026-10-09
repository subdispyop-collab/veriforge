# Experiment protocol

Protocol version: `0.5.0`  
Protocol id: `veriforge-phase5-research-protocol`  
Status: **frozen for Phase 5** as a preregistered protocol.

Phase 10 held-out execution uses a separate protocol document:

- Protocol id: `veriforge-phase10-held-out-evaluation`
- Protocol version: `1.0.0`
- Details: `experiments/protocols/phase10-held-out-protocol.md`
- Runner: `scripts/run_held_out_evaluation.py`

This document freezes the initial research protocol required by specification §9 and Phase 5. Hypotheses remain hypotheses until held-out evidence supports them.

## Research question

> Does SMT-based equivalence checking improve the detection and rejection of incorrect arithmetic rewrites, and what computational overhead does it introduce under a defined, restricted arithmetic model?

## Hypotheses (preregistered; not findings)

1. Verification identifies incorrect candidates within the supported model when the encoding and solver are correct.
2. Verification introduces measurable computational overhead.
3. The overhead and success rates vary by expression complexity and transformation category.

## Baselines (§9.3)

Defined in `veriforge.experiment_engine.baseline_catalog()`. Phase 10 measurement status is recorded in evaluation reports / `baseline_catalog_phase10`.

| Id | Name | SMT | Production optimizer | Status |
| --- | --- | --- | --- | --- |
| `baseline.original_no_optimization` | Original expression without optimization | no | no | harness implemented (Phase 10) |
| `baseline.rule_based_without_smt` | Rule-based optimizer without SMT verification | no | yes (eval harness) | harness implemented (Phase 10) |
| `baseline.verification_enabled` | Verification-enabled optimizer | yes | yes | harness implemented (Phase 10) |
| `baseline.testing_only_validation` | Testing-only candidate validation (EVALUATION_ONLY harness) | yes | no | harness implemented (Phase 10) |
| `baseline.external_tool` | Existing relevant tool or method | — | — | **not_selected** |

Differences between baselines must be documented when they are measured. Systems are not compared under incompatible semantics or unequal workloads without explaining the limitation. If a host cannot import Z3, baseline results are **unavailable**.

## Primary outcomes

The specification does not use the heading "primary outcomes." Outcomes named by §9.1 and §2:

- Detection and rejection of incorrect arithmetic rewrites (error-detection effectiveness)
- Computational overhead of SMT-based equivalence checking
- Correctness of accepted rewrites under the defined model
- Execution-performance trade-offs, measured separately from verification overhead

Results for every outcome remain **unavailable** until a later phase runs the evaluation.

## Datasets

- Versioned partitions under `datasets/development/` and `datasets/held_out/`
- Metadata and per-case fields required by §9.4 (see `datasets/README.md`)
- Near-duplicate keys prevent leakage across partitions (`veriforge.dataset_engine`)
- Artificial 90/10 mix is a **controlled configuration**, labeled as not real-world prevalence

## Experiment run records

Every experiment run records:

- Unique `run_id`
- `configuration_fingerprint` (SHA-256 of sorted JSON configuration)
- Protocol version, software version
- Optional baseline id, dataset version/partition, seed, semantic mode, bit width
- Raw observations on the filesystem (`experiments/raw/<run_id>/`)
- Run metadata index in SQLite (`experiments/experiment_runs.sqlite3`)

Phase 5 validates this machinery. Phase 7 deepens audit export/replay (`veriforge.audit_engine`, protocol id `veriforge-phase7-audit-protocol`, version `0.7.0`): §13 optimization-run fields, JSON/CSV export with result links, secret redaction, integrity checks, and raw (`experiments/raw/`) vs derived (`experiments/reports/`) separation. Phase 6 adds `veriforge.benchmark_engine` (protocol id `veriforge-phase6-benchmark-protocol`, version `0.6.0`) for separate timing of parse, optimize, candidate generation, translate, solve, execute, with warmups, seeds, timeout policy, environment records, medians/variability, and reproduction from saved configuration. Benchmark engine runs on the development partition are **not** held-out research conclusions.

## Metric calculations

Metrics are computed only from stored raw observations (`compute_metrics_from_observations`):

- Detection rate among detectable (incorrect / mutation) cases
- Timeout and UNKNOWN rates among samples
- Counts of equivalent / counterexample / other statuses
- **Results by class** (transformation category), not only aggregate accuracy

Known-case unit tests validate the arithmetic of these calculations. Those fixture numbers are not research findings.

## Explicit non-goals

- No invented experimental results, citations, or scientific findings
- Phase 6 engine-validation timings on the development partition are not research findings
- Phase 7 audit exports and integrity checks do not constitute research evaluation
- Phase 10 does not start Phase 11 independent review
- Baseline 5 remains not selected unless a fair external comparison is later implemented

## Reproduction note

Exact bit-for-bit reproduction of solver timing may fail because of solver, platform, or timing nondeterminism. Phase 6 records that disclosure on every `BenchmarkConfiguration` and `BenchmarkReport`. Phase 7 replay uses the recorded configuration fingerprint and semantic settings; timings may still differ. Phase 10 held-out reports inherit the same nondeterminism disclosure. Timing nondeterminism has not been measured as a quantitative bound.
