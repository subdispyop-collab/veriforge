# Final research report

Version under discussion: VERIFORGE `1.0.0`. This report does not raise the version.

## 1. Question and motivation

Can a second, non-Z3 reading of a small arithmetic language catch semantic mistakes that a single translator would miss, and what does that cost? The production tool already checks four identities with Z3. The open risk was a shared encoding bug, a small held-out set, and an unresolved complexity hypothesis.

## 2. Prior work

Translation validation, Z3, Alive, and Alive2 already do SMT equivalence checking of rewrites. Property-based testing and mutation testing are older than this project. Sources and the failed 2026 refresh are in `research/LITERATURE_REVIEW.md`. No novelty claim follows from a blocked search.

## 3. Contribution

An auditable engineering layer: independent parser and evaluator, polynomial identity for integers, exhaustive unsigned checks inside a budget, a frozen 463-pair dataset, and preregistered decisions. It is not a new verifier for general programs. Eight further algebraic rules entered `default_rules()` only after the production Z3 census below returned `EQUIVALENT_WITHIN_MODEL` in both modes.

## 4. Semantics and scope

Mode A: mathematical integers. Mode B: unsigned values in `[0, 2^w - 1]`, wrap on `+`, `-`, and `*`, literals outside the range rejected. Grammar: literals, variables, parentheses, `+`, `-`, `*`, unary `+` and `-`. Signed wrap exists only in `veriforge/signed_experiment.py` and is not a production mode. At width 8, `(127 + 1)` is `128` unsigned and `-128` signed.

## 5. Method

Protocol `veriforge-assurance-v1` hashed at `2026-10-11T16:43:36Z` before held-out scoring. Seed `20261011`. Families are not split. Labels come from the polynomial oracle or the exhaustive oracle, not from the family name. Historical n=8 was kept.

## 6. Baselines and fairness

Same 153 held-out pairs for every baseline in the first scored run. That run did not execute production Z3, the second encoder, CVC5, or Bitwuzla. The later production Z3 census is separate and is not an oracle-accuracy score. The rule baseline in the first run sees only the four identity rules and abstains otherwise. The testing baseline sees only its sample. The exhaustive oracle is the Mode B label, so agreement with it is not a second opinion.

## 7. Benchmark and ground truth

463 unique pairs, 27 families, dataset SHA-256 `36e430e0bdecfb47ac1d2ee254e7d2ba48a0f06664f7c34b7fd6e206fb746ae2`. Two pairs were `not_computed` because the domain was 16,777,216. They were not sampled and then called exhaustive.

## 8. Results

Held-out: 64 equivalent, 54 non-equivalent, 34 unsupported, 1 not computed.

Testing false equivalences: `0/54` at budgets 10, 100, 1,000, and 10,000. False differences: `0/64` at each budget.

Rule baseline false accepts: `0` non-equivalent pairs. It accepted 20 equivalent pairs and abstained on 98 labeled pairs.

Pipeline-versus-oracle false accepts `0/54` and false rejects `0/64`, circular with the label source.

Mode traps: 16/16 pairs differed by mode.

## 9. Uncertainty

Wilson 95% upper bound on the `0/54` testing miss rate is `0.0664135880908964`. The H_test decision uses the point comparison, which is `not_supported` because the rates are equal. The interval does not create a difference the counts do not show. Family clustering means 54 pairs are not 54 independent designs. Spearman `0.9684560277703408` is on 48 nested-addition configurations of a few microseconds. It does not estimate solver scaling.

## 10. Overhead

Testing the held-out equivalent and non-equivalent pairs took `0.004081947001168373` seconds at budget 10 and `4.782053818000122` seconds at budget 10,000. Evaluator medians on the scaling grid were about `6.4e-7` to `3.3e-6` seconds. Solver overhead was not measured. Shorter expressions are not an execution-speed claim. Five identity examples lost 1 or 3 operators.

## 11. Failures found

No false accept of a non-equivalent pair by the testing baseline or the rule baseline on the held-out labels. Two algebraic pairs exceeded the exhaustive budget and stayed unresolved. The later production census did run Z3; its status counts are in section 16. That section does not score Z3 against the labeling oracle.

## 12. Mutation results

`10/10` seeded mutants detected on fixed fixtures, `0` survived. Denominator 10. mutmut did not run. Later install attempts are in section 18.

## 13. Limitations

Shared Python integer semantics. CVC5 1.3.2 matched the Z3 status of every pair. Bitwuzla 0.8.2 matched on unsigned pairs and rejected integer logic. That agreement is not a proof of the translator. The first pipeline-versus-oracle comparison stays circular. Small expressions that boundary values hit easily. Historical H3 on the census stays unresolved because that timing was seen before a solver-time rule existed. A later preregistered pass on 72 new pairs is also unresolved. Alive2 was not run and is not a fair comparison. Z3 here is 4.8.17, not the pinned `z3-solver==5.1.0.0` wheel. pytest 9.1.1 passed 383 tests; Hypothesis on that run was Debian 6.155.7, not the lock pin 6.168.5.

## 14. Reproducibility

```bash
python3 scripts/run_assurance_experiment.py
python3 -m unittest tests.unit.test_research_hardening -v
python3 scripts/judge_safety_demo.py
```

The experiment refuses to score if the protocol hash changes. `scripts/run_production_smt.py` refuses to score if the amendment hash changes. PyPI and apt did not serve packages on this host. Z3 4.8.17 was taken from the Amazon Linux 2023 RPMs via the CloudFront host `d21lvh0gtuor4a.cloudfront.net`.

## 15. Conclusions the evidence supports

On this held-out set, raising the testing budget from 10 to 10,000 did not reduce false equivalences, because there were none at budget 10. Unsigned wrap and integer arithmetic disagree on the 16 recorded mode traps. The four identity rules did not falsely accept a held-out non-equivalent pair, and they abstained on most pairs. Production Z3 status counts are in section 16. They are not an accuracy claim against the oracles. The project does not claim a new formal method, a faster program, or a general proof.

## 16. Production Z3 census

Amendment `veriforge-production-smt-v1`, SHA-256 `3ef2952ca699df306978afa1e4f70f15dcb4a102d1cd0f63cc9a55f446b75d49`, recorded at `2026-10-11T18:20:40Z` before the run. `verify_equivalence_timed` on 463 pairs, timeout 5 seconds, Z3 4.8.17. `COUNTEREXAMPLE_FOUND` was counted only after the reference evaluator confirmed the model. That check passed for all 96 such rows.

| Status | All 463 | Mode A (132) | Mode B (331) | Development (310) | Held-out (153) |
| --- | --- | --- | --- | --- | --- |
| equivalent_within_model | 318 | 72 | 246 | 253 | 65 |
| counterexample_found | 96 | 34 | 62 | 42 | 54 |
| invalid_input | 8 | 2 | 6 | 8 | 0 |
| unsupported | 41 | 24 | 17 | 7 | 34 |
| unknown | 0 | 0 | 0 | 0 | 0 |
| timeout | 0 | 0 | 0 | 0 | 0 |

All eight admission templates were `equivalent_within_model` in Mode A and in the listed Mode B width, and they are in `default_rules()`. `add_self` at width 1 and `const_reassoc` at width 2 were `invalid_input` in Mode B and stayed out.

## 17. Second solver

Command: `python3 scripts/run_second_solver.py`. Binaries: CVC5 1.3.2 and Bitwuzla 0.8.2 from Debian sid packages extracted through `dpvctowv9b08b.cloudfront.net`. Timeout 5 seconds. Same 463 pairs and the same Mode A integer / Mode B unsigned semantics. `COUNTEREXAMPLE_FOUND` only after `reference_evaluator.evaluate` disagreed. Wall time 2.9129006489993117 seconds. Artifact: `experiments/reports/assurance-v1-smt/second_solver.json`.

| Solver | equivalent_within_model | counterexample_found | invalid_input | unsupported | solver_error |
| --- | --- | --- | --- | --- | --- |
| CVC5 1.3.2 | 318 | 96 | 8 | 41 | 0 |
| Bitwuzla 0.8.2 | 246 | 62 | 8 | 41 | 106 |

CVC5 matches Z3 on every pair, including Mode A 72/34/2/24 and Mode B 246/62/6/17. Bitwuzla’s 106 `solver_error` rows are the Mode A pairs that parsed: the binary reports `unsupported logic 'QF_NIA'`. Its Mode B counts match Z3 and CVC5. Against the labeling oracle, false equivalence is 0/96 for all three solvers. Two pairs the exhaustive oracle left `not_computed` (`av1-0252`, `av1-0258`) were `equivalent_within_model`. That oracle comparison is not an independent proof.

## 18. Confirmatory v2

Protocol SHA-256 `1d991b3c444f3a93b531196b4da4a9794937d697212b4e45d285cf8f0f6c498b` at `2026-10-11T18:59:22Z`, before the 72-pair file was written. `datasets/held_out/cases.jsonl` remains 8 lines. Z3 4.8.17 and CVC5 1.3.2 false equivalence: 0/33 pairs, 0/12 in Mode A, 0/21 in Mode B. Seven pairs are oracle `not_computed` and are not in that denominator. Correct acceptance 32/32. Correct rejection 33/33.

H3 is unresolved. Z3 init was `0.0069491530002778745` seconds and was not a per-case sample. Spearman of 12 family-median operator counts against family-median `solver_seconds` is `0.0036324031737947717`, with bootstrap interval `-0.5543202549518428` to `0.5625128124822065`. The uniform equivalent class has one family.

Ablation false equivalence stayed 0/33. Concrete checking and the full pipeline took more wall time than the verifier (0.46935624000252574 and 2.552952216999074 seconds versus 0.4641656299972965) and did not reduce the count. The encoder arm also stayed at 0/33.

`z3.proof()` returned objects for three UNSAT production queries and one direct integer query. No external checker ran. Podman 4.3.1 executed the Dockerfile and exited 1 when pip could not fetch setuptools. `z3-solver==5.1.0.0`, `hypothesis==6.168.5`, and mutmut were not fetched. pytest was not rerun against those pins. The suite record remains pytest 9.1.1, Hypothesis 6.155.7, Z3 4.8.17, 383 tests, 0 failures.
