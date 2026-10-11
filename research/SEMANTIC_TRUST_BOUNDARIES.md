# Semantic trust boundaries

## Path

1. Input length and resource limits (`SemanticConfiguration`).
2. Production parse (`parser_engine`, Python `ast`) or independent parse (`independent_parser`, recursive descent).
3. Production IR (`models.Expr`) or independent IR (`ILit`, `IVar`, `IUnary`, `IBinary`).
4. Production Z3 translation (`translate_to_z3`) when `z3` imports. Otherwise `verify_equivalence` returns `VERIFICATION_ERROR` with reason `z3-solver is not installed`.
5. Independent Z3 encoder (`independent_encoder`) when `z3` imports. Otherwise verdict `unavailable`.
6. Polynomial expansion for Mode A (`polynomial_oracle`).
7. Exhaustive enumeration for Mode B when `2^(w*k)` is at most the budget (`exhaustive_oracle`).
8. Concrete evaluation (`reference_evaluator` or `independent_evaluator`).
9. `combine_gates` chooses one `VerificationStatus`.
10. The assurance experiment writes JSON and CSV under `experiments/reports/assurance-v1/`. The Streamlit UI was not re-executed on this host.

## What can go wrong

| Failure | Status that must not be equivalence |
| --- | --- |
| Bad syntax | `UNSUPPORTED` or `INVALID_INPUT` |
| Solver missing | `unavailable` gate, ignored by the contract; top-level status comes from another completed check or `UNKNOWN` |
| Solver timeout | `TIMEOUT` |
| Solver UNKNOWN | `UNKNOWN` |
| One check says equivalent and another says counterexample | `SEMANTIC_DISAGREEMENT` |
| SAT model not confirmed | `COUNTEREXAMPLE_VALIDATION_FAILED` on the production path |
| Domain larger than the budget | `not_computed`, then `UNKNOWN` if nothing else finished |

`audit_equivalence` maps a production `VERIFICATION_ERROR` whose reason says the solver is not installed to gate verdict `unavailable`. A missing solver does not veto a completed polynomial or exhaustive proof, and it is not itself a proof.

## Shared pieces

- Both parsers aim at the same grammar and the same literal rules. A shared mistake in the written contract can survive both.
- Both evaluators use Python integers. Mode B wrap is `value % 2**w` in the independent evaluator and `value % modulus` in `semantics.wrap_unsigned`. Those are separate functions. They can still share a wrong idea of Python's remainder.
- The polynomial check and the concrete evaluator are different algorithms. A witness is re-evaluated concretely.
- Two Z3 encoders would still share Z3. That arm did not run.
- The scored "audited pipeline" in `summary.json` establishes Mode A equivalence with the polynomial oracle and Mode B equivalence with the exhaustive oracle. Comparing that pipeline to those oracles is circular. The file says so.

## Parser boundary

The independent parser does not call `ast`. On the 463-case benchmark, accept/reject agreed with the production parser (0 splits in the pre-hash differential sweep). Non-ASCII names are rejected by the independent parser and are outside the benchmark. Node-count limits are not the same count as `ast.walk`, so a huge expression could pass one limiter and fail the other. Benchmark cases are small.
