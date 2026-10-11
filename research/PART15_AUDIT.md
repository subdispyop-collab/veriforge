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
| H3 solver-time claim | `research/PROTOCOL_CONFIRMATORY_V2.md` and `experiments/reports/confirmatory-v2/summary.json` | The new preregistered pass leaves H3 unresolved | The rule was hashed before the new pairs existed. Spearman on 12 family medians has a bootstrap interval that contains 0, and the uniform equivalent class has 1 family. | rho `0.0036324031737947717`, interval `-0.5543202549518428` to `0.5625128124822065`, seed `20261012`, 2000 resamples. | Init time and CVC5 process time were recorded and do not decide H3. Families were not added after the result. |
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

## Confirmatory v2

Protocol `veriforge-confirmatory-v2`, SHA-256 `1d991b3c444f3a93b531196b4da4a9794937d697212b4e45d285cf8f0f6c498b`, recorded at `2026-10-11T18:59:22Z` in `research/protocol_confirmatory_v2.json`. `dataset_generated_before_hash` is false. `datasets/held_out/cases.jsonl` stayed at 8 lines. The 0/96 census was not used to pick families or a pass threshold. There is no numeric pass threshold.

```text
env -u PYTHONPATH PYTHONPATH=/home/ubuntu/py-z3:/workspace Z3_LIBRARY_PATH=/home/ubuntu/al-root/usr/lib64 LD_LIBRARY_PATH=/home/ubuntu/al-root/usr/lib64 python3 scripts/run_confirmatory_v2.py
```

Exit 0. Python 3.12.3. Z3 4.8.17. CVC5 version line `This is cvc5 version 1.3.2`. 12 families, 72 pairs. Oracle labels: equivalent 32, non_equivalent 33, not_computed 7. Artifact: `experiments/reports/confirmatory-v2/summary.json`.

False equivalence is an oracle `non_equivalent` pair called `equivalent_within_model`. Z3 and CVC5 match.

| Scope | False equivalence | Wilson 95% |
| --- | --- | --- |
| All pairs | 0/33 pairs, 0/6 families | 0.0 to 0.10426999754245206 |
| Mode A | 0/12 pairs, 0/6 families | 2.7755575615628914e-17 to 0.24249400665524085 |
| Mode B | 0/21 pairs, 0/6 families | 0.0 to 0.154639018924847 |

The Mode A lower endpoint is floating-point residue from `wilson_interval` on a zero numerator. The numerator is 0. Family denominators are 6, so `insufficient_sample` is false for this rate. Secondary counts on the labeled pairs, for Z3, CVC5, the encoder, and the full pipeline: correct acceptance 32/32, false rejection 0/32, correct rejection 33/33. The 7 `not_computed` pairs are excluded from those denominators. Six of them were `equivalent_within_model` (`cv2-0006`, `cv2-0012`, `cv2-0015`, `cv2-0018`, `cv2-0024`, `cv2-0033`). One, `cv2-0054` (`sub_swap`, Mode B width 8), was `counterexample_found`. They are not false equivalences under the locked denominator.

Init time, one observation each, not used as per-case samples: Z3 empty `Solver()` `0.0069491530002778745` seconds; CVC5 `--version` `0.01112446600018302` seconds. H3 uses Z3 `solver_seconds` reduced to family medians. CVC5 per-case figures in `cases.jsonl` are process wall times, including startup, and were not a second correlation after rho was known.

H3 verdict: `unresolved`. Complexity arm: `unresolved`, because rho is about 0.0036 and the bootstrap interval contains 0. Category arm: the uniform equivalent class is only `cancel_add` (1 family) and is insufficient. The uniform non-equivalent class has 4 families (`add_const`, `const_gap`, `drop_factor`, `mul_self`). Seven families are mixed because a width-8 pair is `not_computed` or, for `wrap_alias`, because Mode A and width 8 differ from width 4. Classes were not merged. Success rates do not vary: timeout or unknown is 0/6 in the equivalent class’s decisive rows and 0/24 in the non-equivalent class. The locked rule stays `unresolved` when the complexity arm is unresolved or a required class has fewer than 4 families.

Ablation on the same 72 pairs. False equivalence stayed 0/33 in every arm.

| Arm | Wall seconds | False equivalence |
| --- | --- | --- |
| verifier (`verify_equivalence_timed`) | 0.4641656299972965 | 0/33 |
| verifier plus concrete all-zero check | 0.46935624000252574 | 0/33 |
| independent encoder (`encode_difference` only) | 0.4516596080038653 | 0/33 |
| full pipeline (`audit_equivalence`, `run_smt=True`) | 2.552952216999074 | 0/33 |

Concrete checking did not reduce false equivalence and took more wall time. The full pipeline did not reduce false equivalence and took more wall time. The independent encoder also left the count at 0/33. Its wall time is lower because that arm does not include the verifier. It did not catch an additional false equivalence on this set.

Z3 UNSAT proofs, `experiments/reports/confirmatory-v2/z3_unsat_proofs.json`. `z3.set_param('proof', True)` before `Solver()`, then `solver.proof()` after `unsat`. Z3 4.8.17. Production translations: `cv2-0001` Mode A `(a + b)` vs `(b + a)` (346 characters), `cv2-0021` Mode B width 8 `(a - b)` vs `(a + (-b))` (775 characters), `cv2-0029` Mode B width 4 `((a + 3) - 3)` vs `a` (1382 characters). A direct `x + 0 != x` proof (447 characters) is in the same file and is not a dataset pair. No external proof checker ran.

The third proof length in the generator print was 1382 characters for `cv2-0029`. The sentence above must not invent a second 775. I will fix this in the file after I confirm the JSON.

Dockerfile. Podman was not installed from Ubuntu (`archive.ubuntu.com`, the EC2 mirror, and `security.ubuntu.com` returned HTTP 403). Bookworm debs from `https://dpvctowv9b08b.cloudfront.net/debian/` provided podman 4.3.1, crun 1.8.1, conmon 2.1.6, fuse-overlayfs 1.10, and setuid `newuidmap`. Rootless podman started. `public.ecr.aws/docker/library/python:3.12-slim` (`df18428df8a0`) was tagged `docker.io/library/python:3.12-slim` so `FROM python:3.12-slim` resolved without Docker Hub. The Dockerfile text was not changed.

```text
podman build --network=host -t veriforge:1.0.0 -f Dockerfile .
```

Exit 1. pip could not read `https://pypi.org/simple/setuptools/` (`SSL: UNEXPECTED_EOF_WHILE_READING`) and reported `No matching distribution found for setuptools>=68`. Log: `experiments/reports/confirmatory-v2/dockerfile_build.log`. The image was not produced. CI on GitHub Actions was not run.

mutmut did not install. Bookworm, sid, stable, testing, trixie, and unstable package indexes contain zero `mutmut` package names. GitHub, GitLab, Bitbucket, Codeberg, jsDelivr, and snapshot.debian.org failed with `SSL_ERROR_SYSCALL`. It was not run on the parser, verifier, or acceptance gate.

`z3-solver==5.1.0.0` and `hypothesis==6.168.5` were not fetched. `https://pypi.org/pypi/z3-solver/5.1.0.0/json` and `https://files.pythonhosted.org/packages/source/h/hypothesis/hypothesis-6.168.5.tar.gz` failed with `SSL_ERROR_SYSCALL`. HTTP to files.pythonhosted.org returned 403. Debian `python3-z3` is 4.8.12 or 4.13.3, not the pip pin. Debian `python3-hypothesis` tops out at 6.155.7 in sid. pytest was not rerun against those pins. The recorded suite remains pytest 9.1.1, Hypothesis 6.155.7, Z3 4.8.17, JUnit 383 tests, 0 failures, 0 errors, 0 skipped. Details: `experiments/reports/confirmatory-v2/install_attempts.json`.

No Alive2 score was produced. No full IRIS page was produced.

## Corrected metrics

H1 on the historical n=8 file, software 0.10.0: 2 unique non-equivalent cases. The published 4/4 is those two cases under `baseline.verification_enabled` and `baseline.testing_only_validation`. It is not four bugs. Classes in that file are one `incorrect_rewrite` and one `artificial_mutation`.

Assurance dataset 1.1.0: 463 unique pairs, 27 families. Oracle labels: equivalent 316, non_equivalent 96, unsupported 36, invalid_input 13, not_computed 2. The 96 non-equivalent pairs sit in 8 families: boundary_values, const_off_by_one, drop_term, modular_collapse, mul_to_add, op_swap, swap_sub, wrong_factor. Family is the independent unit, not the pair and not a repeated timing.

For Z3 and for CVC5, on those 96 pairs: false equivalence 0, correct rejection 96, false rejection of the 316 equivalent pairs 0, correct acceptance 316. Decisive answers 414/463. The other 49 are invalid_input or unsupported, not successes. Bitwuzla: false equivalence 0/96, correct rejection 62, solver_error on 34 non-equivalent Mode A pairs and 72 equivalent Mode A pairs. Decisive 308/463.

Wilson 95% upper bound on 0/96 false equivalences: 0.038475587857675686. The interval helper’s lower endpoint was a floating-point residue near 0; the numerator is 0. Mode A upper bound on 0/34 is 0.10151455415332376. Mode B upper bound on 0/62 is 0.058344072101372484.

Counterexample detection on the 96 non-equivalent pairs is 96/96 for Z3 and CVC5, and 62/96 for Bitwuzla. False-equivalence acceptance is the safety count, and it is 0/96 for each. Those are different rates. Unknown, timeout, unsupported, invalid_input, and solver_error are not counted as verification.

Two pairs, `av1-0252` and `av1-0258`, are oracle `not_computed` because width 8 with three variables exceeds the 65,536 assignment budget. Z3 and CVC5 called both `equivalent_within_model`. They are not in the 0/96 denominator.

H_test remains not supported: 0/54 and 0/54 at budgets 10 and 10,000 on the assurance held-out non-equivalent pairs. Historical H3 on n=8 stays inconclusive. The new preregistered solver-time pass is unresolved.

## Results to downgrade or label exploratory

- Historical H1 `supported_on_this_sample` applies to software 0.10.0 and two unique cases. It is exploratory for version 1.0.0. Do not quote 4/4 as four independent detections.
- Pipeline-versus-oracle 64/64 and 54/54 in `summary.json` stays a contract check. The oracle and the pipeline share the polynomial and exhaustive procedures.
- Solver agreement with that oracle is corroboration on this set, not a proof of the translator. Z3 and CVC5 were given the same parsed semantics.
- The eight production algebra rules were admitted from templates checked in the Z3 census, after the amendment hash. They are not evidence from the n=8 file.
- Evaluator scaling Spearman is execution time only. It does not settle H3.
- No compiler bug was discovered here.

## Not completed

- mutmut. Debian indexes have no package, and GitHub, GitLab, Bitbucket, Codeberg, jsDelivr, and snapshot.debian.org failed with `SSL_ERROR_SYSCALL`. It did not run on the parser, verifier, or acceptance gate.
- The pinned `z3-solver==5.1.0.0` wheel and `hypothesis==6.168.5` source. PyPI HTTPS failed with `SSL_ERROR_SYSCALL`. HTTP to files.pythonhosted.org returned 403. pytest was not rerun against those pins.
- A finished container image. Podman 4.3.1 executed the Dockerfile once. The build exited 1 because pip could not fetch setuptools from PyPI. GitHub Actions was not run.
- An external checker for the Z3 proof objects. The proof strings were produced. Nothing checked them.
- Alive2 as a baseline. Not installed, and not a fair comparison if it were. No Alive2 score.
- Signed Mode B as a production mode. It remains the experimental module.
- Full IRIS HTML. The allowlisted fetch rejected the guideline host. Only the retrieved excerpts are on file. No IRIS score.

## Hypothesis verdict

| Hypothesis | Verdict |
| --- | --- |
| H1, n=8, software 0.10.0 | supported_on_this_sample, 2 unique cases, not four |
| H1 as a general or 1.0.0 claim | exploratory; not established |
| H_test, larger budget catches more held-out bugs | not supported, 0/54 at both budgets |
| H_audit, a second encoder catches production misses | inconclusive; the census was not that comparison |
| H3, overhead and success vary by complexity and category | unresolved on the confirmatory-v2 rule; inconclusive on n=8 |
| Novel method | not supported |
| Engineering implementation of the dual-mode checker | the tests and the solver census are consistent with it |

## Contribution

Closest published methods, from `docs/LITERATURE_REVIEW.md` and the fetched Alive2 paper: Pnueli, Siegel, and Singerman on translation validation; Necula on translation validation for an optimizing compiler; de Moura and Bjørner on Z3; Lopes, Menendez, Nagarakatte, and Regehr on Alive; Lopes, Lee, Hur, Liu, and Regehr on Alive2.

VERIFORGE checks one expression pair at a time in a `+` `-` `*` grammar, with an explicit integer mode and an unsigned wrap mode. Alive and Alive2 check LLVM peephole or IR refinement, including poison and flags. Necula’s validator checks compiler IR. Z3 and CVC5 are solvers, not rewrite checkers. The difference is the restricted language and the two modes. The experiment that speaks to it is the 463-pair census, not a comparison of bug-finding rates against Alive2.

Alive2 is not a fair accuracy or speed baseline. The input language and the semantics do not match. No such comparison is claimed.

The supported outcome is item 3 in the part 15 list: a technically correct implementation without a demonstrated novel contribution. The useful empirical results are the negative testing result and the solver status counts.
