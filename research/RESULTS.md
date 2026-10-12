# Results

The measured study is `veriforge-canonical-form-v1`. Software version `1.0.0`. Protocol SHA-256 `e5cb120f983a8df481b1db2c52aa92d8293eb80e94251b1e536c8fa71646cd00`, locked before the dataset existed. Dataset `datasets/canonical_form_v1/cases.jsonl`, 57 lines, SHA-256 `e7de7560c6fa46f23038d6f2ea3701d867d3114fdd7d1b323cf672c6f4a5f37a`. Held-out file: 8 lines. Python 3.12.3. Z3 `4.8.17`. cvc5 line `This is cvc5 version 1.3.2`.

Raw rows: `experiments/reports/canonical-form-v1/cases.jsonl`. Summary: `experiments/reports/canonical-form-v1/summary.json`. The counts below are that summary. Exhaustive `not_computed` was 0. Polynomial `not_computed` was 0. Polynomial `equivalent` with exhaustive `non_equivalent` was 0.

## Primary question

Integer coefficient comparison was the wrong semantics on 9 pairs: exhaustive label `equivalent` and polynomial verdict `counterexample`. The canonical checker returned `EQUIVALENT` on all 9. Numerator 9, denominator 9. Wilson 95% interval `[0.7008549515804559, 1.0]`.

Those pairs are `cf-0031`, `cf-0034`, `cf-0037`, `cf-0040`, `cf-0043`, `cf-0046`, `cf-0049`, `cf-0052`, and `cf-0055`. Each is width 1. The nine families are `sub_swap`, `sub_vs_add`, `add_self_zero`, `falling_pair`, `square_vs_var`, `triple_vs_var`, `two_squares`, `plus_two`, and `double_sum`. Family numerator 9, family denominator 9, same Wilson interval. Each family contributes one pair, so the family count is not an extra sample.

Widths 2 and 4 of those same families are exhaustive `non_equivalent`. They are not in the primary denominator. The checker returned `NOT_EQUIVALENT` on them.

## False equivalence

Denominator: 27 exhaustive `non_equivalent` pairs.

| Procedure | Numerator | Denominator | Wilson 95% |
| --- | --- | --- | --- |
| Canonical checker | 0 | 27 | `[0.0, 0.12455502974186705]` |
| Z3 4.8.17 | 0 | 27 | `[0.0, 0.12455502974186705]` |
| cvc5 1.3.2 | 0 | 27 | `[0.0, 0.12455502974186705]` |

By width, all three procedures are 0/3 at width 1, 0/12 at width 2, and 0/12 at width 4. The width-1 and width-2/4 intervals printed by the script have a lower endpoint of `5.551115123125783e-17` or `2.7755575615628914e-17` when the numerator is 0. That is a floating-point residue of the Wilson function. The numerator is 0.

## False rejection

Denominator: 30 exhaustive `equivalent` pairs. Canonical `NOT_EQUIVALENT`, Z3 `counterexample_found`, and cvc5 `counterexample_found` are each 0/30. Wilson 95% `[0.0, 0.11351339317396876]`. By width: 0/16 at width 1, 0/7 at width 2, 0/7 at width 4, for each procedure.

## Decisive rate

Denominator: 57 pairs. Canonical statuses `EQUIVALENT` or `NOT_EQUIVALENT`: 57/57. Z3 `equivalent_within_model` or `counterexample_found`: 57/57. cvc5 the same: 57/57. Wilson 95% `[0.9368611651470209, 0.9999999999999998]` for each. Counts: canonical 30 `EQUIVALENT` and 27 `NOT_EQUIVALENT`. Z3 and cvc5 match those counts with their own status names. No `UNKNOWN`, `TIMEOUT`, `UNSUPPORTED`, or `ERROR` on this set.

## Time

Initialization, excluded from the per-case sums: Z3 empty solver `0.012033996001264313` seconds, cvc5 `--version` `0.006565760999365011` seconds.

Per-case seconds, n=57:

| Clock | Sum | Median |
| --- | --- | --- |
| Canonical wall around `decide_mode_b` | `0.007584139995742589` | `0.00012991299809073098` |
| Z3 wall around `verify_equivalence_timed` | `0.3974383819877403` | `0.006064753997634398` |
| Z3 solver field only | `0.1880304170117597` | `0.002636724999319995` |
| cvc5 process wall | `0.2561598999782291` | `0.003891644002578687` |

On these 57 expressions the canonical wall sum is smaller than either solver wall sum. The expressions have syntactic degree at most 2 and at most 3 variables. This is not a measurement of hard bit-vector problems. No superiority test was preregistered.

## Earlier gate

`scripts/method_discovery_analysis.py` still checks the NO-GO preregistration and prints `pair_count` 0. That script was not the analysis of this dataset. It does not score the 57 pairs.
