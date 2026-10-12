# Candidate methods and the go / no-go gate

Five designs were written down before any implementation. None is implemented. The gate is **NO-GO**.

The review in the last section is an internal adversarial review by the same author. It is not an independent audit.

## Candidate 1 — exact integer expansion

1. Expand both expressions in the monomial basis of `Z[x1,...,xk]` and compare coefficients.
2. Pseudocode: `expand` on literals, variables, unary minus as scaling, addition as coefficient sum, multiplication as the distributive product; return EQUIVALENT if the maps match, NOT_EQUIVALENT with a witness if they differ, UNKNOWN if the term count exceeds a budget.
3. Basis: the polynomial ring. Two polynomials are equal as functions on `Z` exactly when their coefficients match, for this operator set.
4. Sound and complete inside the budget. Incomplete when the budget trips.
5. Proof obligation: every algebraic step preserves the denoted polynomial, and the witness makes the coefficient difference nonzero. This is already the argument in `polynomial_oracle.py`.
6. Worst case is exponential in expression size because products of sums multiply term counts.
7. This is the existing checker. It is not Z3 and not cvc5. It is not different from VERIFORGE.
8. It can beat SMT when both expansions are tiny. That advantage is the existing oracle, not a new result.
9. A wide sum-of-products blows the budget and returns UNKNOWN while Z3 may still answer.
10. Hypothesis that would have been tested: fewer UNKNOWN results than Z3 at the same timeout on expressions with more than 4096 monomials. Falsifier: Z3 also returns unknown, or the new code is the same expansion.

Rejected. The algorithmic step is the current code.

## Candidate 2 — Schwartz evaluation as a proof

1. Bound the degree from the syntax. Evaluate the difference at one or more random points. Return EQUIVALENT if every evaluation is zero.
2. Pseudocode: `degree(e)`; sample `x` from a large interval; if `eval(left,x) != eval(right,x)` return NOT_EQUIVALENT; else return EQUIVALENT.
3. Schwartz, JACM 1980, gives a probabilistic bound, not a certainty, unless the sample is large enough for a zero error, which returns to evaluating a huge grid or expanding.
4. Sound for NOT_EQUIVALENT when the concrete evaluator confirms the point. Unsound for EQUIVALENT on a small sample.
5. The proof obligation for EQUIVALENT cannot be discharged by a finite sample that the lemma does not make exhaustive.
6. Each trial is cheap. The number of trials required for certainty grows with degree and the number of variables.
7. Differs from Z3 by not searching. Differs from expansion by not building the coefficient map. The lemma is prior work, and the prompt forbids the unsound reading.
8. A single random point can find a rare counterexample faster than expansion. That is testing, and the testing baseline already lost its preregistered comparison.
9. Equivalent expressions always evaluate equal, so the procedure cannot confirm them. Inequivalent polynomials that vanish on the sample are false equivalences.
10. Falsifier: any pair the polynomial oracle calls non-equivalent and this procedure calls EQUIVALENT. One such pair kills a soundness claim.

Rejected. It cannot return EQUIVALENT under the prompt's rule.

## Candidate 3 — equality saturation

1. Put both expressions in an e-graph. Apply a finite set of ring rules until saturation or a node limit. Return EQUIVALENT if they share an e-class.
2. Pseudocode: `merge(root_left, root_right)` is not done up front. Rewrite with commutativity, associativity, distributivity, and constants. EQUIVALENT only on a common class. Otherwise UNKNOWN, never EQUIVALENT by exhaustion of the rules.
3. Congruence closure plus rewriting, as in Willsey, Nandi, Wang, Flatt, Tatlock, and Panchekha, POPL 2021.
4. Sound for EQUIVALENT when every rule is sound. Incomplete. Not a counterexample procedure unless a separate evaluator finds one.
5. Proof obligation: each rule preserves the Mode A value, and the e-class merge is a congruence. Mode B needs a separate proof for each rule. The width-1 and width-2 traps already show that a Mode A rule can be illegal in Mode B.
6. E-graph size can grow without deciding the pair. Saturation is not polynomial identity.
7. Different architecture from Z3 and from expansion. The decision, when it succeeds, is still "a known rule set proved these two terms congruent." That is not a new decision procedure. A complete rule set for polynomials is as strong as expansion and usually encoded by it.
8. It could find a short proof of a shallow identity faster than a large expansion. The production rules already do that for twelve templates, and they abstain otherwise.
9. Non-equivalent pairs that no rule separates stay UNKNOWN. Distributivity both ways cycles unless a cycle guard exists. The optimizer already has that guard.
10. Falsifier: a pair expansion calls equivalent and saturation, with a stated rule set, never merges. That shows incompleteness, which the design already admits, so it cannot be the primary claim of a complete verifier.

Rejected. The distinctive step is a published e-graph, and the complete case collapses into expansion.

## Candidate 4 — falling-factorial canonical form modulo `2^w`

1. Expand the difference over `Z`, then reduce by the null polynomials of `Z/2^w Z` into the falling-factorial basis with the coefficient bounds stated by the retrieved eprint as Keller and Olson's canonical representation.
2. Pseudocode: `diff = expand(left) - expand(right)`; `canon = reduce_mod_null(diff, width)`; EQUIVALENT if every coefficient is 0; else search a witness or return NOT_EQUIVALENT after a concrete modular evaluation of a nonzero reduced form.
3. Carlitz 1964 and the falling-factorial null polynomials described in IACR eprint 2022/1364. The 1968 Keller and Olson paper was not opened; the claim of uniqueness is taken from that eprint, which cites it.
4. Sound for modular functional equivalence of polynomial expressions if the reduction matches that theorem. Not a procedure for non-polynomial operators, which this language does not have.
5. Proof obligation: the reduction does not change the function modulo `2^w`, and the only reduced form of the zero function is the zero coefficient vector. That obligation is a published theorem, not a theorem proved in this repository.
6. Multivariate reduction still pays the expansion cost, then extra divisibility bookkeeping. It can be slower than Z3 on short bit-vector queries, which the existing census finished in well under a second per pair.
7. It does not call Z3 or cvc5, and it is not integer expansion alone, because integer inequality is not modular inequality. The algorithm is still the published canonical form.
8. It could decide a wide Mode B pair whose domain exceeds 65536 without SMT. That would be an implementation advantage of a known method, not a new method. The gate requires the novelty to be distinguishable from prior work.
9. A bug in the `p`-adic valuation of `i!` accepts a nonzero wraparound function. High width and many variables exhaust memory before Z3 does.
10. Falsifier: any pair exhaustive search calls non-equivalent and the canonical form calls EQUIVALENT. Also, a benchmark where its median time is not lower than Z3 on the preregistered wide pairs would kill a performance claim. No such benchmark was run, because the novelty test already failed.

Rejected as a new method. It is the closest engineering pivot, and it is recorded as a pivot rather than implemented under a new name.

## Candidate 5 — a canonical diagram of the bit-vector function

1. Build a binary decision diagram, or an algebraic decision diagram, of the Mode B function of each expression. Compare roots.
2. Pseudocode: Shannon-expand on each bit of each variable; share identical subgraphs; EQUIVALENT if the roots are the same node.
3. Canonical boolean representations are a standard decision-diagram method. This session did not retrieve a separate Bryant paper, so no page citation is attached. The idea is not claimed as new, and it is not claimed as a retrieved theorem beyond the description above.
4. Sound and complete for a finite boolean encoding when the diagram finishes. Mode A is infinite, so the diagram is not a Mode A procedure.
5. Proof obligation: the node interprets the expression, and identical nodes denote the same function. That is the usual diagram invariant.
6. Worst case is exponential in the number of bits `w*k`, the same order as the domain. Sharing may help. It may also lose to bit-blasting inside Z3.
7. Different data structure from Z3's clauses and from polynomials. Not different mathematics from "compile the finite function to a canonical form."
8. Very small widths might be faster than process-startup cvc5. The existing in-process Z3 checks on the confirmatory set had median solver times around a few milliseconds. A diagram is unlikely to change a scientific conclusion at that scale, and that guess is not a measurement.
9. Multiplication of wide bit-vectors produces large diagrams. Malformed variable orders blow the diagram while SMT still answers.
10. Falsifier: any diagram EQUIVALENT answer whose concrete exhaustive check finds a difference. Performance falsifier: median time not below Z3 on a frozen small-width set. Not run.

Rejected. The step is a known canonical representation of a finite function, and the expected gain is not a justified new procedure.

## Decision matrix

Scores are 0, 1, or 2. They do not override the rejection reasons.

| Candidate | Soundness path | Distinct from prior work | Feasible here | Measurable gain | Independent check | Falsifiable | Reject? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 Expansion | 2 | 0 | 2 | 0, already shipped | 1, re-expand | yes | yes |
| 2 Random points | 0 for EQUIVALENT | 0 | 2 | 0, testing already failed | 0 | yes | yes |
| 3 E-graph | 1, incomplete | 0 | 1 | unclear | 1, replay rules | yes | yes |
| 4 Falling factorial | 2 if the cited theorem is implemented faithfully | 0 | 1 | possible, not a new algorithm | 1, second reduction | yes | yes |
| 5 Decision diagram | 2 on a finite domain | 0 | 1 | unlikely, unmeasured | 1, second diagram | yes | yes |

## Gate

- What exactly is new? Nothing that survives. Every EQUIVALENT path is expansion, a probabilistic test that cannot prove equivalence, equality saturation, a published modular canonical form, or a decision diagram.
- What is already known? The rows in `research/PRIOR_ART_MATRIX.md`.
- Which algorithmic step is different? None that is both different and justified as a contribution.
- Why should a difference matter? The only practical gap is Mode B pairs that are too large to enumerate and that integer expansion cannot decide. The published falling-factorial reduction addresses that gap and is not new.
- Correctness argument? Available for candidates 1 and 4 only by citing existing mathematics. Candidate 4's uniqueness proof was not re-proved here.
- What would disprove a novelty claim? Identifying the step in Schwartz, in the polynomial oracle, in the egg paper, or in the modular-canonical-form literature. That identification is the rejection.
- Is the difference supported by the literature review? The literature shows the methods. It does not show a hole that a fifth algorithm would fill.
- Can an experiment separate the method from the baselines? An experiment could time an implementation of candidate 4 against Z3. That would evaluate an implementation of prior work. It would not create a new method. The prompt says not to fabricate novelty, so that experiment was not run and no pairs were generated.

**Verdict of the gate: NO-GO.** No novel core is implemented. No confirmatory dataset is generated. Historical files stay as they were.

## Phase 4 internal adversarial notes

These are attacks on the rejected designs, listed so a later pivot does not repeat them.

- Candidate 1 at Mode B width 1: `x+y` and `x-y` are different integer polynomials and the same function modulo 2. Calling the integer result a modular equivalence is a false inequivalence, not a false equivalence. The oracle file already says this.
- Candidate 2: `(x-x)*y` versus `0` is equivalent, so random zeros teach nothing. `(x*x)-(x)` versus `0` over the integers is not equivalent, and unlucky zeros would be a false equivalence.
- Candidate 3: a distributivity rule applied in both directions cycles. The production optimizer already refuses a repeated rendered term.
- Candidate 4: forgetting `nu_p(i!)` accepts a null polynomial as nonzero or the reverse. A test would be `x(x-1)...(x-m+1)` modulo `2^w` for `m` large enough that the product is identically 0, compared with `0`.
- Candidate 5: mixing Mode A integers into a fixed bit width silently changes the question. The result contract would have to reject that input as UNSUPPORTED.
- Shared parser risk: every candidate that uses `parse_independent` inherits a parser bug. A certificate checker that walks the same AST nodes does not remove that risk. A checker that only sees coefficients still trusts the producer that built them.

No independent reviewer was available. This section is not an external review.
