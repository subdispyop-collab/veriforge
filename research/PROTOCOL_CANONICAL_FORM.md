# Protocol: unsigned canonical form on wraparound pairs

- Record id: `veriforge-canonical-form-v1`
- Software version: `1.0.0` (not bumped)
- Parent commit before this file: `68555ba1f657478d48f1db8dbaaf66d2144c5d9a`
- Created at: `2026-10-12T13:25:52Z`
- This file is hashed before any pair in `datasets/canonical_form_v1/` exists.
- The 1968 Keller and Olson paper was not opened. Any attribution to that paper is second-hand through IACR eprint 2022/1364, which was retrieved. This protocol does not call the representation a new theorem.

The earlier NO-GO record remains `research/PREREGISTRATION.md` with SHA-256 `d0b112064b93acb4b19aecd62cac865eedb2f653a1a9aade65ee10d2255869cb`. This file does not edit that record. It authorizes one new dataset for the question below.

## Question

On unsigned wraparound, how often does the falling-factorial canonical-form checker give a certificate-backed decision on pairs where integer coefficient comparison is the wrong semantics, and how do that checker, Z3 4.8.17, and cvc5 1.3.2 compare on the same pairs for false equivalence, decisive rate, and time?

Integer coefficient comparison is the wrong semantics on a pair when `polynomial_oracle.polynomial_compare` returns `counterexample` and the exhaustive Mode B label is `equivalent`. Equal integer polynomials induce equal wraparound functions, so the opposite mismatch is recorded if it appears and is not part of the primary numerator.

## Procedure under test

`veriforge.falling_factorial.decide_mode_b`, checked by `veriforge.canonical_certificate.check_certificate`.

Mode B only. The core step reduces the integer difference in the falling-factorial basis and compares canonical coefficients modulo `2^w`. It does not call Z3, cvc5, Alive2, or `veriforge.polynomial_oracle`. `EQUIVALENT` is allowed only after the certificate checker accepts. `NOT_EQUIVALENT` is allowed only after `reference_evaluator.evaluate` confirms a concrete assignment. `UNKNOWN` is not promoted to `EQUIVALENT`.

Fixed budgets inside that procedure, named here so they are not retuned after the run:

- term budget `256`
- certificate grid budget `4096`
- maximum syntactic degree per variable `12`
- maximum variable count `6`
- timeout `5` seconds, the same budget as the solver calls

## Templates

Widths are `1`, `2`, and `4`, in that order, for every template. The generator emits one row per template per width, in the order below. It aborts if a literal is outside `[0, 2^w - 1]`. It does not drop a row. It does not consult a solver while generating.

`construction_intent` is a note about why the template is in the file. It is not a label and it is not an analysis input.

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
  {"family": "double_sum", "intent": "modular_sensitive", "original": "((a + b) + (a + b))", "candidate": "0"}
]
```

Expected row count: 19 templates times 3 widths = 57. Case ids `cf-0001` through `cf-0057`. Partition `canonical_form_v1`. Semantic mode `mode_b` on every row. Output path `datasets/canonical_form_v1/cases.jsonl`.

`datasets/held_out/cases.jsonl` is not an input and is not rewritten. The run aborts unless that file still has 8 non-empty lines. `datasets/confirmatory_v2/cases.jsonl` and `datasets/assurance_v1/cases.jsonl` are not rewritten.

## Ground truth

Mode B ground truth is `exhaustive_oracle.exhaustive_compare` with assignment budget `65536`. Every domain in this file is at most `2^(4*3) = 4096`, so a `not_computed` exhaustive label is a run failure, not a case to drop quietly. Construction intent is not ground truth.

Integer coefficient comparison, used only to define the wrong-semantics subset, is `polynomial_oracle.polynomial_compare` with term budget `4096`. That call is a baseline. It is not the procedure under test.

## Outcomes

Primary, pair level. Denominator: pairs with polynomial verdict `counterexample` and exhaustive label `equivalent`. Numerator: those pairs whose canonical status is `EQUIVALENT`. Report the numerator, the denominator, and a 95% Wilson interval when the denominator is positive. An empty denominator is null, not a zero rate.

Primary, family level, because three widths of one template are not independent pairs. A family is in the denominator when at least one of its pairs is in the pair-level denominator. It is in the numerator when every such pair has canonical status `EQUIVALENT`. Report both counts.

False equivalence, three procedures, same pairs. Denominator: exhaustive label `non_equivalent`. Numerator: canonical status `EQUIVALENT`, Z3 status `equivalent_within_model`, or cvc5 status `equivalent_within_model`, respectively. Wilson interval on each. Also split the same counts by width.

False rejection. Denominator: exhaustive label `equivalent`. Numerator: canonical `NOT_EQUIVALENT`, Z3 `counterexample_found`, or cvc5 `counterexample_found`.

Decisive rate. Denominator: all 57 pairs. Numerator: canonical status in `{EQUIVALENT, NOT_EQUIVALENT}`. For Z3 and cvc5, numerator: status in `{equivalent_within_model, counterexample_found}`. `UNKNOWN`, `TIMEOUT`, `UNSUPPORTED`, `ERROR`, `solver_error`, `counterexample_validation_failed`, and `unknown` are non-decisive.

Time. Per-case wall-clock seconds around `decide_mode_b`, around `verify_equivalence_timed`, and around the cvc5 process. One initialization sample for Z3 and one for cvc5, recorded separately and excluded from the per-case sums. Report `n`, sum, and median for each per-case series. No superiority test is authorized.

Other mismatches. Count polynomial `equivalent` with exhaustive `non_equivalent`, and polynomial `not_computed`. They do not enter the primary numerator.

## Solvers

Z3 through the installed `z3` module, expected version `4.8.17`, via `verify_equivalence_timed`, timeout 5 seconds. cvc5 expected version line containing `1.3.2`, via the existing SMT-LIB script and `scripts.run_second_solver`, per-query limit 5000 ms. A counterexample from either solver counts only after `reference_evaluator.evaluate` confirms it. The canonical procedure's own witness rule is the same evaluator.

## Analysis script

`scripts/run_canonical_form_study.py` checks this file's SHA-256 against `research/protocol_canonical_form.json`, checks that `dataset_generated_before_hash` is false, writes the dataset, then runs the three procedures. It refuses to start if the hash differs. It does not add a template. It writes raw rows to `experiments/reports/canonical-form-v1/cases.jsonl` and the summary to `experiments/reports/canonical-form-v1/summary.json`.

## Stopping rule

One run of that script. Do not add a family after seeing a count. Do not retune a budget. Do not regenerate the 57 rows to change a denominator. If the canonical procedure returns `EQUIVALENT` on an exhaustive `non_equivalent` pair, that false equivalence is the result; it is not deleted. A code fix after that print requires a new protocol file and a new hash before any replacement dataset exists. Unit tests run before this script are allowed to change code, because they are not this dataset and they do not authorize a change to the templates or the budgets above.
