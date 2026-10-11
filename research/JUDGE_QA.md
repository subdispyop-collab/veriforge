# Judge questions

1. What is genuinely original? No new algorithm is claimed. The new code is a second parser, a second evaluator, a polynomial check, and a budgeted exhaustive check for this grammar, plus a 463-pair measurement.

2. What is already known? Translation validation, Z3, Alive, Alive2, property-based testing, and mutation testing. See `research/LITERATURE_REVIEW.md`.

3. Why does the question matter? A single translator can be wrong and still return UNSAT. A second reading can catch some of those mistakes. The production census recorded Z3 statuses. It did not score those statuses against the labeling oracle.

4. Why were only four rules in 1.0.0? Those were the rules that release admitted. Eight more templates later returned `EQUIVALENT_WITHIN_MODEL` from production Z3 in Mode A and in a legal Mode B width, and those eight are now in `default_rules()`. Width-1 `x * 2` and width-2 `x + 5` stayed out.

5. Is the benchmark large enough? 463 pairs, 27 families, every reported category has at least 30 pairs. The pairs are small arithmetic expressions, not LLVM IR. Fifty-four held-out non-equivalent pairs are enough for the preregistered testing comparison and not enough to estimate rare solver bugs.

6. How were labels set? Mode A by polynomial identity. Mode B by exhaustive evaluation when the domain fit in 65,536 assignments. Construction intent was not the label. Two pairs stayed `not_computed`.

7. What keeps the translator and the evaluator from sharing a bug? They do not share source functions. They can still share a mistaken reading of unsigned wrap, and both use Python integers. The zero-assignment and top-of-range sweeps found 0 disagreements. That is not a proof.

8. Does a counterexample check prove equivalence? No. It only confirms one differentiating assignment.

9. What happens on UNKNOWN or timeout? The status stays `UNKNOWN` or `TIMEOUT`. The judge demo's timeout fixture was not labeled equivalent. A domain over the budget is `UNKNOWN`, not equivalent.

10. How is this different from Alive2? Alive2 validates LLVM IR with SMT and has found real miscompilations. VERIFORGE checks `+ - *` identities. This pass ran production Z3 4.8.17 on the 463-pair set. It did not run Alive2.

11. Does it improve execution speed or verifier reliability? Execution speed was not shown. Production Z3 returned 318 `equivalent_within_model`, 96 reference-confirmed `counterexample_found`, 8 `invalid_input`, and 41 `unsupported` on 463 pairs, with 0 `unknown` and 0 `timeout` at 5 seconds. That is a status census, not a reliability gain against the oracles. Testing on this set was already saturated at budget 10.

12. What is the measured overhead? Held-out testing wall time `0.00408` seconds at budget 10 and `4.782` seconds at budget 10,000. Evaluator medians on the scaling grid were under `4e-6` seconds. Solver overhead: not measured.

13. Which faults were reproduced? Ten seeded mutants, all detected on their fixtures. No published LLVM, GCC, or Alive2 bug was reproduced. The fetched arithmetic bugs need poison, `nsw`, shifts, casts, or floating point. The two `+`/`-` skeletons that can be written were `equivalent_within_model` in both modes.

14. Strongest remaining failure modes? A false UNSAT from a shared semantic mistake. CVC5 repeating Z3 does not remove that risk. Bitwuzla does not check Mode A. Testing looks perfect because these bugs are boundary-sized. Alive2 is a different language and was not compared.

15. What would falsify the main executed hypothesis? A held-out non-equivalent pair that budget 10,000 distinguishes and budget 10 does not, in these files. The files show `0/54` and `0/54`, so the strict decrease is false.

16. Why trust the results? The protocol hash was written at `2026-10-11T16:43:36Z` before the first scored run. The production-Z3 amendment hash was written at `2026-10-11T18:20:40Z` before `scripts/run_production_smt.py`. Counts match `experiments/reports/assurance-v1/summary.json` and `experiments/reports/assurance-v1-smt/production_smt.json`. Historical n=8 was not edited.

17. Which claims are excluded? A new decision procedure, an execution speedup, a population error rate, an IRIS score, a judge score, a Z3 proof certificate, signed Mode B as a product mode, and any claim that solver agreement proves the translator. The Z3, CVC5, and Bitwuzla status counts are reported as counts. The 0/96 false-equivalence figure uses the project’s own oracle and is not an external proof.
