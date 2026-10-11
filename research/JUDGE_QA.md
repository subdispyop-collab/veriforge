# Judge questions

1. What is genuinely original? No new algorithm is claimed. The new code is a second parser, a second evaluator, a polynomial check, and a budgeted exhaustive check for this grammar, plus a 463-pair measurement.

2. What is already known? Translation validation, Z3, Alive, Alive2, property-based testing, and mutation testing. See `research/LITERATURE_REVIEW.md`.

3. Why does the question matter? A single translator can be wrong and still return UNSAT. A second reading can catch some of those mistakes. This run did not measure that against Z3, because Z3 was not installed.

4. Why are four production rules enough for the current scope? They are the rules the 1.0.0 optimizer actually applies. Eight more candidates passed an independent check and stayed out of `default_rules()` until Z3 admission can run.

5. Is the benchmark large enough? 463 pairs, 27 families, every reported category has at least 30 pairs. The pairs are small arithmetic expressions, not LLVM IR. Fifty-four held-out non-equivalent pairs are enough for the preregistered testing comparison and not enough to estimate rare solver bugs.

6. How were labels set? Mode A by polynomial identity. Mode B by exhaustive evaluation when the domain fit in 65,536 assignments. Construction intent was not the label. Two pairs stayed `not_computed`.

7. What keeps the translator and the evaluator from sharing a bug? They do not share source functions. They can still share a mistaken reading of unsigned wrap, and both use Python integers. The zero-assignment and top-of-range sweeps found 0 disagreements. That is not a proof.

8. Does a counterexample check prove equivalence? No. It only confirms one differentiating assignment.

9. What happens on UNKNOWN or timeout? The status stays `UNKNOWN` or `TIMEOUT`. The judge demo's timeout fixture was not labeled equivalent. A domain over the budget is `UNKNOWN`, not equivalent.

10. How is this different from Alive2? Alive2 validates LLVM IR with SMT and has found real miscompilations. VERIFORGE 1.0.0 checks four identities on `+ - *`. This pass did not run Alive2 and did not run Z3.

11. Does it improve execution speed or verifier reliability? Neither was shown for the production Z3 path. Testing reliability on this particular set was already saturated at budget 10. Operator count dropped on five identity examples. That is not a runtime speedup.

12. What is the measured overhead? Held-out testing wall time `0.00408` seconds at budget 10 and `4.782` seconds at budget 10,000. Evaluator medians on the scaling grid were under `4e-6` seconds. Solver overhead: not measured.

13. Which faults were reproduced? Ten seeded mutants, all detected on their fixtures. The width-1 fact that addition and subtraction coincide was reproduced on development before the protocol hash. No LLVM bug ID was reproduced, because the bug trackers were unreachable.

14. Strongest remaining failure modes? A false UNSAT from a shared semantic mistake; any domain larger than the budget; the missing SMT comparison; testing that looks perfect because the bugs are boundary-sized.

15. What would falsify the main executed hypothesis? A held-out non-equivalent pair that budget 10,000 distinguishes and budget 10 does not, in these files. The files show `0/54` and `0/54`, so the strict decrease is false.

16. Why trust the results? The protocol hash was written at `2026-10-11T16:43:36Z` before the scored run. Counts match `experiments/reports/assurance-v1/summary.json`. Historical n=8 was not edited. Z3 numbers were not invented.

17. Which claims are excluded? Novelty, execution speedup, population error rates, SMT-versus-testing comparisons, CVC5 or Bitwuzla results, Z3 proof certificates, signed Mode B as a product mode, and any IRIS score.
