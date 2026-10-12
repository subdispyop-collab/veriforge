# Specification of the unsigned canonical-form checker

This is an implementation of a published representation, not a new theorem. The univariate canonical form is the one IACR eprint 2022/1364 attributes to Keller and Olson, Duke Mathematical Journal 35(4):835–838, 1968. That 1968 paper was not opened. The attribution is second-hand. The eprint's Theorem 1, which it traces to Singmaster's argument, says a polynomial is null modulo `p^e` exactly when each falling-factorial coefficient of `(X)_i` is divisible by `p^{max(e - v_p(i!), 0)}`. Its Theorem 2, cited there as Keller and Olson, chooses the representative with `0 ≤ c_i < p^{e - v_p(i!)}` below the first null falling factorial.

Mode A is not decided here. `decide_mode_b` returns `UNSUPPORTED` when the configuration is Mode A. The integer polynomial checker remains the Mode A procedure.

## Domain

Unsigned width `w ≥ 1`. Expressions built from integer literals, variables, parentheses, binary `+` `-` `*`, and unary `+` `-`. A Mode B literal outside `[0, 2^w - 1]` is `UNSUPPORTED`. The function decided is the integer polynomial reduced modulo `2^w`.

Limits fixed in `veriforge/falling_factorial.py` and in `research/PROTOCOL_CANONICAL_FORM.md`: term budget 256, certificate grid budget 4096, syntactic degree at most 12 in each variable, at most 6 variables, timeout 5 seconds. Crossing a size budget returns `UNKNOWN`. Crossing the clock returns `TIMEOUT`. Neither is an equivalence.

## Result contract

`veriforge.falling_factorial.CanonicalStatus`:

- `EQUIVALENT` only from the branch that runs after `canonical_certificate.check_certificate` returns `accepted` and `all_residues_zero`. There is no other return of that status.
- `NOT_EQUIVALENT` only when `reference_evaluator.evaluate` reports different Mode B values on the witness.
- `UNKNOWN` when a budget stops the argument, including when the checker cannot recompute a zero certificate.
- `TIMEOUT` when the clock stops the argument.
- `UNSUPPORTED` for Mode A, rejected syntax, and illegal literals.
- `ERROR` when the checker disagrees with the produced coefficients, or a nonzero residue does not confirm. `ERROR` is not rewritten as `EQUIVALENT`.

## Producer

`_expand` writes the difference in the monomial basis over `Z`. `_to_falling` converts each monomial with Stirling numbers of the second kind, using `x^n = sum_k S(n, k) (x)_k`, and the product of those identities for several variables. `_certificate` stores, for every multiindex in the syntactic degree box, the integer coefficient, the modulus, and the residue.

The modulus is `2^{max(0, w - sum_i v_2(alpha_i!))}`. It is computed by `canonical_certificate.canonical_modulus`. For one variable and `v_2(i!) < w`, this is the eprint bound on the falling-factorial coefficient. When the valuation is at least `w`, the modulus is `1` and the only residue is `0`, which is the eprint's statement that `(X)_i` itself is then a null polynomial.

## Why the residues decide the wraparound function

This is the argument the code relies on. It is not claimed as a theorem of this repository, and the multivariate sentence is not a sentence of the retrieved eprint, which is univariate.

1. Products of falling factorials are a basis of `Z[x_1, ..., x_k]`. The Stirling change of basis is triangular with integer inverse, so each integer polynomial has one integer coefficient vector `b_alpha` in that basis. `_to_falling` computes that vector. The checker recomputes the same number as `Δ^alpha f(0) / prod_i (alpha_i!)`.
2. For every integer `x` and every `m ≥ 0`, the falling factorial `(x)_m` is divisible by `m!`, because it is a product of `m` consecutive integers. A product over variables is therefore divisible by `prod_i (alpha_i!)`.
3. If `v_2(b_alpha) ≥ max(0, w - sum_i v_2(alpha_i!))`, every integer value of that term is divisible by `2^w`. That is `b_alpha % modulus == 0` in `_certificate`.
4. Conversely, if `f` is divisible by `2^w` at every integer point, every forward difference `Δ^alpha f(0)` is divisible by `2^w`. The Newton coefficient is that difference divided by `prod_i (alpha_i!)`, so the same valuation bound holds.
5. Therefore every canonical residue is zero if and only if the two expressions define the same function on the unsigned `w`-bit box. `EQUIVALENT` additionally requires the checker to recompute those residues from evaluations, not from the Stirling table.

## Checker

`check_certificate` evaluates the integer difference on the syntactic grid `{0, ..., d_i}` and applies the forward-difference formula. It rejects a certificate whose degree box, modulus, raw coefficient, or residue differs. A residue that was edited, and a raw coefficient shifted by the modulus, are both rejected. The checker does not multiply polynomials and does not build Stirling numbers, so the check is a different and smaller procedure than the search.

## Witness

A nonzero residue has a minimal multiindex `alpha` in the product order. At the integer point `alpha`, every other basis term that can be nonzero is componentwise smaller, and those smaller residues are zero, so they contribute multiples of `2^w`. The remaining value is `b_alpha * prod (alpha_i!)`, which is not divisible by `2^w` precisely because the residue is nonzero. The polynomial function modulo `2^w` depends only on each coordinate modulo `2^w`, because `(x + 2^w)^n - x^n` is divisible by `2^w`. The witness passed to the reference evaluator is `alpha_i mod 2^w`. If that evaluation does not separate the expressions, the status is `ERROR`.

## What is not claimed

No new null-polynomial theorem. No claim that the procedure is faster than Z3 or cvc5. No claim about LLVM, Alive2, division, shifts, or memory. The measured question is the one in `research/PROTOCOL_CANONICAL_FORM.md`.
