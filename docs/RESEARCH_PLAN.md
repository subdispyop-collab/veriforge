# Research plan

This file pre-registers the research design from the controlling specification. Every hypothesis below is a hypothesis to investigate. None is a finding. No held-out evaluation has been run. Results are unavailable.

No literature review was done. This file contains no citations and no novelty claim.

Protocol freeze for Phase 5: details required by §9 are locked in `docs/EXPERIMENT_PROTOCOL.md` (protocol version `0.5.0`). This plan keeps hypotheses as hypotheses and records only protocol details the specification already requires.

## Research question

Specified question, section 9.1:

> Does SMT-based equivalence checking improve the detection and rejection of incorrect arithmetic rewrites, and what computational overhead does it introduce under a defined, restricted arithmetic model?

The project vision in section 2 states the same evaluation target in these words: correctness, error-detection effectiveness, verification overhead, and execution-performance trade-offs of a conservative arithmetic optimizer supported by SMT-based equivalence checking.

The question is not a conclusion. The experiments may show benefits, limitations, or mixed results. Those experiments have not been run on the held-out set.

## Hypotheses

Specified in section 9.2. Status of each: not investigated. Results unavailable.

1. Verification identifies incorrect candidates within the supported model when the encoding and solver are correct.
2. Verification introduces measurable computational overhead.
3. The overhead and success rates vary by expression complexity and transformation category.

These sentences are not advance reports of what VERIFORGE will find.

## Baselines

Specified in section 9.3. Defined in code by `veriforge.experiment_engine.baseline_catalog()`. **None measured in Phase 5.**

1. Original expression without optimization (`baseline.original_no_optimization`).
2. Rule-based optimizer without SMT verification (`baseline.rule_based_without_smt`).
3. Verification-enabled optimizer (`baseline.verification_enabled`).
4. Testing-only candidate validation (`baseline.testing_only_validation`) — EVALUATION_ONLY harness.
5. An existing relevant tool or method (`baseline.external_tool`) — **not selected**.

Differences between baselines must be documented when they are built. Systems are not to be compared under incompatible semantics or unequal workloads unless that limitation is explained.

The two product configurations that feed baselines 2 and 3 remain: a verification-guided path (default, implemented) and an evaluation-only harness for incorrect candidates in `veriforge.fuzzer_suite` (implemented for detection tests; not a completed research measurement).

## Specified outcomes

The specification does not use the heading "primary outcomes." The outcomes named by the question and by section 2 are:

- Detection and rejection of incorrect arithmetic rewrites (error-detection effectiveness), under the defined restricted model.
- Computational overhead of SMT-based equivalence checking.
- Correctness of accepted rewrites under that model.
- Execution-performance trade-offs of the conservative optimizer, measured separately from verification overhead.

Results for every one of these are unavailable.

Section 10 quantities are measured independently by `veriforge.benchmark_engine` (Phase 6). Development-partition runs validate the engine only and are **not** research conclusions:

- Parsing time.
- Optimization time.
- Candidate-generation time.
- AST-to-Z3 translation time.
- Solver time.
- End-to-end verification latency.
- Original expression execution time.
- Optimized expression execution time.
- Timeout rate.
- UNKNOWN rate.
- Verification completion rate.
- Rejection and counterexample rates.

Specified reporting rules (applied by the Phase 6 report helpers to engine-validation data; not yet applied to held-out research data):

- Report medians and variability.
- Use confidence intervals and statistical tests only where their assumptions hold.
- Report performance by class and transformation category, not only as one aggregate accuracy number.
- Do not treat a large set of related generated expressions as that many independent observations.
- Do not claim an execution speedup because an expression is shorter, the AST has fewer nodes, the solver returns faster, or the dashboard looks efficient.
- Distinguish the speed of finding a proof from the speed of executing an optimized expression.
- If a benchmark shows no improvement or shows a slowdown, report that.
- A passing randomized test is not a mathematical proof of equivalence.
- A solver result is a statement about the submitted formula, not proof that the implementation matches this plan.

Metric *calculation* functions are unit-tested against known fixture observations in Phase 5. Fixture numbers are not findings.

## Method constraints already fixed

These constraints are part of the specification. They are recorded so later phases do not weaken them.

- Freeze the question, hypotheses, methods, and outcomes before the final held-out evaluation. This file plus `docs/EXPERIMENT_PROTOCOL.md` are that pre-registration.
- Keep development cases separate from held-out cases (`datasets/development/`, `datasets/held_out/`).
- Prevent near-duplicates and variants of the same transformation from leaking across partitions (`near_duplicate_key` + `assert_no_cross_partition_leakage`).
- For every dataset, record version, generation procedure, semantic model, random seed, case identifier, expected outcome where independently known, transformation category, complexity characteristics, and inclusion or exclusion reason.
- An artificial mixture of 90% correct and 10% incorrect candidates may be one controlled configuration. It must not be presented as an estimate of real-world error prevalence. See `ARTIFICIAL_90_10_MIX` / development metadata `controlled_mix_label`.
- Use fixed recorded seeds where applicable, repeated trials, warmups where appropriate, identical workloads for paired comparisons, a documented timeout policy, controlled configurations, a recorded software and hardware environment, and raw measurement storage.
- The benchmark must not be tuned against the held-out evaluation set.
- Every reported numerical claim needs traceable experimental evidence.
- If exact bit-for-bit reproduction is not guaranteed, document that limitation.
- Every experiment run has a unique `run_id` and a `configuration_fingerprint`; raw observations are stored on the filesystem and indexed in SQLite.

Dataset version for the Phase 5 seed partitions: `0.5.0`. Random seed: `20261009`. Held-out evaluation: **not run**.

## What this phase does not contain

- No held-out protocol execution.
- No baseline measurement campaign.
- No sample size, rate, duration, or statistical *research* result.
- No source has been reviewed. A novelty claim waits on the literature review required by section 16.
- No Streamlit UI. Phase 6 benchmark engine exists for development-partition validation only; no held-out research evaluation.
