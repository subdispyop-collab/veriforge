# Limitations

## Current limitations

Phases 1–12 are implemented. Version **`1.0.0`**. §20 Definition of Done is **met** after Phase 5 warm-host clean-venv attestation (`pip install -e ".[dev]"` + **359/0/0**). The Phase 12 authoring host still cannot reach PyPI (egress); that remains an environment limit for fresh VMs, not a procedure defect. Residual research limitations (small held-out n, TCB, baseline 5 not selected, H3 inconclusive) stay disclosed below.

Consequences:

- The Streamlit interface (Phase 8) presents engines honestly: UNKNOWN/timeout are never labeled equivalent; charts require completed-run measurements; missing capabilities show unavailable states. It does not invent research findings.
- Phase 9 documents the threat model and §15 controls in `docs/SECURITY.md`. **VERIFORGE does not claim resistance to every attack.**
- Phase 10 literature review (`docs/LITERATURE_REVIEW.md`) uses real sources and makes **no novelty claim**.
- Phase 11 independent review (`docs/INDEPENDENT_REVIEW.md`) does **not** strengthen C2/P1/H\* beyond sample-limited ledger statuses.
- Phase 12 release checklist / final report: `docs/RELEASE_CHECKLIST.md`, `docs/FINAL_RESEARCH_REPORT.md`.
- Held-out evaluation harness exists (`veriforge/evaluation_engine.py`). Actual Phase 10 held-out numbers are in `experiments/reports/phase10-held-out-evaluation.md` (warm host, seed `20261009`, n=8). On hosts without installable `z3-solver`, measurements remain **unavailable** and must be labeled as such. Do not invent rates or timings. Small-n sample statuses are not population estimates.
- Baselines 1–4 are implemented in the harness; baseline 5 (external tool) remains not selected.
- Metric unit tests and benchmark-engine validation runs may use development/fixture data. Those numbers are not scientific findings unless a held-out report says otherwise with traceable raw observations.
- Timing and solver wall-clock measurements are subject to platform and Z3 nondeterminism; exact bit-for-bit reproduction of durations is not guaranteed.
- The Phase 3 optimizer shipped four identity-preserving production rules. Eight algebra rules were added later, only after production Z3 returned `EQUIVALENT_WITHIN_MODEL` for each template in Mode A and in one legal Mode B width. Width-1 `x * 2` and width-2 `x + 5` stay rejected.
- Artificial mutations exist only in `veriforge.fuzzer_suite` for detection testing. They are not estimates of real-world defect prevalence.
- An artificial 90/10 correct/incorrect mix may appear as a controlled configuration only. It is not real-world prevalence.
- Passing Hypothesis property tests and mutation campaigns is not a mathematical proof of equivalence.
- The held-out seed partition is small (8 cases). Even successful runs are not population estimates; related generated variants must not be treated as independent observations.
- Warm-host suite evidence for release: **359 passed / 0 failed / 0 skipped** at `6848fd4`. Local pytest on egress-blocked hosts remains unavailable.
- Residual TCB risk: correlated encoder/evaluator error can yield false EQUIVALENT_WITHIN_MODEL; see `docs/FORMAL_MODEL.md` and ledger R1/R2.
- Signed interpretation for Mode B is intentionally unused. If later operators need signedness, that is a new decision.
- Division, remainder, bitwise ops, shifts, comparisons, Booleans, and casts remain unsupported and rejected.
- TIMEOUT and UNKNOWN paths for live Z3 searches are classified correctly; unit tests may drive those branches with controlled solver mocks because the initial arithmetic fragment usually decides quickly. The configurable timeout (default 5s) is still applied to every real `check`. The optimizer treats those statuses as rejection, never as acceptance.
- Near-duplicate keys are based on whitespace-normalized sources plus category and semantic model. They do not prove semantic independence of all generated variants for statistical purposes.
- Secret redaction is pattern-based; novel secret formats may slip through (see `docs/SECURITY.md`).
- Path confinement applies to VERIFORGE export/derived APIs; bypassing those APIs is out of scope for the control.
- Dependency reinstall may be blocked by PyPI egress on some agent hosts; pins are reviewed from lock files, not always from a fresh install attestation.
- Rule-based-without-SMT is an **evaluation harness** for baseline comparison. Production `optimize()` remains verification-guided.

## Trusted computing base

Equivalence claims depend on the components listed in `docs/FORMAL_MODEL.md` (extended in Phase 11): CPython/`ast` + VERIFORGE parser, the Mode A / Mode B contract, semantic helpers, the Z3 translator, the pinned `z3-solver` package, the reference evaluator for counterexample confirmation, configured resource limits, and (for accepted rewrites) optimizer acceptance policy. A solver result does not prove those components correct.

## Standing limits from the specification

These limits remain in force after implementation. They are not waived by a working demo, a passing test, or a solver result.

- Do not claim that VERIFORGE invents a new formal verification technique unless a literature review and experimental evidence substantiate that claim. The literature review finds established methods; **no novelty claim** is made.
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
- Do not claim resistance to every attack. The threat model and remaining limitations are in `docs/SECURITY.md` and this file.
- If bit-for-bit reproduction is not guaranteed because of solver, platform, or timing nondeterminism, that limitation has to be documented.
- If a later experiment is not run, its results stay labeled unavailable. If a hypothesis is unsupported, the report says so.
- If online research is unavailable when the literature review is attempted, the limitation and a review plan replace a pretended completed review.
