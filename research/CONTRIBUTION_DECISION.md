# Contribution decision

## Research question

Does an independently audited arithmetic rewrite check reduce undetected semantic defects relative to a single symbolic path, and what does the extra check cost?

The SMT half of that question was not answerable on this host. The executable secondary question was whether a larger random-and-boundary test budget reduces false equivalences on the new held-out set.

## Precise contribution

An engineering and empirical study of one restricted arithmetic fragment (`+`, `-`, `*`, unary `+`/`-`, mathematical integers, unsigned wrap). The code adds a second parser, a second concrete evaluator, a polynomial identity check for integers, and exhaustive enumeration for bit-vectors inside an explicit budget. It does not add a new decision procedure for general programs.

## Difference from the closest prior work

Alive and Alive2 already discharge rewrite equivalence with SMT and produce counterexamples. Translation validation already checks each candidate rather than the whole compiler. Property-based testing already searches for witnesses. The implementation difference is the small grammar, the unsigned-versus-integer mode split, and the recorded budgeted exhaustive oracle. That is an application of known methods.

## Established techniques

SMT equivalence queries, counterexample checking, mutation fixtures, Wilson intervals, family-clustered held-out splits, and polynomial identity for the ring of integer polynomials.

## What is genuinely new

Nothing in this record is claimed as a new algorithm or as a new empirical law. The measured statements are about this dataset only. See `research/RESULTS_AND_ANALYSIS.md`.

## What would falsify the claims that are made

- A held-out non-equivalent pair that budget 10,000 testing calls undistinguished, if someone reports `r(10000) < r(10)` from these files. The files show `0/54` at both budgets, so the inequality is false.
- A production-rule reduction that the oracle says is non-equivalent, if someone reports zero false accepts. The held-out rule baseline accepted 0 non-equivalent pairs.
- An evaluator disagreement on the zero or top-of-range assignment sweep. The sweep recorded 0 disagreements.
- A Z3 comparison number. None was produced.

## What the search could not establish

Whether a 2024–2026 paper already combines exhaustive unsigned checking with a second parser for this grammar. The network block is recorded in `research/LITERATURE_REVIEW.md`. The project is positioned as a rigorous engineering study with one preregistered negative testing result, not as a novel verifier.
