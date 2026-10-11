# Confirmatory protocol v2

- Protocol id: `veriforge-confirmatory-v2`
- Software version under test: `1.0.0` (not bumped)
- Dataset id: `confirmatory-v2`
- Dataset path: `datasets/confirmatory_v2/cases.jsonl`
- Historical file `datasets/held_out/cases.jsonl` is not an input and is not rewritten.
- Dataset `datasets/assurance_v1/cases.jsonl` is not an input.
- This file is hashed before the dataset file is written and before any solver status or solver time on these pairs is computed.
- Construction intent is not a ground-truth label and is not a stopping rule.

## Primary hypothesis

H_false_eq: On this new family-clustered set, production Z3’s false-equivalence count is the number of pairs whose oracle label is `non_equivalent` and whose `verify_equivalence_timed` status is `equivalent_within_model`.

The hypothesis is estimated, not accepted because an earlier census was zero. There is no numeric pass threshold. The result is the count, the denominator, the family count, and a Wilson 95% interval, reported separately by semantic mode.

## Outcome

Primary outcome: false equivalence, as defined above.

Secondary outcomes, not substitutes for the primary outcome:

- Correct rejection: oracle `non_equivalent` and status `counterexample_found`.
- False rejection: oracle `equivalent` and status `counterexample_found`.
- Correct acceptance: oracle `equivalent` and status `equivalent_within_model`.
- Unresolved: `unknown`, `timeout`, `unsupported`, `invalid_input`, `not_computed`, `solver_error`, `translation_error`, `verification_error`. These are not decisive verifications and are not folded into the false-equivalence numerator or denominator.

## Independent unit

The independent unit is the rewrite family. Pairs that share a family are repeated observations, not independent cases. Pair counts are reported with their denominators and are not described as independent samples.

## Inclusion

Every row in the template block below is included once for each of these three settings:

- Mode A, width omitted
- Mode B, width 4
- Mode B, width 8

That is 12 families, 2 templates each, 3 settings: 72 pairs. No template is added or removed after this file is hashed.

## Exclusion

- `datasets/held_out/cases.jsonl` and `datasets/assurance_v1/cases.jsonl` are excluded.
- Oracle labels `unsupported`, `invalid_input`, and `not_computed` are excluded from false-equivalence denominators and listed as coverage.
- A category or mode with fewer than 4 families that have at least one pair in the denominator is `insufficient_sample` for that category or mode. Categories are not merged to reach 4.
- The run stops after one generation, one labeling pass, and one solver pass. Families are not added after solver output exists.

## Sample-size target

Target before any result on this file: 12 families and 72 pairs, with 6 families whose construction intent is `equivalent` and 6 whose construction intent is `non_equivalent`. Intent is not the label. A family-level conclusion requires at least 4 families in that oracle class. Below that, the conclusion is `insufficient_sample`.

## Label source

Same oracles as protocol `veriforge-assurance-v1`, applied only after this file’s hash is recorded:

- Mode A: polynomial identity, term budget 4096.
- Mode B: exhaustive independent evaluation when the assignment space is at most 65536, otherwise `not_computed`.
- Parse failures from the independent parser: `unsupported` or `invalid_input`.

## Analysis plan

For Z3 (`verify_equivalence_timed`, timeout 5 seconds) and for CVC5 (the same SMT-LIB semantics as `scripts/run_second_solver.py`, `--tlimit-per=5000`):

- False equivalence by mode: numerator and denominator.
- The same counts by family: a family contributes to the family denominator when it has at least one oracle `non_equivalent` pair in that mode. It contributes to the numerator when any such pair is a false equivalence.
- Wilson 95% intervals use `veriforge.stats_util.wilson_interval`. They are descriptive. Overlap does not create a second threshold.
- CVC5 is a second translation of the same semantics. Agreement is corroboration, not a proof that the translation is correct.

## Stopping rules

Generate the 72 pairs, label them, and run each solver once. Do not drop a family because its status is uniform. Do not add a family because a rate is zero or nonzero. Do not change the timeout, the widths, or the outcome definition after the hash.

## H3 preregistration

Historical H3 is unchanged: overhead and success rates vary by expression complexity and by transformation category.

This assessment uses only the new 72 pairs. It does not use `datasets/assurance_v1` timings.

Init time is measured once per solver and is not a per-case sample:

- Z3 init: time to construct an empty `z3.Solver()` after import, one observation.
- CVC5 init: wall time of one `cvc5 --version` process, one observation.

Per-case time:

- Z3: `TimedVerificationResult.solver_seconds` from `verify_equivalence_timed`.
- CVC5: wall time of that pair’s solver process. This includes process startup. It is not reported as check time.

Complexity is the independent parser’s operator count of the original source. Category is the template category. Categories are not merged.

Decision, in this order:

1. Reduce pairs to one number per family: the median of that family’s per-case times. Families with no finite per-case time are excluded from the correlation and counted.
2. Spearman rho between family median operator count and family median per-case time. Bootstrap the rho with 2000 resamples of families, seed `20261012`, using the same percentile indexes as `bootstrap_median_interval`.
3. Complexity overhead is supported only if rho is defined, rho is strictly positive, and the bootstrap interval lies entirely above 0. If rho is undefined or the interval contains 0, this arm is unresolved.
4. Category overhead uses families whose oracle label class is the category `equivalent` or `non_equivalent`. A class with fewer than 4 families is insufficient and is not merged. Category overhead varies only if both classes are sufficient and their bootstrap median intervals for family median time are disjoint.
5. Success is a finite decisive status: `equivalent_within_model` or `counterexample_found`. Failure for the rate is `timeout` or `unknown`. Other statuses are excluded from this rate and counted. A class with fewer than 4 families is insufficient. Success rates vary only if both classes are sufficient and their Wilson intervals for the timeout-or-unknown rate are disjoint.
6. Historical H3 is supported only if arms 3, 4, and 5 all hold. If arm 3 or 4 holds and arm 5 does not, H3 is `not_supported`. If arm 3 is unresolved or a required class is insufficient, H3 stays `unresolved`.
7. Init times and evaluator execution times are reported and do not decide H3.

One H3 pass. No second grid after seeing rho.

## Ablation

On these same 72 pairs, after labels exist, time and score four arms:

1. `verifier`: `verify_equivalence_timed`.
2. `verifier_plus_concrete`: the verifier result, plus one extra concrete comparison of the two sides at the all-zero assignment when both parse. If the verifier said `equivalent_within_model` and the concrete values differ, the arm status becomes `concrete_counterexample`.
3. `verifier_plus_independent_encoder`: `encode_difference`. A false equivalence for this arm is an encoder verdict `equivalent` on an oracle `non_equivalent` pair.
4. `full_pipeline`: `audit_equivalence` with `run_smt=True`. A false equivalence is status `equivalent_within_model` on an oracle `non_equivalent` pair.

Wall time is the sum of arm elapsed times. False equivalence uses the same denominators as the primary outcome. If an arm’s false-equivalence count equals the verifier arm’s count and its wall time is higher, the arm did not improve the primary outcome on this set.

## Templates

```json
[
  {"family": "comm_add", "category": "equivalent_algebraic", "intent": "equivalent", "original": "(a + b)", "candidate": "(b + a)"},
  {"family": "comm_add", "category": "equivalent_algebraic", "intent": "equivalent", "original": "((a + b) + c)", "candidate": "(c + (a + b))"},
  {"family": "comm_mul", "category": "equivalent_algebraic", "intent": "equivalent", "original": "(a * b)", "candidate": "(b * a)"},
  {"family": "comm_mul", "category": "equivalent_algebraic", "intent": "equivalent", "original": "((a * b) * c)", "candidate": "(c * (a * b))"},
  {"family": "assoc_mul", "category": "equivalent_algebraic", "intent": "equivalent", "original": "((a * b) * c)", "candidate": "(a * (b * c))"},
  {"family": "assoc_mul", "category": "equivalent_algebraic", "intent": "equivalent", "original": "((a * b) * (c * d))", "candidate": "(a * (b * (c * d)))"},
  {"family": "sub_neg", "category": "equivalent_algebraic", "intent": "equivalent", "original": "(a - b)", "candidate": "(a + (-b))"},
  {"family": "sub_neg", "category": "equivalent_algebraic", "intent": "equivalent", "original": "((a - b) - c)", "candidate": "((a + (-b)) + (-c))"},
  {"family": "cancel_add", "category": "equivalent_algebraic", "intent": "equivalent", "original": "((a + b) - b)", "candidate": "a"},
  {"family": "cancel_add", "category": "equivalent_algebraic", "intent": "equivalent", "original": "((a + 3) - 3)", "candidate": "a"},
  {"family": "right_factor", "category": "equivalent_algebraic", "intent": "equivalent", "original": "((a * b) + (c * b))", "candidate": "((a + c) * b)"},
  {"family": "right_factor", "category": "equivalent_algebraic", "intent": "equivalent", "original": "((a * 2) + (b * 2))", "candidate": "((a + b) * 2)"},
  {"family": "add_const", "category": "non_equivalent", "intent": "non_equivalent", "original": "(a + 1)", "candidate": "a"},
  {"family": "add_const", "category": "non_equivalent", "intent": "non_equivalent", "original": "(b + 2)", "candidate": "b"},
  {"family": "mul_self", "category": "non_equivalent", "intent": "non_equivalent", "original": "(a * a)", "candidate": "(a + a)"},
  {"family": "mul_self", "category": "non_equivalent", "intent": "non_equivalent", "original": "(b * b)", "candidate": "(b + b)"},
  {"family": "sub_swap", "category": "non_equivalent", "intent": "non_equivalent", "original": "(a - b)", "candidate": "(b - a)"},
  {"family": "sub_swap", "category": "non_equivalent", "intent": "non_equivalent", "original": "((a - b) - c)", "candidate": "(c - (a - b))"},
  {"family": "const_gap", "category": "non_equivalent", "intent": "non_equivalent", "original": "(a + 4)", "candidate": "(a + 1)"},
  {"family": "const_gap", "category": "non_equivalent", "intent": "non_equivalent", "original": "(b + 6)", "candidate": "(b + 2)"},
  {"family": "drop_factor", "category": "non_equivalent", "intent": "non_equivalent", "original": "((a * b) + a)", "candidate": "(a * b)"},
  {"family": "drop_factor", "category": "non_equivalent", "intent": "non_equivalent", "original": "((a * b) + b)", "candidate": "(a * b)"},
  {"family": "wrap_alias", "category": "mode_dependent", "intent": "mode_dependent", "original": "(a + 15)", "candidate": "(a - 1)"},
  {"family": "wrap_alias", "category": "mode_dependent", "intent": "mode_dependent", "original": "(b + 15)", "candidate": "(b + (-1))"}
]
```
