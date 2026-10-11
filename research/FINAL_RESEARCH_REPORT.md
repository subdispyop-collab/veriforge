# Final research report

Version under discussion: VERIFORGE `1.0.0`. This report does not raise the version.

## 1. Question and motivation

Can a second, non-Z3 reading of a small arithmetic language catch semantic mistakes that a single translator would miss, and what does that cost? The production tool already checks four identities with Z3. The open risk was a shared encoding bug, a small held-out set, and an unresolved complexity hypothesis.

## 2. Prior work

Translation validation, Z3, Alive, and Alive2 already do SMT equivalence checking of rewrites. Property-based testing and mutation testing are older than this project. Sources and the failed 2026 refresh are in `research/LITERATURE_REVIEW.md`. No novelty claim follows from a blocked search.

## 3. Contribution

An auditable engineering layer: independent parser and evaluator, polynomial identity for integers, exhaustive unsigned checks inside a budget, a frozen 463-pair dataset, and preregistered decisions. It is not a new verifier for general programs. Eight further algebraic rules were checked independently and were not admitted to production, because Z3 did not run.

## 4. Semantics and scope

Mode A: mathematical integers. Mode B: unsigned values in `[0, 2^w - 1]`, wrap on `+`, `-`, and `*`, literals outside the range rejected. Grammar: literals, variables, parentheses, `+`, `-`, `*`, unary `+` and `-`. Signed wrap exists only in `veriforge/signed_experiment.py` and is not a production mode. At width 8, `(127 + 1)` is `128` unsigned and `-128` signed.

## 5. Method

Protocol `veriforge-assurance-v1` hashed at `2026-10-11T16:43:36Z` before held-out scoring. Seed `20261011`. Families are not split. Labels come from the polynomial oracle or the exhaustive oracle, not from the family name. Historical n=8 was kept.

## 6. Baselines and fairness

Same 153 held-out pairs for every baseline that ran. Production Z3, the second Z3 encoder, CVC5, and Bitwuzla did not run. The rule baseline sees only the four identity rules and abstains otherwise. The testing baseline sees only its sample. The exhaustive oracle is the Mode B label, so agreement with it is not a second opinion.

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

No false accept of a non-equivalent pair by the testing baseline or the rule baseline on the held-out labels. The production optimizer was not re-scored with Z3. Two algebraic pairs exceeded the exhaustive budget and stayed unresolved. A missing Z3 install is reported as solver unavailable, not as equivalence.

## 12. Mutation results

`10/10` seeded mutants detected on fixed fixtures, `0` survived. Denominator 10. mutmut did not run.

## 13. Limitations

Shared Python integer semantics. No second SMT solver. Circular oracle comparison. Small expressions that boundary values hit easily. H_audit inconclusive. Historical H3 unresolved. No 2026 literature refresh. Official IRIS rules were not fetched.

## 14. Reproducibility

```bash
python3 scripts/run_assurance_experiment.py
python3 -m unittest tests.unit.test_research_hardening -v
python3 scripts/judge_safety_demo.py
```

The experiment refuses to score if the protocol hash changes. This host could not `pip install`. A machine with the lockfile packages can run the existing pytest suite; this host did not.

## 15. Conclusions the evidence supports

On this held-out set, raising the testing budget from 10 to 10,000 did not reduce false equivalences, because there were none at budget 10. Unsigned wrap and integer arithmetic disagree on the 16 recorded mode traps. The four identity rules did not falsely accept a held-out non-equivalent pair, and they abstained on most pairs. Z3 reliability relative to the new oracles was not measured. The project does not claim a new formal method, a faster program, or a general proof.
