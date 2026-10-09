# Formal model (Phase 2)

This document records the encoded equivalence query and the trusted computing base (TCB) assumptions for Phase 2 verification. It does not claim that VERIFORGE invents a new verification technique.

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

Correctness claims about Phase 2 equivalence checking depend on:

1. Python's `ast` module and the VERIFORGE fail-closed parser (`parser_engine`).
2. The documented Mode A / Mode B contract in `docs/SEMANTICS.md`.
3. The Z3 translation in `verifier_engine` matching that contract (integer sorts for Mode A; bit-vector sorts for Mode B).
4. The Z3 SMT solver (`z3-solver`, pinned in `pyproject.toml` / `requirements.lock`).
5. The independent reference evaluator used to confirm counterexamples.
6. Correct configuration of resource limits, including solver timeout (default 5 seconds).

Components outside this TCB for Phase 2 equivalence claims: Streamlit UI (not implemented), datasets, experiment framework, persistence, the Phase 6 benchmark engine (timing/orchestration only — it calls the verifier but is not part of the equivalence TCB), and the Phase 7 audit/storage layer (records and exports verification outcomes; it does not redefine the encoded query). The Phase 4 mutation harness *uses* Phase 2 results for detection tests; it is not part of the production acceptance TCB and never accepts candidates into the optimizer.

The Phase 3 optimizer *uses* Phase 2 results as an acceptance gate. An accepted rewrite therefore depends on the Phase 2 TCB plus correct rule matching, trace recording, and the verification-guided acceptance policy in `optimizer_engine`. A solver UNSAT still does not prove the optimizer implementation correct.

## Explicit non-claims

- UNSAT does not prove the application is bug-free.
- UNKNOWN and TIMEOUT are not equivalence.
- A confirmed counterexample is only a counterexample under the encoded model and after reference validation.
- Mode A and Mode B results are not interchangeable.
