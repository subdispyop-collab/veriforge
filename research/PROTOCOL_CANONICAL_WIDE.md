# Protocol: wider unsigned canonical-form evaluation

- Record id: `veriforge-canonical-wide-v1`
- Software version: `1.0.0` (not bumped)
- Parent commit before this file: `524e0070a16248cc03117316f6aedc73fbcbac7c`
- Created at: `2026-10-12T14:38:59Z`
- This file is hashed before any pair in `datasets/canonical_wide_v1/` exists.
- It does not edit `research/PROTOCOL_CANONICAL_FORM.md`, `datasets/canonical_form_v1/`, or `experiments/reports/canonical-form-v1/`.
- The representation is not a new theorem. The Keller and Olson attribution remains second-hand through IACR eprint 2022/1364.

## Question

At unsigned widths 8 and 32, with widths 1, 2, and 4 kept as a control, what are the false-equivalence count, false-rejection count, decisive rate, and per-case time of the falling-factorial checker, of Z3 4.8.17, and of cvc5 1.3.2?

`UNKNOWN` is not equivalence. A row that hits the term cap stays in the file and counts as non-decisive.

## Procedure under test

`veriforge.falling_factorial.decide_mode_b`. Budgets are the code defaults and are not retuned after this hash:

- term budget `256`
- certificate grid budget `4096`
- maximum syntactic degree per variable `12`
- maximum variable count `6`
- timeout `5` seconds

The two `degree_six_*` templates are included because their expanded term count exceeds 256. If the checker returns `UNKNOWN` and names that cap, the row is kept.

## Templates

Widths, in order: `1`, `2`, `4`, `8`, `32`. Widths `1`, `2`, and `4` are the control. Widths `8` and `32` are the wide arm. The generator emits one row per template per width. It aborts if a literal is outside `[0, 2^w - 1]`. It does not drop a row. It does not consult a solver while generating.

`construction_intent` is not a label.

```json
[
  {"family": "comm_add", "intent": "integer_identity", "original": "(a + b)", "candidate": "(b + a)"},
  {"family": "cancel_sub", "intent": "integer_identity", "original": "(a - a)", "candidate": "0"},
  {"family": "add_zero", "intent": "integer_identity", "original": "(a + 0)", "candidate": "a"},
  {"family": "mul_one", "intent": "integer_identity", "original": "(a * 1)", "candidate": "a"},
  {"family": "nested_cancel", "intent": "integer_identity", "original": "((a + 1) - 1)", "candidate": "a"},
  {"family": "distribute", "intent": "integer_identity", "original": "(b * (a + 1))", "candidate": "((b * a) + b)"},
  {"family": "assoc_add", "intent": "integer_identity", "original": "((a + b) + c)", "candidate": "(a + (b + c))"},
  {"family": "const_gap", "intent": "separating", "original": "(a + 1)", "candidate": "a"},
  {"family": "drop_var", "intent": "separating", "original": "(a + b)", "candidate": "a"},
  {"family": "mul_vs_add", "intent": "separating", "original": "(a * b)", "candidate": "(a + b)"},
  {"family": "sub_swap", "intent": "modular_sensitive", "original": "(a - b)", "candidate": "(b - a)"},
  {"family": "sub_vs_add", "intent": "modular_sensitive", "original": "(a - b)", "candidate": "(a + b)"},
  {"family": "add_self_zero", "intent": "modular_sensitive", "original": "(a + a)", "candidate": "0"},
  {"family": "falling_pair", "intent": "modular_sensitive", "original": "(a * (a - 1))", "candidate": "0"},
  {"family": "square_vs_var", "intent": "modular_sensitive", "original": "(a * a)", "candidate": "a"},
  {"family": "triple_vs_var", "intent": "modular_sensitive", "original": "((a + a) + a)", "candidate": "a"},
  {"family": "two_squares", "intent": "modular_sensitive", "original": "((a * a) + (a * a))", "candidate": "0"},
  {"family": "plus_two", "intent": "modular_sensitive", "original": "((a + 1) + 1)", "candidate": "a"},
  {"family": "double_sum", "intent": "modular_sensitive", "original": "((a + b) + (a + b))", "candidate": "0"},
  {"family": "degree_six_self", "intent": "term_cap", "original": "(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)", "candidate": "(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)"},
  {"family": "degree_six_zero", "intent": "term_cap", "original": "(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)*(a+b+c+d+e+f)", "candidate": "0"}
]
```

Expected row count: 21 templates times 5 widths = 105. Case ids `cw-0001` through `cw-0105`. Partition `canonical_wide_v1`. Output path `datasets/canonical_wide_v1/cases.jsonl`.

`datasets/held_out/cases.jsonl` is not rewritten. The run aborts unless it still has 8 non-empty lines. `datasets/canonical_form_v1/cases.jsonl` is not rewritten.

## Ground truth

Ground truth is not `decide_mode_b`, not Z3, and not cvc5.

1. If the Mode B domain size `2^(width * variable_count)` is at most `65536`, the label is `exhaustive_oracle.exhaustive_compare` with that assignment budget: `equivalent`, `non_equivalent`, or `not_computed`.
2. Otherwise the reference evaluator is run on a fixed point set that does not come from the checker. For each variable the values are the unique members of `{0, 1, min(2, 2^w - 1), 2^w - 1}`. If the cartesian product has size at most `4096`, every point is evaluated. If it is larger, only these points are evaluated: all variables `0`; all variables `2^w - 1`; and, for each variable, that variable set to `1` and the others set to `0`. A point where the two Mode B values differ is a confirmed counterexample and the label is `non_equivalent`. If none differs, the label is `not_computed`. Absence of a witness is not equivalence.

`not_computed` stays out of the false-equivalence denominator and out of the false-rejection denominator.

## Outcomes

Reported by width, and again for the control widths together and the wide widths together.

False equivalence. Denominator: ground-truth `non_equivalent`. Numerator: canonical status `EQUIVALENT`, Z3 status `equivalent_within_model`, or cvc5 status `equivalent_within_model`. Wilson 95% when the denominator is positive. An empty denominator is null, not a zero rate.

False rejection. Denominator: ground-truth `equivalent`. Numerator: canonical `NOT_EQUIVALENT`, Z3 `counterexample_found`, or cvc5 `counterexample_found`. Same Wilson rule.

Decisive rate. Denominator: every row at that width, including `UNKNOWN`. Numerator: canonical status in `{EQUIVALENT, NOT_EQUIVALENT}`. For Z3 and cvc5, status in `{equivalent_within_model, counterexample_found}`. `UNKNOWN`, `TIMEOUT`, `UNSUPPORTED`, `ERROR`, `solver_error`, `counterexample_validation_failed`, and `unknown` are non-decisive. `UNKNOWN` is never counted as equivalence.

Time. Per-case wall-clock seconds around `decide_mode_b`, around `verify_equivalence_timed`, and around the cvc5 process. One Z3 initialization and one cvc5 initialization, excluded from the per-case sums. For each width, report `n`, sum, and median.

Also report the count of canonical `UNKNOWN` rows and, when the detail names a term count, the cap `256`.

## Solvers

Z3 4.8.17 through `verify_equivalence_timed`, timeout 5 seconds. cvc5 1.3.2 through `scripts.run_second_solver`, per-query limit 5000 ms. A solver counterexample counts only after `reference_evaluator.evaluate` confirms it.

## Analysis script

`scripts/run_canonical_wide.py` checks this file's SHA-256 against `research/protocol_canonical_wide.json`, checks that `dataset_generated_before_hash` is false, writes the dataset, then runs the three procedures. It refuses to start if the hash differs. Raw rows: `experiments/reports/canonical-wide-v1/cases.jsonl`. Summary: `experiments/reports/canonical-wide-v1/summary.json`.

## Stopping rule

One run. Do not drop a width-32 `UNKNOWN` row. Do not retune the term cap. Do not rewrite the 57-pair study. A false `EQUIVALENT` on a ground-truth `non_equivalent` row is kept.
