# Compiler-bug case study

This is a case study, not a benchmark and not a bug discovery. VERIFORGE did not find these bugs. The grammar is literals, names, parentheses, and `+`, `-`, `*`. A fetched report is encoded only when both sides can be written in that grammar. Measured statuses come from `verify_equivalence_timed` on 2026-10-11 and are stored in `experiments/reports/assurance-v1-smt/part15_confusion.json` under `encoded_case_study`.

## Sources actually opened

1. Lopes, Lee, Hur, Liu, and Regehr, “Alive2: Bounded Translation Validation for LLVM,” PLDI 2021. Page text retrieved from `https://web.ist.utl.pt/nuno.lopes/pubs/alive2-pldi21.pdf` and saved locally during retrieval. The paper says: “4 incorrect arithmetic operations.” The selected arithmetic example says: “This transformation, which exploits the associativity of addition to reduce the number of instructions using vector addition, is not a refinement. The problem is that LLVM’s addition operator, when qualified by the nsw flag (which turns signed overflows into poison values), is not associative.”
2. LLVM issue 57683, retrieved as page text: “Reassociation pass incorrectly uses an existing vector with poison elements as replacement in (sub A B) -> (add A, -B).” URL: `https://github.com/llvm/llvm-project/issues/57683`.
3. Alive2 README, retrieved as page text. The release/10.x example uses `sub`, `icmp`, `zext`, and `lshr`, and the optimized function returns only `sub i3 0, %0`. URL: `https://github.com/AliveToolkit/alive2`.
4. GCC commit message for PR119417, retrieved as page text: “The mult_rhs1 operand already has SImode and we change type1 to unsigned int and so no cast is actually done, except that the & 0xffff is lost that way.” URL: `https://github.com/zephyrproject-rtos/gcc/commit/6c7c25c282642565b23da21cab7e313e78744ab5`.

## Encoded skeletons

| Case | Original | Candidate | Mode | Status |
| --- | --- | --- | --- | --- |
| pldi21-nsw-add-skeleton | `((a + b) + (c + d))` | `(((a + b) + c) + d)` | A | equivalent_within_model |
| pldi21-nsw-add-skeleton | same | same | B, width 8 | equivalent_within_model |
| llvm-57683-scalar-negation | `(a - b)` | `(a + (-b))` | A | equivalent_within_model |
| llvm-57683-scalar-negation | same | same | B, width 8 | equivalent_within_model |

These statuses do not reproduce the published bugs. Without `nsw` or poison, addition is associative in Mode A and under unsigned wrap, and `(a - b)` equals `(a + (-b))` in both modes.

## Fetched reports that do not fit

- The Alive2 release/10.x miscompile needs `icmp`, `zext`, and `lshr`. Those operators are outside the grammar, so the pair was not encoded.
- GCC PR119417 drops a mask and changes integer casts during widening multiplication. Masks and casts are outside the grammar, so the pair was not encoded.
- The PLDI paper’s second selected bug is `fmul nsz` followed by `fadd` of `+0.0`. Floating point is outside the grammar.

## Conclusion

No fetched LLVM, GCC, or Alive2 arithmetic bug reduces to two non-equivalent expressions in this grammar. Alive2 is not a fair baseline: it checks LLVM IR refinement, including poison, flags, memory, and control flow. VERIFORGE was not run against Alive2, and no accuracy or speed comparison is claimed.
