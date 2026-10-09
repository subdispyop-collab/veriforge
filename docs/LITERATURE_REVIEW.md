# Literature review

Protocol reference: controlling specification §16.  
Access date for online sources: **2026-10-09**.  
Method: web search against publisher/author pages and DOIs; bibliographic fields recorded below. No citation was invented.

This review situates VERIFORGE among established methods. It does **not** establish a novel research contribution. Confirmed research findings from VERIFORGE’s held-out evaluation are recorded separately in the evidence ledger and Phase 10 evaluation report; where measurements are unavailable, that status is explicit.

## Scope investigated

| Topic (§16) | Covered in this review |
| --- | --- |
| SMT-based program verification | Yes (Z3; SMT encodings in Alive/Alive2) |
| Compiler optimization correctness | Yes (CompCert; Alive; Alive2) |
| Translation validation | Yes (Pnueli et al.; Necula; Alive2) |
| Equivalence checking | Yes (Alive; Alive2; Gupta et al.) |
| Arithmetic expression rewriting | Partial — peephole / IR rewrite verification (Alive family); not a dedicated survey of standalone arithmetic DSLs |
| Property-based and differential testing | Yes (QuickCheck; Hypothesis) |
| Mutation testing | Yes (Jia & Harman survey) |
| Verification-performance trade-offs | Partial — Alive2 discusses bounded resource limits; quantitative VERIFORGE overhead remains an experimental question |

## Annotated sources

### L1 — Translation validation (foundational)

- **Title:** Translation Validation  
- **Authors:** Amir Pnueli, Michael Siegel, Eli Singerman  
- **Venue:** Tools and Algorithms for the Construction and Analysis of Systems (TACAS 1998), Lecture Notes in Computer Science, vol. 1384, pp. 151–166  
- **Year:** 1998  
- **DOI / URL:** https://doi.org/10.1007/BFb0054170  
- **Access date:** 2026-10-09  
- **Claim supported:** Validates each translation/compiler run rather than proving the entire translator once; introduces the translation-validation framing used by later equivalence checkers.  
- **Relation to VERIFORGE:** Established method. VERIFORGE’s per-candidate SMT equivalence check is an instance of this idea on a restricted arithmetic fragment, not a new validation paradigm.

### L2 — Translation validation for an optimizing compiler

- **Title:** Translation Validation for an Optimizing Compiler  
- **Authors:** George C. Necula  
- **Venue:** ACM SIGPLAN Conference on Programming Language Design and Implementation (PLDI 2000); also ACM SIGPLAN Notices 35(5):83–94  
- **Year:** 2000  
- **DOI / URL:** https://doi.org/10.1145/349299.349314  
- **Access date:** 2026-10-09  
- **Claim supported:** Practical infrastructure can check semantic preservation across compiler passes (demonstrated for GCC) with effort comparable to implementing one pass.  
- **Relation to VERIFORGE:** Established combination of compiler IR comparison and automated checking. VERIFORGE targets user-level arithmetic expressions rather than full compiler IRs.

### L3 — Z3 SMT solver

- **Title:** Z3: An Efficient SMT Solver  
- **Authors:** Leonardo de Moura, Nikolaj Bjørner  
- **Venue:** TACAS 2008, LNCS 4963, pp. 337–340  
- **Year:** 2008  
- **DOI / URL:** https://doi.org/10.1007/978-3-540-78800-3_24  
- **Access date:** 2026-10-09  
- **Claim supported:** Z3 decides SMT formulas over combinations of theories including arithmetic and bit-vectors and is used in software verification applications.  
- **Relation to VERIFORGE:** Established tool. VERIFORGE uses the pinned `z3-solver` package as its verification engine (trusted computing base; see `docs/FORMAL_MODEL.md`).

### L4 — CompCert verified compiler

- **Title:** Formal Verification of a Realistic Compiler  
- **Authors:** Xavier Leroy  
- **Venue:** Communications of the ACM, 52(7):107–115  
- **Year:** 2009  
- **DOI / URL:** https://doi.org/10.1145/1538788.1538814  
- **Access date:** 2026-10-09  
- **Claim supported:** A realistic C subset compiler (CompCert) can be proved to preserve semantics using a proof assistant, providing compiler-correctness guarantees stronger than per-run validation alone.  
- **Relation to VERIFORGE:** Established contrasting method (verified compiler vs translation validation). Not selected as an external baseline: different language, workload, and proof artifact; a fair same-workload comparison was not implemented.

### L5 — Alive peephole optimization verification

- **Title:** Provably Correct Peephole Optimizations with Alive  
- **Authors:** Nuno P. Lopes, David Menendez, Santosh Nagarakatte, John Regehr  
- **Venue:** PLDI 2015, pp. 22–32  
- **Year:** 2015  
- **DOI / URL:** https://doi.org/10.1145/2737924.2737965  
- **Access date:** 2026-10-09  
- **Claim supported:** A DSL plus SMT discharging can prove LLVM peephole rewrites correct or produce counterexamples; used to find incorrect LLVM optimizations.  
- **Relation to VERIFORGE:** Closest established combination (rewrite rules + SMT equivalence/counterexamples). VERIFORGE applies a much smaller identity-rule set to a restricted expression language with explicit Mode A / Mode B semantics. No novelty claim that this combination is new.

### L6 — Alive2 bounded translation validation

- **Title:** Alive2: Bounded Translation Validation for LLVM  
- **Authors:** Nuno P. Lopes, Juneyoung Lee, Chung-Kil Hur, Zhengyang Liu, John Regehr  
- **Venue:** PLDI 2021  
- **Year:** 2021  
- **DOI / URL:** https://doi.org/10.1145/3453483.3454030  
- **Access date:** 2026-10-09  
- **Claim supported:** Automatic SMT-based bounded translation validation for LLVM IR can find real miscompilation bugs while limiting resources (e.g., loop unrolling bounds); designed to avoid false alarms.  
- **Relation to VERIFORGE:** Established method for verification-performance trade-offs via bounds/timeouts. VERIFORGE similarly treats TIMEOUT/UNKNOWN as non-equivalence and records solver time separately from execution time.

### L7 — Program equivalence checking with SMT (invariant sketching)

- **Title:** Effective Use of SMT Solvers for Program Equivalence Checking through Invariant Sketching and Query Decomposition  
- **Authors:** (as listed on author PDF) — see https://sorav.compiler.ai/pubs/sat18.pdf  
- **Venue:** SAT 2018 (author-hosted PDF verified 2026-10-09)  
- **Year:** 2018  
- **DOI / URL:** https://sorav.compiler.ai/pubs/sat18.pdf (access date 2026-10-09)  
- **Access date:** 2026-10-09  
- **Claim supported:** SMT solvers discharge equivalence proof obligations; invariant sketching and query decomposition extend which transformations can be proved equivalent.  
- **Relation to VERIFORGE:** Established equivalence-checking techniques for programs with richer control flow than VERIFORGE’s loop-free arithmetic fragment.

### L8 — QuickCheck property-based testing

- **Title:** QuickCheck: A Lightweight Tool for Random Testing of Haskell Programs  
- **Authors:** Koen Claessen, John Hughes  
- **Venue:** ICFP 2000; ACM SIGPLAN Notices 35(9):268–279  
- **Year:** 2000  
- **DOI / URL:** https://doi.org/10.1145/351240.351266  
- **Access date:** 2026-10-09  
- **Claim supported:** Properties can be tested on randomly generated inputs; foundational property-based testing method.  
- **Relation to VERIFORGE:** Established method. VERIFORGE’s Hypothesis properties inherit this testing style; passing properties is not a mathematical proof of equivalence (§3 / §20).

### L9 — Hypothesis property-based testing (Python)

- **Title:** Hypothesis: A New Approach to Property-Based Testing  
- **Authors:** David R. MacIver, Zac Hatfield-Dodds, and many other contributors  
- **Venue:** Journal of Open Source Software, 4(43), 1891  
- **Year:** 2019  
- **DOI / URL:** https://doi.org/10.21105/joss.01891  
- **Access date:** 2026-10-09  
- **Claim supported:** Hypothesis provides mature property-based testing for Python with shrinking and structured generation.  
- **Relation to VERIFORGE:** Tool used in the test suite. Not a VERIFORGE research finding.

### L10 — Mutation testing survey

- **Title:** An Analysis and Survey of the Development of Mutation Testing  
- **Authors:** Yue Jia, Mark Harman  
- **Venue:** IEEE Transactions on Software Engineering, 37(5):649–678  
- **Year:** 2011  
- **DOI / URL:** https://doi.org/10.1109/TSE.2010.62  
- **Access date:** 2026-10-09  
- **Claim supported:** Mutation testing injects artificial faults to evaluate detection power; the literature is mature and widely studied.  
- **Relation to VERIFORGE:** Established method. VERIFORGE’s `fuzzer_suite` artificial mutations are EVALUATION_ONLY and must not be presented as real-world defect prevalence.

### L11 — SMT-based translation validation for ML compilers

- **Title:** SMT-Based Translation Validation for Machine Learning Compiler  
- **Authors:** (mlir-tv / Springer chapter; see https://link.springer.com/chapter/10.1007/978-3-031-13188-2_19)  
- **Venue:** CAV 2022 proceedings chapter (LNCS; Springer link verified 2026-10-09)  
- **Year:** 2022  
- **DOI / URL:** https://doi.org/10.1007/978-3-031-13188-2_19  
- **Access date:** 2026-10-09  
- **Claim supported:** SMT encodings can validate MLIR-style transformations, with abstraction/refinement for floating-point and reductions.  
- **Relation to VERIFORGE:** Established SMT translation-validation instance in another domain. Not a fair external baseline for VERIFORGE’s integer/bit-vector expression fragment.

## Distinctions required by §16

1. **Established methods:** Translation validation; SMT solving; verified compilers; peephole rewrite verification; property-based testing; mutation testing.  
2. **Existing combinations:** Rewrite candidates + SMT equivalence/counterexamples (Alive/Alive2 family); bounded/timeout resource policies in validators.  
3. **Features implemented in VERIFORGE:** Restricted safe parser; Mode A mathematical integers vs Mode B unsigned fixed-width; conservative identity rules; verification-guided acceptance; separated solver vs execution timing; held-out dataset discipline; audit/export.  
4. **Possible contributions that still require evidence:** Whether SMT checking improves incorrect-rewrite detection *on VERIFORGE’s held-out set* with measured overhead — hypotheses H1–H3 remain hypotheses until supported by held-out observations.  
5. **Confirmed research findings:** None claimed as novel scientific results from this review alone. Experimental confirmation depends on held-out runs recorded in `experiments/reports/` and `docs/EVIDENCE_LEDGER.md`.

## Novelty assessment

**No novelty claim.** VERIFORGE assembles established techniques (safe parsing, identity rewriting, Z3 equivalence checks, property/mutation testing, reproducible experiment logging) under an explicit dual semantic contract. That engineering assembly is not, by itself, a confirmed research contribution.

## Limitations of this review

- Review used online bibliographic sources available through the agent research tools on 2026-10-09.  
- Not every adjacent paper on arithmetic simplification, superoptimization, or differential testing was exhaustively surveyed.  
- Author lists for L7 and L11 should be cross-checked against the PDF title pages when citing in a formal publication.  
- If additional offline library access becomes available, deepen coverage of arithmetic rewrite systems and verification-cost studies; see plan below.

## Follow-up literature-review plan (if deeper access is needed)

1. Pull full PDFs for L1–L11 and extract precise page-level quotations for claims used in the final research report.  
2. Add surveys on SMT bit-vector theory performance and on expression-simplification correctness.  
3. Decide whether any external tool can be integrated as baseline 5 under equal semantics/workload; until then keep `not_selected`.  
4. Update this file’s access dates and evidence-ledger novelty rows only when new sources are actually read.
