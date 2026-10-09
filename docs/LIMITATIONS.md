# Limitations

## Current limitations

Phases 1–7 (semantic foundation through audit/storage) are implemented. Phases 8–12 are not started.

Consequences:

- There is no Streamlit interface (Phase 8). Phase 7 adds audit export/replay, §13 optimization-run records, integrity checks, and raw vs derived separation on top of the Phase 5 SQLite + filesystem store.
- Held-out evaluation has **not** been run as a research conclusion. Dataset partitions exist; research results are unavailable. Phase 6 may use the development partition only for engine validation.
- Baselines are defined, not measured. No external comparison tool is selected.
- Metric unit tests and benchmark-engine validation runs use development/fixture data. Those numbers are not scientific findings.
- Timing and solver wall-clock measurements are subject to platform and Z3 nondeterminism; exact bit-for-bit reproduction of durations is not guaranteed (disclosed on every `BenchmarkConfiguration` / `BenchmarkReport`).
- The Phase 3 optimizer ships only four identity-preserving production rules. Aggressive rewrites are intentionally absent.
- Artificial mutations exist only in `veriforge.fuzzer_suite` for detection testing. They are not estimates of real-world defect prevalence.
- An artificial 90/10 correct/incorrect mix may appear as a controlled configuration only. It is not real-world prevalence.
- Passing Hypothesis property tests and mutation campaigns is not a mathematical proof of equivalence.
- No literature review has been done. No citation is recorded.
- The evidence ledger required by section 17 does not exist. No research claim has an evidence status beyond Phase 1–5 implementation and test evidence.
- Definition of done (section 20) is not met. That is expected before release. The project is not complete.
- Signed interpretation for Mode B is intentionally unused. If later operators need signedness, that is a new decision.
- Division, remainder, bitwise ops, shifts, comparisons, Booleans, and casts remain unsupported and rejected.
- TIMEOUT and UNKNOWN paths for live Z3 searches are classified correctly; unit tests drive those branches with controlled solver mocks because the initial arithmetic fragment usually decides quickly. The configurable timeout (default 5s) is still applied to every real `check`. The optimizer treats those statuses as rejection, never as acceptance.
- Near-duplicate keys are based on whitespace-normalized sources plus category and semantic model. They do not prove semantic independence of all generated variants for statistical purposes.

## Trusted computing base (Phase 2)

Equivalence claims depend on the components listed in `docs/FORMAL_MODEL.md`: Python `ast` + VERIFORGE parser, the Mode A / Mode B contract, the Z3 translator, the pinned `z3-solver` package, the reference evaluator for counterexample confirmation, and configured resource limits. A solver result does not prove those components correct.

## Standing limits from the specification

These limits remain in force after implementation. They are not waived by a working demo, a passing test, or a solver result.

- Do not claim that VERIFORGE invents a new formal verification technique unless a literature review and experimental evidence substantiate that claim. Neither exists. No novelty claim is made.
- A solver result is a statement about the formula supplied to the solver. It does not, by itself, establish that the parser, semantic translator, optimizer, or application is correct.
- UNSAT means equivalent within the encoded model and assumptions. It does not mean equivalent in an unspecified language, and it does not mean the implementation was proved correct.
- UNKNOWN, timeout, and interruption are not equivalence.
- A counterexample that the reference evaluator cannot validate is not a confirmed counterexample.
- Passing randomized tests is not a mathematical proof of equivalence.
- Coverage is diagnostic evidence, not proof of correctness.
- A passing unit test does not establish scientific novelty. A benchmark result does not establish universal correctness. A formal proof does not establish that the application encoded the intended semantics.
- Do not fabricate demonstration results, benchmark values, users, citations, or experimental achievements. Scientific charts may show only measurements from completed runs.
- Do not claim an execution speedup because an expression is shorter, the AST is smaller, the solver is faster, or the interface looks efficient. Solver time and expression execution time are different.
- An artificial mix of correct and incorrect candidates, including a 90/10 mix, is not an estimate of real-world error prevalence.
- Generated expressions that are variants of one transformation are not independent research observations.
- The optimizer must not execute arbitrary user-supplied Python. `eval` and `exec` on user input are forbidden.
- Unsupported syntax fails closed. It is not silently rewritten.
- Mathematical integers and fixed-width bit-vectors are never silently conflated.
- The benchmark must not be tuned against the held-out evaluation set.
- Do not claim resistance to every attack. The threat model and the remaining limitations have to be written when security work is done. They are not written as a completed review here.
- If bit-for-bit reproduction is not guaranteed because of solver, platform, or timing nondeterminism, that limitation has to be documented. Phase 6 discloses timing nondeterminism on every benchmark configuration/report. Phase 7 replay restores the recorded semantic configuration and rule fingerprint; wall-clock timings and near-timeout UNKNOWN/TIMEOUT outcomes may still differ and are not claimed bit-identical.
- If a later experiment is not run, its results stay labeled unavailable. If a hypothesis is unsupported, the report says so.
- If online research is unavailable when the literature review is attempted, the limitation and a review plan replace a pretended completed review.
