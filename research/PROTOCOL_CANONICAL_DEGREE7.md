# Protocol: degree-7 canonical-form evaluation

- Record id: `veriforge-canonical-degree7-v1`
- Software version: `1.0.0` (not bumped)
- Branch point: `d6d0ba1d6fee3c418b7184c1e0c04e153bd4047e`
- Created at: `2026-10-12T15:06:00Z`
- This file is hashed before any pair in `datasets/canonical_degree7_v1/` exists.
- It does not edit `datasets/canonical_form_v1/`, `experiments/reports/canonical-form-v1/`, `datasets/canonical_wide_v1/`, or `experiments/reports/canonical-wide-v1/`.
- The representation is not a new theorem. The Keller and Olson attribution remains second-hand through IACR eprint 2022/1364.

## Question

On degree-6 and degree-7 products of `(a+b+c+d+e+f)`, at unsigned widths 1, 2, 4, 8, and 32, what are the decisive rate, the false-equivalence count, and the per-case time of the falling-factorial checker, of Z3 4.8.17, and of cvc5 1.3.2?

`UNKNOWN` is not equivalence. `TIMEOUT` is not equivalence. A row that hits the term cap or the clock stays in the file and counts as non-decisive.

## Term cap

The cap is the falling-factorial term count of the degree-7 product, measured on that expression before any pair file existed:

| Product | Monomial terms | Falling-factorial terms | Syntactic box |
| --- | --- | --- | --- |
| six factors, degree 6 | 462 | 923 | `7^6 = 117649` |
| seven factors, degree 7 | 792 | 1715 | `8^6 = 262144` |

Term budget: `1715`. Certificate grid budget: `262144`. Maximum syntactic degree per variable: `12`. Maximum variable count: `6`. Timeout: `5` seconds. These are the code defaults. They are not retuned after this hash.

A row whose expansion exceeds 1715 returns `UNKNOWN` and the detail names the actual term count and the cap. A row whose certificate grid exceeds 262144 returns `UNKNOWN`. A row that passes the clock returns `TIMEOUT`. None of those statuses is `EQUIVALENT`.

## Templates

Widths, in order: `1`, `2`, `4`, `8`, `32`. The generator emits one row per template per width. It aborts if a literal is outside `[0, 2^w - 1]`. It does not drop a row. It does not consult a solver while generating.

`construction_intent` is not a label. The degree-6 strings are the ones that previously returned `UNKNOWN` at term count 462.

```json
[
  {"family": "degree_six_self", "degree": 6, "intent": "identical", "original": "(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)", "candidate": "(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)"},
  {"family": "degree_six_zero", "degree": 6, "intent": "separating", "original": "(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)", "candidate": "0"},
  {"family": "degree_seven_self", "degree": 7, "intent": "identical", "original": "(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)", "candidate": "(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)"},
  {"family": "degree_seven_zero", "degree": 7, "intent": "separating", "original": "(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)", "candidate": "0"}
]
```

Expected row count: 4 templates times 5 widths = 20. Case ids `cd-0001` through `cd-0020`. Partition `canonical_degree7_v1`. Output path `datasets/canonical_degree7_v1/cases.jsonl`.

`datasets/held_out/cases.jsonl` is not rewritten. The run aborts unless it still has 8 non-empty lines and SHA-256 `36e4218e8026320a8d7988721a8051c286a980e7876a1ad226d10ef1ba866063`. `datasets/canonical_form_v1/cases.jsonl` must stay 57 lines with SHA-256 `e7de7560c6fa46f23038d6f2ea3701d867d3114fdd7d1b323cf672c6f4a5f37a`. `datasets/canonical_wide_v1/cases.jsonl` must stay 105 lines with SHA-256 `4ca42c4ddfa73e26e74fa10077e56b237f18921662d26b8e0ea6eb1f9c941c82`. The two earlier summary files must stay at SHA-256 `5f6fc25c5f25aed9836fa10edaab114b609b79a3cc65024e5465cf1ea93a3cde` and `9ac5cf6ae42d16c3875fa05cc5056f71ad50ac7c623246df6f30caef97891196`.

## Ground truth

Ground truth is not `decide_mode_b`, not Z3, and not cvc5.

1. If the Mode B domain size `2^(width * variable_count)` is at most `65536`, the label is `exhaustive_oracle.exhaustive_compare` with that assignment budget: `equivalent`, `non_equivalent`, or `not_computed`.
2. Otherwise the reference evaluator is run on a fixed point set that does not come from the checker. For each variable the values are the unique members of `{0, 1, min(2, 2^w - 1), 2^w - 1}`. If the cartesian product has size at most `4096`, every point is evaluated. If it is larger, only these points are evaluated: all variables `0`; all variables `2^w - 1`; and, for each variable, that variable set to `1` and the others set to `0`. A point where the two Mode B values differ is a confirmed counterexample and the label is `non_equivalent`. If none differs, the label is `not_computed`. Absence of a witness is not equivalence.

`not_computed` stays out of the false-equivalence denominator and out of the false-rejection denominator.

## Outcomes

Reported for every degree, every width, and every degree-width pair, and for the full set.

False equivalence. Denominator: ground-truth `non_equivalent`. Numerator: canonical status `EQUIVALENT`, Z3 status `equivalent_within_model`, or cvc5 status `equivalent_within_model`. Wilson 95% when the denominator is positive. An empty denominator is null, not a zero rate.

False rejection. Denominator: ground-truth `equivalent`. Numerator: canonical `NOT_EQUIVALENT`, Z3 `counterexample_found`, or cvc5 `counterexample_found`. Same Wilson rule.

Decisive rate. Denominator: every row in the slice, including `UNKNOWN` and `TIMEOUT`. Numerator: canonical status in `{EQUIVALENT, NOT_EQUIVALENT}`. For Z3 and cvc5, status in `{equivalent_within_model, counterexample_found}`. Every other status is non-decisive.

Time. Per-case wall-clock seconds around `decide_mode_b`, around `verify_equivalence_timed`, and around the cvc5 process. One Z3 initialization and one cvc5 initialization, excluded from the per-case sums. For each slice, report `n`, sum, and median.

Also report the term budget `1715`, the measured monomial and falling-factorial counts above, and every canonical `UNKNOWN` or `TIMEOUT` detail.

## Solvers

Z3 4.8.17 through `verify_equivalence_timed`, timeout 5 seconds. cvc5 1.3.2 through `scripts.run_second_solver`, per-query limit 5000 ms. A solver counterexample counts only after `reference_evaluator.evaluate` confirms it.

## Analysis script

`scripts/run_canonical_degree7.py` checks this file's SHA-256 against `research/protocol_canonical_degree7.json`, checks that `dataset_generated_before_hash` is false, writes the dataset, then runs the three procedures. It refuses to start if the hash differs. Raw rows: `experiments/reports/canonical-degree7-v1/cases.jsonl`. Summary: `experiments/reports/canonical-degree7-v1/summary.json`.

## Stopping rule

One run. Do not drop a non-decisive row. Do not retune the term cap or the grid budget. Do not rewrite the 57-pair study or the 105-row study. A false `EQUIVALENT` on a ground-truth `non_equivalent` row is kept.
