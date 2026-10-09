# Limitations

## Current limitations

VERIFORGE is not implemented. The repository audit on 2026-10-09 found an empty git tree. Phase 0 added this documentation only.

Consequences:

- There is no supported language in running code, no evaluator, no optimizer, no Z3 translation, no benchmark, no dataset, and no user interface.
- The program cannot be installed or run, because there is no application and no dependency manifest.
- No test has been executed. Quality claims cannot be made.
- No experiment has been run. Every measurement listed in the research plan is unavailable.
- No literature review has been done. No citation is recorded.
- The evidence ledger required by section 17 does not exist. No claim has an evidence status.
- Documentation in this phase states the specified contract and the audit. It does not state observed tool behavior.
- Mode B signed interpretation, integer-literal conversion into a fixed width, the set of integer-literal spellings, and the numeric resource limits are not decided. Until they are, those parts of the contract are incomplete on purpose.
- The trusted computing base is not defined, because no component exists.
- Definition of done (section 20) is not met. That is expected at Phase 0. The project is not complete.

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
- If bit-for-bit reproduction is not guaranteed because of solver, platform, or timing nondeterminism, that limitation has to be documented. It is already expected as a possibility. It has not been measured.
- If a later experiment is not run, its results stay labeled unavailable. If a hypothesis is unsupported, the report says so.
- If online research is unavailable when the literature review is attempted, the limitation and a review plan replace a pretended completed review.
