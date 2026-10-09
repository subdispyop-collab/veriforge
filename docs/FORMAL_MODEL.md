# Formal model

This document records the encoded equivalence query and the trusted computing base (TCB) assumptions for VERIFORGE verification. It does not claim that VERIFORGE invents a new verification technique.

Phase 11 independent review: see `docs/INDEPENDENT_REVIEW.md`. Solver UNSAT is never a proof of the application implementation.

## Encoded query

For an original expression `E_o` and a candidate `E_c` under a fixed `SemanticConfiguration`:

```
exists x in Domain:  [[E_o]](x) ≠ [[E_c]](x)
```

- Domain for Mode A: mathematical integers (Z3 `Int` sort).
- Domain for Mode B: unsigned values in `[0, 2^w - 1]` (Z3 `BitVec` sort of width `w`).
- `[[·]]` is the Z3 translation of the Phase 1 expression IR using the same operators as `docs/SEMANTICS.md`.

Solver reading:

| Z3 outcome | Reported status (after validation where required) |
| --- | --- |
| `unsat` | `EQUIVALENT_WITHIN_MODEL` |
| `sat`, and the reference evaluator confirms differing outputs | `COUNTEREXAMPLE_FOUND` |
| `sat`, but validation fails or is impossible | `VERIFICATION_ERROR` (discrepancy / unvalidatable; not a confirmed counterexample) |
| `unknown` with timeout/cancel reason | `TIMEOUT` |
| `unknown` otherwise | `UNKNOWN` |

A solver result is a statement about the formula submitted to Z3. It is not a proof that the parser, translator, optimizer, or application implementation is correct.

## Trusted computing base

### In-TCB components (equivalence / accepted-rewrite claims)

Correctness claims about equivalence checking and verification-guided acceptance depend on:

1. **CPython** runtime and Python's `ast` module (parse without execute).
2. The VERIFORGE fail-closed parser (`parser_engine`) and its resource limits.
3. The documented Mode A / Mode B contract in `docs/SEMANTICS.md` plus locked Phase 1 decisions.
4. Shared semantic helpers in `semantics.py` (literal/assignment domain checks; Mode B wrap/negate) as used by parser and reference evaluator.
5. The Z3 translation in `verifier_engine` matching that contract (integer sorts for Mode A; bit-vector sorts for Mode B).
6. The Z3 SMT solver (`z3-solver`, pinned in `pyproject.toml` / `requirements.lock`, currently `5.1.0.0`).
7. The reference evaluator used to confirm SAT models before `COUNTEREXAMPLE_FOUND`.
8. Correct configuration of resource limits, including solver timeout (default 5 seconds).
9. For **accepted** production rewrites only: optimizer rule matching, trace recording, and the verification-guided acceptance policy in `optimizer_engine` (accept only `EQUIVALENT_WITHIN_MODEL`).

### Out of TCB for equivalence claims

- Streamlit UI, Plotly, and Pandas presentation layers.
- Dataset authorship quality and near-duplicate key policy (research design, not the encoded query).
- Experiment / evaluation / benchmark orchestration, except insofar as they call the verifier.
- Audit/storage persistence (records outcomes; does not redefine the query).
- The Phase 4 mutation harness (uses verifier results for detection tests; never production acceptance).
- pytest / Hypothesis (test oracles; not production acceptance).
- Operating-system scheduling and wall-clock timer resolution (affects performance claims, not logical UNSAT/SAT classification).

### Residual TCB risks (Phase 11)

- **Correlated mis-encoding:** if the translator systematically makes unequal expressions look equal, Z3 may return UNSAT and there is no SAT model for the reference evaluator to reject. Independent SAT validation does not close this risk.
- **Partial independence of the reference evaluator:** it does not use Z3, but it shares the same written contract and `semantics.py` helpers. It is not a second, separately authored semantics implementation (§6.2 only partially met).
- **Pinned native solver bugs** and CPython/`ast` bugs are outside VERIFORGE's proof obligation.

## Explicit non-claims

- UNSAT does not prove the application is bug-free.
- UNKNOWN and TIMEOUT are not equivalence.
- A confirmed counterexample is only a counterexample under the encoded model and after reference validation.
- Mode A and Mode B results are not interchangeable.
- A passing test suite, warm-host pytest count, or held-out sample result does not prove novelty or universal correctness.
- Held-out `supported_on_this_sample` labels are not population estimates (`docs/EVIDENCE_LEDGER.md`, `docs/INDEPENDENT_REVIEW.md`).
