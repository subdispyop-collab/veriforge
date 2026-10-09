# Phase 10 held-out evaluation report

- Protocol: `veriforge-phase10-held-out-evaluation` v`1.0.0`
- Software: `0.10.0`
- Dataset version: `0.5.0`
- Seed: `20261009`
- Configuration fingerprint: `1b5a4a762b6485eca8668cc6e7dba93cd829246479cbeee00caf977c8fea5464`
- Created (UTC): `2026-10-09T20:05:42Z`
- Dependency available: `True`

## Dependency blocker

none

## Unavailable baselines

none

## Baseline runs

### `baseline.original_no_optimization`

- run_id: `7a818cd4-12e1-4228-8957-bc00182a5d96`
- observation_count: 8
- overall sample_count: 8; detection_rate: 0.3333333333333333; timeout_rate: 0.0; unknown_rate: 0.0
- by class:
  - `artificial_mutation`: n=1, detected=0, counterexample=0, equivalent=0, timeout=0, unknown=0
  - `boundary_value`: n=1, detected=0, counterexample=0, equivalent=0, timeout=0, unknown=0
  - `identity_preserving`: n=3, detected=0, counterexample=0, equivalent=0, timeout=0, unknown=0
  - `incorrect_rewrite`: n=1, detected=0, counterexample=0, equivalent=0, timeout=0, unknown=0
  - `nested_expression`: n=1, detected=0, counterexample=0, equivalent=0, timeout=0, unknown=0
  - `unsupported_or_malformed`: n=1, detected=1, counterexample=0, equivalent=0, timeout=0, unknown=0

### `baseline.rule_based_without_smt`

- run_id: `c46db134-e96b-4d0e-aa12-15ee44ff5aa5`
- observation_count: 8
- overall sample_count: 8; detection_rate: 0.3333333333333333; timeout_rate: 0.0; unknown_rate: 0.0
- by class:
  - `artificial_mutation`: n=1, detected=0, counterexample=0, equivalent=0, timeout=0, unknown=0
  - `boundary_value`: n=1, detected=0, counterexample=0, equivalent=0, timeout=0, unknown=0
  - `identity_preserving`: n=3, detected=0, counterexample=0, equivalent=0, timeout=0, unknown=0
  - `incorrect_rewrite`: n=1, detected=0, counterexample=0, equivalent=0, timeout=0, unknown=0
  - `nested_expression`: n=1, detected=0, counterexample=0, equivalent=0, timeout=0, unknown=0
  - `unsupported_or_malformed`: n=1, detected=1, counterexample=0, equivalent=0, timeout=0, unknown=0

### `baseline.verification_enabled`

- run_id: `1e09025c-7a8e-43e5-995b-a8afc24c0a87`
- observation_count: 8
- overall sample_count: 8; detection_rate: 1.0; timeout_rate: 0.0; unknown_rate: 0.0
- by class:
  - `artificial_mutation`: n=1, detected=1, counterexample=1, equivalent=0, timeout=0, unknown=0
  - `boundary_value`: n=1, detected=0, counterexample=0, equivalent=1, timeout=0, unknown=0
  - `identity_preserving`: n=3, detected=0, counterexample=0, equivalent=3, timeout=0, unknown=0
  - `incorrect_rewrite`: n=1, detected=1, counterexample=1, equivalent=0, timeout=0, unknown=0
  - `nested_expression`: n=1, detected=0, counterexample=0, equivalent=1, timeout=0, unknown=0
  - `unsupported_or_malformed`: n=1, detected=1, counterexample=0, equivalent=0, timeout=0, unknown=0

### `baseline.testing_only_validation`

- run_id: `f1505097-db35-4af9-934e-3814c653e663`
- observation_count: 8
- overall sample_count: 8; detection_rate: 0.375; timeout_rate: 0.0; unknown_rate: 0.0
- by class:
  - `artificial_mutation`: n=1, detected=1, counterexample=1, equivalent=0, timeout=0, unknown=0
  - `boundary_value`: n=1, detected=0, counterexample=0, equivalent=1, timeout=0, unknown=0
  - `identity_preserving`: n=3, detected=0, counterexample=0, equivalent=3, timeout=0, unknown=0
  - `incorrect_rewrite`: n=1, detected=1, counterexample=1, equivalent=0, timeout=0, unknown=0
  - `nested_expression`: n=1, detected=0, counterexample=0, equivalent=1, timeout=0, unknown=0
  - `unsupported_or_malformed`: n=1, detected=1, counterexample=0, equivalent=0, timeout=0, unknown=0

## Latency separation (solver vs execution)

- `baseline.original_no_optimization`: solver median=None (n=0); original exec median=2.8409000151441433e-05 (n=7); optimized exec median=2.8409000151441433e-05 (n=7)
- `baseline.rule_based_without_smt`: solver median=None (n=0); original exec median=2.6470000193512533e-05 (n=7); optimized exec median=2.5566000658727717e-05 (n=7)
- `baseline.verification_enabled`: solver median=4.757999977300642e-05 (n=7); original exec median=2.569900061644148e-05 (n=7); optimized exec median=2.5650000679888763e-05 (n=7)
- `baseline.testing_only_validation`: solver median=4.3060000280092936e-05 (n=7); original exec median=3.026000013051089e-05 (n=7); optimized exec median=1.650200010772096e-05 (n=7)

## Hypothesis status (not advance findings)

- **H1_verification_detects_incorrect**: supported_on_this_sample — 4/4 incorrect held-out cases detected (sample is small; not a general proof)
- **H2_verification_introduces_overhead**: supported_on_this_sample — positive solver_seconds observed (n=14); overhead is measurable but magnitude is host-specific
- **H3_varies_by_complexity_and_category**: inconclusive_on_this_sample — multiple categories present (['artificial_mutation', 'incorrect_rewrite']); sample sizes are too small for a stable category-effect claim

## Limitations

- Held-out sample size is small (seed partition); do not treat rates as population estimates.
- Exact bit-for-bit reproduction of solver timings is not guaranteed (platform / Z3 nondeterminism).
- Baseline external_tool remains not_selected.
- Rule-based-without-SMT is an evaluation harness; production optimize() remains verification-guided.
- Post-hoc SMT oracle on the rule-based-without-SMT baseline is used only for detection metrics, not for rewrite acceptance in that baseline.

## Novelty

No novelty claim. Literature review situates VERIFORGE among established translation-validation / equivalence-checking methods; confirmed novel research findings are not established.

