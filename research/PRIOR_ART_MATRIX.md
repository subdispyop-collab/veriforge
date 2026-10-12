# Prior-art matrix

Access date for searches in this file: 2026-10-12. Sources already in `docs/LITERATURE_REVIEW.md` were accessed 2026-10-09. A paper is cited only when a page or a search result retrieved in this session, or that earlier review, records the bibliographic fields. Unopened papers are marked.

Alive2 was not run. No Alive2 score is stated.

## Methods

### Polynomial expansion over the integers

- Problem: decide whether two `+` `-` `*` expressions denote the same function on all integers.
- Semantics: the polynomial ring in commuting variables over `Z`.
- Core idea: expand to monomials and compare coefficients. Schwartz's 1980 paper, retrieved from the ACM record and an extracted PDF, states that identity testing asks whether the simplified form has all coefficients zero, and that direct expansion is hopeless when the expression is huge (`Journal of the ACM` 27(4):701–717, DOI `10.1145/322217.322225`).
- Guarantees: complete for this operator set when expansion finishes. The VERIFORGE implementation stops at 4096 terms and returns `not_computed`.
- Equivalence: identical coefficient maps. Inequivalence: a witness assignment on the difference.
- Bottleneck: term blow-up under multiplication.
- Limitation: unequal integer polynomials can still agree modulo `2^w`.
- Relation: this is `veriforge/polynomial_oracle.py`. It is not a proposed new method.
- Distinction from a new method: none. Reimplementing it would be the same algorithm.

### Randomized polynomial identity testing

- Problem: same integer identity question, without full expansion.
- Semantics: polynomials over an integral domain. Schwartz 1980 requires an infinite domain at points in the argument. The Wikipedia page retrieved the same day also names Zippel, EUROSAM 1979, LNCS 72:216–226, DOI `10.1007/3-540-09519-5_73`, and DeMillo and Lipton, Information Processing Letters 7(4):193–195, 1978, DOI `10.1016/0020-0190(78)90067-4`. Those two papers were not opened.
- Core idea: a nonzero polynomial of known degree is unlikely to vanish at a random point from a large set.
- Guarantees: probabilistic, one-sided. A nonzero evaluation proves inequivalence. A zero evaluation does not prove equivalence.
- Bottleneck: repeating trials, and choosing a domain larger than the degree.
- Limitation: the master prompt forbids treating a finite sample as universal equivalence.
- Relation: VERIFORGE's testing baseline is this idea without the probabilistic completeness claim. H_test was not supported on the held-out non-equivalent pairs.
- Distinction: a new wrapper around random evaluation would not be a new algorithm, and it would be unsound if it returned `EQUIVALENT`.

### Z3

- Problem: SMT, including arithmetic and bit-vectors.
- Source: de Moura and Bjørner, TACAS 2008, LNCS 4963:337–340, DOI `10.1007/978-3-540-78800-3_24`, from the 2026-10-09 review.
- Core idea: a CDCL-style SMT solver over combined theories. VERIFORGE asks it whether `original != candidate` is satisfiable.
- Equivalence in this project: `unsat`, after the encoding. Inequivalence: a model confirmed by the reference evaluator.
- Bottleneck: nonlinear integer arithmetic and bit-vector multiplication.
- Limitation: the encoding is part of the trusted base. Two calls to Z3 are not independent proofs.
- Measured on this project, not rerun here: 463 pairs, timeout 5 seconds, Z3 4.8.17, no timeout. Confirmatory-v2 false equivalence 0/33.
- Distinction: calling Z3 is the existing production verifier.

### cvc5

- Problem: SMT-LIB, including the logics VERIFORGE emits.
- Source retrieved 2026-10-12: Barbosa, Barrett, Brain, Kremer, Lachnitt, Mann, Mohamed, Mohamed, Niemetz, Nötzli, Ozdemir, Preiner, Reynolds, Sheng, Tinelli, and Zohar, TACAS 2022, LNCS 13243:415–442, DOI `10.1007/978-3-030-99524-9_24`. The abstract in the retrieved PDF says cvc5 builds on CVC4 and is compared with CVC4 and Z3 on SMT-LIB.
- Core idea: a separate SMT solver, used here as a second translation of the same semantics.
- Measured, not rerun: cvc5 1.3.2 matched Z3 on all 463 pairs. Agreement does not prove the translation.
- Distinction: calling cvc5 is a baseline, not a new method.

### Polynomial functions modulo `p^e`

- Problem: decide whether two integer polynomials define the same function on `Z/p^e Z`.
- Sources retrieved 2026-10-12:
  - L. Carlitz, Functions and polynomials (mod `p^n`), Acta Arithmetica 9(1):67–78, 1964, DOI `10.4064/aa-9-1-67-78`. The journal landing page was retrieved. The article body was not opened.
  - IACR eprint 2022/1364, text retrieved. It states that since the mid-1960s the literature uses the falling-factorial basis because those polynomials produce null polynomials modulo `p^e`, and that two integer polynomials represent the same function modulo `p^e` if and only if their difference is a null polynomial. It attributes the unique canonical representation of bounded falling-factorial coefficients to Keller and Olson, Duke Mathematical Journal 35(4):835–838, 1968. That 1968 paper was not opened.
- Core idea: reduce the difference into that canonical basis. The function is identically zero modulo `2^w` exactly when every canonical coefficient is zero.
- Guarantees: this is a known decision method for polynomial functions on `Z/2^w Z`, not a theorem discovered here.
- Bottleneck: multivariate analogues still expand, and the null ideal is nontrivial, so integer inequality is not modular inequality.
- Relation: this is the mathematical reason Mode B can disagree with Mode A. VERIFORGE does not implement the canonical basis. It uses exhaustive search or SMT.
- Distinction from a new method: implementing Keller–Olson / falling-factorial reduction would be an implementation of published mathematics. It is not a new algorithm.

### Equality saturation

- Problem: rewrite expressions by saturating an e-graph.
- Source retrieved 2026-10-12: Willsey, Nandi, Wang, Flatt, Tatlock, and Panchekha, egg: Fast and Extensible Equality Saturation, Proc. ACM Program. Lang. 5(POPL), article 23, 2021, DOI `10.1145/3434304`. The ACM record and a PDF were retrieved. The PDF describes e-graphs as a congruence and equality saturation as rewrite-driven optimization and synthesis, not as a new decision procedure for integer polynomial identity.
- Guarantees: only the equalities derivable from the supplied rules. A finite rule set for `+` `-` `*` is not automatically complete.
- Bottleneck: e-graph growth.
- Relation: VERIFORGE already admits twelve production rules only after Z3 accepted their templates. Those rules are not a complete decision procedure.
- Distinction: adding egg, or a hand-rolled e-graph, would apply a published technique. Completeness would collapse back into polynomial identity or an incomplete rewrite system.

### Alive and Alive2

- Alive: Lopes, Menendez, Nagarakatte, and Regehr, PLDI 2015, DOI `10.1145/2737924.2737965`.
- Alive2: Lopes, Lee, Hur, Liu, and Regehr, PLDI 2021, DOI `10.1145/3453483.3454030`.
- Problem: LLVM peephole or IR refinement, including poison and flags.
- Semantics: not the VERIFORGE expression language. The earlier case study encoded two `+` `-` skeletons and both were equivalent in Mode A and Mode B width 8. The bugs that were fetched need poison, flags, casts, or vector lanes.
- Comparison: not fair. No score.

### Translation validation and other SMT equivalence work

Pnueli, Siegel, and Singerman, TACAS 1998, DOI `10.1007/BFb0054170`. Necula, PLDI 2000, DOI `10.1145/349299.349314`. Leroy, CACM 2009, DOI `10.1145/1538788.1538814`. The SAT 2018 PDF at `https://sorav.compiler.ai/pubs/sat18.pdf` is listed in the 2026-10-09 review; this session did not open it, so author names are not repeated. The CAV 2022 MLIR chapter, DOI `10.1007/978-3-031-13188-2_19`, is a different language.

These solve program or IR equivalence. They do not supply a new decision procedure for a pair of `+` `-` `*` expressions.

## Gap that remains after this matrix

The fragment is already decided, when the resource bound allows, by polynomial expansion over `Z`, by a published canonical form modulo `2^w`, or by SMT. The open engineering issues are term blow-up, the 65536 exhaustive budget, and the trusted translator. None of those issues is a missing algorithm whose identity is distinct from the rows above.
