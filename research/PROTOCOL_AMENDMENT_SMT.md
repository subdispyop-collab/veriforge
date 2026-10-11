# Amendment: production Z3 census on dataset 1.1.0

This amendment does not replace `research/EXPERIMENT_PROTOCOL.md` and does not change its hash. It was written before any production-SMT status from dataset `1.1.0` was inspected.

## What will be run

- Dataset file: `datasets/assurance_v1/cases.jsonl` (the existing 463-pair set). The historical `datasets/held_out/` file is not an input and is not rewritten.
- Solver: the `z3` module that `import z3` resolves in this process. Version is recorded from `z3.get_version_string()` at run time.
- Function: `veriforge.verifier_engine.verify_equivalence_timed`. This is the production translator and solver. The polynomial oracle, the exhaustive oracle, and `audit_equivalence` are not called.
- Each pair is checked in its recorded `semantic_mode` and, for Mode B, its recorded `bit_width`.
- `solver_timeout_seconds` is 5.
- A status of `COUNTEREXAMPLE_FOUND` is counted only when `counterexample.validation_status` is `confirmed`. That confirmation is the production reference evaluator. Any other validation status is counted under its verifier status and is not counted as `COUNTEREXAMPLE_FOUND`.

## What will be reported

Status counts for the whole file, split by recorded mode and by partition. Numerators and denominators. No comparison of these statuses to the polynomial or exhaustive labels is an SMT result, and this run does not compute that comparison.

## Rule gate

The eight templates below are admission candidates. A template enters `default_rules()` only if this run returns `EQUIVALENT_WITHIN_MODEL` in Mode A and in the listed Mode B width. Otherwise it stays out. The two bad-candidate rows are not admission candidates.

| id | Mode A pair | Mode B width | Mode B pair |
| --- | --- | --- | --- |
| distributivity | `(x * (y + z))` vs `((x * y) + (x * z))` | 4 | same |
| factoring | `((x * y) + (x * z))` vs `(x * (y + z))` | 4 | same |
| const_fold | `(2 + 3)` vs `5` | 4 | same |
| sub_self | `(x - x)` vs `0` | 4 | same |
| add_self | `(x + x)` vs `(x * 2)` | 8 | same |
| double_neg | `(-(-x))` vs `x` | 4 | same |
| neg_sub | `(-(x - y))` vs `(y - x)` | 4 | same |
| const_reassoc | `((x + 2) + 3)` vs `(x + 5)` | 8 | same |

Bad candidates, recorded and not admitted: `add_self` at width 1, `(x + x)` vs `(x * 2)`; `const_reassoc` at width 2, `((x + 2) + 3)` vs `(x + 5)`.
