# Results and analysis

Scored run: `python3 scripts/run_assurance_experiment.py` after protocol SHA-256 `3e2f3c81d58e70bc789c8470f82865bd8bbcf8027a96ec7ffdc6c4081a60aa13` recorded at `2026-10-11T16:43:36Z`. Dataset SHA-256 `36e430e0bdecfb47ac1d2ee254e7d2ba48a0f06664f7c34b7fd6e206fb746ae2`. Raw rows: `experiments/reports/assurance-v1/raw/cases.jsonl`. Summary: `experiments/reports/assurance-v1/summary.json`.

The serialization crash before the successful run happened before any summary file was written. The successful process is the scored run. Held-out labels were not used to change the decision rule.

## Dataset

463 pairs, 27 families, 310 development, 153 held-out. Categories, all at least 30 pairs: equivalent_algebraic 283, non_equivalent 70, robustness 45, mode_dependent 35, boundary 30.

Oracle labels, all partitions: equivalent 316, non_equivalent 96, unsupported 36, invalid_input 13, not_computed 2.

Held-out oracle labels: equivalent 64, non_equivalent 54, unsupported 34, not_computed 1.

The not_computed pairs are distributivity and factoring at width 8 with three variables. Domain size `2^(8*3) = 16777216`, above budget 65536. They are not called exhaustive.

Historical `datasets/held_out` remains 8 cases.

## Hypotheses

| ID | Rule | Result |
| --- | --- | --- |
| H_audit | SMT arm required | `inconclusive`. `import z3` failed. No SMT count is reported. |
| H_test | `r(10000) < r(10)` on held-out non-equivalent pairs, denominator at least 30 | `not_supported`. Both rates are `0/54`. |
| H3 historical | Solver time by category | Unresolved. Solver time was not measured. |
| H3_exec | Spearman rho of operator count vs median evaluator time `> 0` | rho `0.9684560277703408` on 48 configurations, so the preregistered point rule is met. This is evaluator time, not solver time. |

## Testing baseline (held-out)

False equivalence means a non-equivalent pair the tester did not distinguish. False difference means an equivalent pair it did distinguish.

| Budget | Misses | Non-equivalent denominator | Wilson 95% | False differences | Equivalent denominator | Wall-clock seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 10 | 0 | 54 | 0 to 0.0664135880908964 | 0 | 64 | 0.004081947001168373 |
| 100 | 0 | 54 | 0 to 0.0664135880908964 | 0 | 64 | 0.02535129399871039 |
| 1,000 | 0 | 54 | 0 to 0.0664135880908964 | 0 | 64 | 0.5068007940008101 |
| 10,000 | 0 | 54 | 0 to 0.0664135880908964 | 0 | 64 | 4.782053818000122 |

Cases where testing missed a bug SMT caught: not computed. Z3 did not run. Cases where SMT missed a bug testing caught: not computed for the same reason. On this set, testing and the non-SMT oracle agreed at every budget: 0 misses and 0 false differences. That does not mean testing matches SMT on other expressions. These pairs are small, and the boundary pool hits the differing constants.

## Other baselines on 118 held-out pairs with an equivalent or non-equivalent label

Production SMT: unavailable.

Independent Z3 encoder: unavailable.

CVC5: `import cvc5` failed. Bitwuzla: `import bitwuzla` failed. No comparison numbers.

Audited pipeline in the summary file: true accept 64/64 equivalent, false reject 0/64, true reject 54/54 non-equivalent, false accept 0/54. Establishing methods are the polynomial and exhaustive oracles that also supplied the labels. This is a contract check. It is not an independent accuracy estimate.

Rule-only baseline: predicted equivalent for 20 pairs, all of them actually equivalent. False accepts of non-equivalent pairs: 0. It abstained (`not_handled`) on 98 of 118 labeled pairs, including all 54 non-equivalent pairs. It is not a general solver. Abstention is not counted as a rejection.

## Mode traps

16 of 16 paired sources differed across Mode A and Mode B. Twelve are equivalences only after unsigned wrap (for example `(x + 255)` versus `(x - 1)` at width 8). Four parse as equivalent in Mode A and invalid in Mode B because a literal does not fit (for example `(x + x)` versus `(x * 2)` at width 1).

## Proposed rules

Eight algebraic rules passed the independent check in Mode A and in a Mode B width where every literal fits: distributivity, factoring, constant folding, `x - x`, `x + x → 2*x`, double negation, `-(a-b) → b-a`, and constant reassociation. They were not added to `default_rules()` because production Z3 admission did not run. `x*2` at width 1 and `x+5` at width 2 were rejected as bad candidates.

## Mutants

10 mutants, 10 detected, 0 survived, denominator 10. Fixtures are the ones in `run_mutants`. This is not a mutmut score. mutmut was not installed.

## Scaling

48 configurations, 30 trials after 3 warmup evaluations. Median evaluator time ranged from `6.415000370907364e-07` seconds (width 8, depth 1, one variable) to `3.3264999501625425e-06` seconds (width 64, depth 8, three variables). Bootstrap of the 48 configuration medians, 2,000 resamples, seed `20261011`: median `1.4072500107431551e-06`, interval `1.1584999697333842e-06` to `1.824000037231599e-06`. That interval is not a confidence interval for the Spearman correlation.

Operator-count reduction on five identity examples, separate from execution speed: `(x + 0)`, `(y - 0)`, `(z * 1)`, and `(a * 0)` go from 1 operator to 0; `(((x + 0) * 1) - 0)` goes from 3 operators to 0. No execution-speed claim.

## Localization

53 of 53 held-out non-equivalent pairs with a non-empty witness had a localized sub-expression that still differed (Wilson 95% about 0.932 to 1). Constant repairs proposed 29, verified 29. One further held-out non-equivalent pair, Mode A `(-1)` versus `255`, has an empty assignment because it has no variables; the summarizer skipped it. This localizer is engineering, not a new algorithm.

## Intent mismatches

Two: the width-8 three-variable distributivity and factoring pairs whose intent was `equivalent` and whose oracle label is `not_computed`. No intent of `non_equivalent` was oracle-equivalent except the width-1 development cases relabeled before the hash.

## Evaluator sweep

0 value disagreements between the production reference evaluator and the independent evaluator on the all-zero assignment for parsed benchmark sources, and 0 on the all-ones-top Mode B assignment.
