# Part 15 audit

Software version remains `1.0.0`. Branch `cursor/research-hardening-7f34`. Historical `datasets/held_out/cases.jsonl` still has 8 lines. No IRIS score and no judge score are claimed.

The conclusion this evidence supports is a technically correct implementation of a small arithmetic checker, plus a negative testing result and a three-solver status census. It is not a demonstrated new method.

## Prioritized issues

| Issue | Evidence in the repository | Scientific consequence | Change made | Validation | Unresolved risk |
| --- | --- | --- | --- | --- | --- |
| H1 “4/4” double-counts | `docs/INDEPENDENT_REVIEW.md` S5; `experiments/reports/phase10-held-out-evaluation.md` | Two unique non-equivalent held-out cases, each run under two SMT baselines, on software 0.10.0 | No count was rewritten in the historical report. This audit states the unique count. | Review text already says 2 unique cases × 2 baselines. | n=8 is exploratory for 1.0.0. It is not fresh confirmatory evidence. |
| Second solver missing from the written claims | `experiments/reports/assurance-v1-smt/second_solver.json` | CVC5 matches Z3. Bitwuzla matches only on unsigned pairs. | Reports updated to those counts. | 926 rows, 0 unconfirmed counterexamples, wall 2.9129006489993117 s. | Shared translation can still fool both Z3 and CVC5. |
| False equivalence hidden inside accuracy | `experiments/reports/assurance-v1-smt/part15_confusion.json` | 0/96 non-equivalent pairs were called equivalent by Z3, CVC5, or Bitwuzla | Matrix written from the saved rows and the existing oracle file. | Wilson upper bound on 0/96 is 0.038475587857675686. | The oracle is this project’s polynomial or exhaustive label, not an outside proof. |
| Alive2 treated as a peer benchmark | Fetched PLDI 2021 paper and Alive2 README | Different language. No fair comparison. | Case study says so and does not report an Alive2 score. | Two grammar skeletons ran and were equivalent. | A fair external IR checker was not built. |
| IRIS rules were asserted without a page | `research/IRIS_GUIDELINES_FETCHED.md` | Only retrieved sentences are usable. | Excerpts saved. Abstract counted at 250 words. | Word count script. | The full HTML page was not stored. Direct fetch was rejected. |
| H3 solver-time claim | `veriforge/assurance_experiment.py` `run_scaling` sets `solver_time` to unavailable | Historical H3 stays inconclusive / unresolved | No new solver-time test was analyzed after seeing the census. | Census has 0 timeout and 0 unknown, which was already visible before any H3 rule could be locked. | A preregistered solver-time study on new expressions is still required. |
| pytest pin | `experiments/reports/assurance-v1-smt/pytest_911.json` | The suite passed on the Debian 9.1.1 package. | None of the tests were weakened for this run. | JUnit: 383 tests, 0 failures, 0 errors, 0 skipped, exit 0. | Hypothesis was 6.155.7, not lock pin 6.168.5. Z3 was 4.8.17, not `z3-solver==5.1.0.0`. |

## Commands and outcomes

```text
python3 scripts/run_second_solver.py
```

Exit succeeded. CVC5 version line `This is cvc5 version 1.3.2`. Bitwuzla version line `0.8.2`. CVC5 counts: equivalent_within_model 318, counterexample_found 96, invalid_input 8, unsupported 41. Bitwuzla counts: 246, 62, 8, 41, and solver_error 106. Mode B matches across Z3 4.8.17, CVC5, and Bitwuzla: 246, 62, 6, 17.

```text
python3 -m pytest --junitxml=/tmp/pytest-911.xml -q --tb=line
```

pytest 9.1.1, Python 3.12.3, exit 0. 383 tests, 0 failures, 0 errors, 0 skipped.

Case-study calls to `verify_equivalence_timed` on the two skeletons returned `equivalent_within_model` in Mode A and in Mode B at width 8.

## Corrected metrics

H1 on the historical n=8 file, software 0.10.0: 2 unique non-equivalent cases. The published 4/4 is those two cases under `baseline.verification_enabled` and `baseline.testing_only_validation`. It is not four bugs. Classes in that file are one `incorrect_rewrite` and one `artificial_mutation`.

Assurance dataset 1.1.0: 463 unique pairs, 27 families. Oracle labels: equivalent 316, non_equivalent 96, unsupported 36, invalid_input 13, not_computed 2. The 96 non-equivalent pairs sit in 8 families: boundary_values, const_off_by_one, drop_term, modular_collapse, mul_to_add, op_swap, swap_sub, wrong_factor. Family is the independent unit, not the pair and not a repeated timing.

For Z3 and for CVC5, on those 96 pairs: false equivalence 0, correct rejection 96, false rejection of the 316 equivalent pairs 0, correct acceptance 316. Decisive answers 414/463. The other 49 are invalid_input or unsupported, not successes. Bitwuzla: false equivalence 0/96, correct rejection 62, solver_error on 34 non-equivalent Mode A pairs and 72 equivalent Mode A pairs. Decisive 308/463.

Wilson 95% upper bound on 0/96 false equivalences: 0.038475587857675686. The interval helper’s lower endpoint was a floating-point residue near 0; the numerator is 0. Mode A upper bound on 0/34 is 0.10151455415332376. Mode B upper bound on 0/62 is 0.058344072101372484.

Counterexample detection on the 96 non-equivalent pairs is 96/96 for Z3 and CVC5, and 62/96 for Bitwuzla. False-equivalence acceptance is the safety count, and it is 0/96 for each. Those are different rates. Unknown, timeout, unsupported, invalid_input, and solver_error are not counted as verification.

Two pairs, `av1-0252` and `av1-0258`, are oracle `not_computed` because width 8 with three variables exceeds the 65,536 assignment budget. Z3 and CVC5 called both `equivalent_within_model`. They are not in the 0/96 denominator.

H_test remains not supported: 0/54 and 0/54 at budgets 10 and 10,000 on the assurance held-out non-equivalent pairs. H3 remains inconclusive on n=8 and unresolved for solver time.

## Results to downgrade or label exploratory

- Historical H1 `supported_on_this_sample` applies to software 0.10.0 and two unique cases. It is exploratory for version 1.0.0. Do not quote 4/4 as four independent detections.
- Pipeline-versus-oracle 64/64 and 54/54 in `summary.json` stays a contract check. The oracle and the pipeline share the polynomial and exhaustive procedures.
- Solver agreement with that oracle is corroboration on this set, not a proof of the translator. Z3 and CVC5 were given the same parsed semantics.
- The eight production algebra rules were admitted from templates checked in the Z3 census, after the amendment hash. They are not evidence from the n=8 file.
- Evaluator scaling Spearman is execution time only. It does not settle H3.
- No compiler bug was discovered here.

## Not completed

- A new confirmatory pair set, preregistered before generation, for version 1.0.0. The n=8 file influenced the historical H1 wording and must not be reused as untouched confirmation. This session did not open a third dataset after the solvers had already agreed, because that design would have been written with the result in view.
- Solver-time H3. It was not locked before the census timings existed.
- mutmut. The Debian sid package index that was downloaded contains no mutmut package.
- Docker and the CI workflow. `docker` and `podman` are not installed, so the Dockerfile was not executed.
- Alive2 as a baseline. Not installed, and not a fair comparison if it were.
- Z3 UNSAT proof objects and an external proof checker.
- Signed Mode B as a production mode. It remains the experimental module.
- Hypothesis lock pin 6.168.5 and the `z3-solver==5.1.0.0` wheel. The green suite used Debian pytest 9.1.1, Debian Hypothesis 6.155.7, and system Z3 4.8.17.
- Full IRIS HTML. The allowlisted fetch rejected the guideline host. Only the retrieved excerpts are on file.
- Component-ablation wall-clock table beyond the solver census already saved.

## Hypothesis verdict

| Hypothesis | Verdict |
| --- | --- |
| H1, n=8, software 0.10.0 | supported_on_this_sample, 2 unique cases, not four |
| H1 as a general or 1.0.0 claim | exploratory; not established |
| H_test, larger budget catches more held-out bugs | not supported, 0/54 at both budgets |
| H_audit, a second encoder catches production misses | inconclusive; the census was not that comparison |
| H3, overhead and success vary by complexity and category | unresolved for solver time; inconclusive on n=8 |
| Novel method | not supported |
| Engineering implementation of the dual-mode checker | the tests and the solver census are consistent with it |

## Contribution

Closest published methods, from `docs/LITERATURE_REVIEW.md` and the fetched Alive2 paper: Pnueli, Siegel, and Singerman on translation validation; Necula on translation validation for an optimizing compiler; de Moura and Bjørner on Z3; Lopes, Menendez, Nagarakatte, and Regehr on Alive; Lopes, Lee, Hur, Liu, and Regehr on Alive2.

VERIFORGE checks one expression pair at a time in a `+` `-` `*` grammar, with an explicit integer mode and an unsigned wrap mode. Alive and Alive2 check LLVM peephole or IR refinement, including poison and flags. Necula’s validator checks compiler IR. Z3 and CVC5 are solvers, not rewrite checkers. The difference is the restricted language and the two modes. The experiment that speaks to it is the 463-pair census, not a comparison of bug-finding rates against Alive2.

Alive2 is not a fair accuracy or speed baseline. The input language and the semantics do not match. No such comparison is claimed.

The supported outcome is item 3 in the part 15 list: a technically correct implementation without a demonstrated novel contribution. The useful empirical results are the negative testing result and the solver status counts.
