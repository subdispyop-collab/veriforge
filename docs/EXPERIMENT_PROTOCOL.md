# Experiment protocol

Protocol version: `0.5.0`  
Protocol id: `veriforge-phase5-research-protocol`  
Status: **frozen for Phase 5** as a preregistered protocol. Not executed against held-out data.

This document freezes the initial research protocol required by specification §9 and Phase 5. Hypotheses remain hypotheses. No experimental findings are reported here.

## Research question

> Does SMT-based equivalence checking improve the detection and rejection of incorrect arithmetic rewrites, and what computational overhead does it introduce under a defined, restricted arithmetic model?

## Hypotheses (preregistered; not findings)

1. Verification identifies incorrect candidates within the supported model when the encoding and solver are correct.
2. Verification introduces measurable computational overhead.
3. The overhead and success rates vary by expression complexity and transformation category.

## Baselines (§9.3)

Defined in `veriforge.experiment_engine.baseline_catalog()`. Status in Phase 5: **defined, not measured**.

| Id | Name | SMT | Production optimizer | Status |
| --- | --- | --- | --- | --- |
| `baseline.original_no_optimization` | Original expression without optimization | no | no | defined_not_measured |
| `baseline.rule_based_without_smt` | Rule-based optimizer without SMT verification | no | yes | defined_not_measured |
| `baseline.verification_enabled` | Verification-enabled optimizer | yes | yes | defined_not_measured |
| `baseline.testing_only_validation` | Testing-only candidate validation (EVALUATION_ONLY harness) | yes | no | defined_not_measured |
| `baseline.external_tool` | Existing relevant tool or method | — | — | **not_selected** |

Differences between baselines must be documented when they are measured. Systems are not compared under incompatible semantics or unequal workloads without explaining the limitation.

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

Phase 5 validates this machinery. Full audit export/replay deepens in Phase 7. The Phase 6 benchmark engine (separate timing of parse, optimize, translate, solve, execute) is **not** part of this protocol freeze beyond naming the required quantities.

## Metric calculations

Metrics are computed only from stored raw observations (`compute_metrics_from_observations`):

- Detection rate among detectable (incorrect / mutation) cases
- Timeout and UNKNOWN rates among samples
- Counts of equivalent / counterexample / other statuses
- **Results by class** (transformation category), not only aggregate accuracy

Known-case unit tests validate the arithmetic of these calculations. Those fixture numbers are not research findings.

## Explicit non-goals for Phase 5

- No held-out evaluation run
- No Streamlit UI
- No full benchmark timing engine (Phase 6)
- No invented experimental results or scientific findings

## Reproduction note

Exact bit-for-bit reproduction of solver timing may fail because of solver, platform, or timing nondeterminism. That limitation is recorded; it has not been measured as a quantitative bound in Phase 5.
