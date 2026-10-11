# Literature review

Access date for sources already recorded in `docs/LITERATURE_REVIEW.md`: 2026-10-09. A fresh retrieval on 2026-10-11 failed. HTTPS to publisher and GitHub hosts ended with `SSL_ERROR_SYSCALL`, and hosts outside the run's egress allowlist returned HTTP 403. No 2026 paper was opened. Absence of a 2026 hit is not evidence that an idea is new.

This review does not add citations that were not already checked in the repository. Bibliographic fields below are copied from that earlier review.

## Comparison

| Prior work | Research problem | Method | Evaluation | Overlap with VERIFORGE | Remaining gap |
| --- | --- | --- | --- | --- | --- |
| Pnueli, Siegel, Singerman, TACAS 1998, DOI 10.1007/BFb0054170 | Compiler runs may be wrong even if the compiler is not proved once | Translation validation of each run | Theoretical framework | Per-candidate equivalence checks are an instance of this idea | VERIFORGE does not validate a compiler |
| Necula, PLDI 2000, DOI 10.1145/349299.349314 | Checking an optimizing compiler | Symbolic invariants and automated checks | GCC | Equivalence checking of transforms | Different language and workload |
| de Moura and Bjørner, TACAS 2008, DOI 10.1007/978-3-540-78800-3_24 | SMT across theories | Z3 | Solver paper | Production verifier uses Z3 when installed | This host could not run Z3 |
| Leroy, CACM 2009, DOI 10.1145/1538788.1538814 | Proving a compiler | CompCert in a proof assistant | Realistic C subset | Contrasting method, not a baseline | Not integrated |
| Lopes et al., PLDI 2015, DOI 10.1145/2737924.2737965 | Wrong LLVM peephole rules | Alive DSL plus SMT | Found LLVM bugs | Rewrite plus SMT counterexamples | VERIFORGE's grammar is `+ - *` only |
| Lopes et al., PLDI 2021, DOI 10.1145/3453483.3454030 | LLVM miscompilations | Alive2 bounded translation validation | Real LLVM bugs, resource bounds | Timeout is not success | Alive2 is not a same-workload baseline here |
| Jia and Harman, IEEE TSE 2011, DOI 10.1109/TSE.2010.62 | How to test tests | Mutation testing survey | Literature survey | Seeded faults in a harness | Ten fixtures are not a mutation-testing study of a compiler |
| Claessen and Hughes, ICFP 2000, DOI 10.1145/351240.351266 | Property testing | QuickCheck | Haskell examples | Testing is not a proof | Budget-10 testing caught every bug in this particular held-out set; that is not a general proof |
| MacIver et al., JOSS 2019, DOI 10.21105/joss.01891 | Python property tests | Hypothesis | Tool paper | Used by the existing suite | Not run on this host |

## What this does not show

The combination "independent parser, concrete evaluator, exhaustive finite check, polynomial identity, and seeded faults" was not shown to be absent from the literature. Differential testing and N-version comparison are established themes in the sources above and in the testing literature those sources cite. VERIFORGE's 1.0.0 release already refused a novelty claim. This pass does not reverse that refusal.
