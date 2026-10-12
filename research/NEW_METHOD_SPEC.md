# Specification status

No new method is specified for implementation. The gate in `research/CANDIDATE_METHODS.md` is NO-GO. This file records the semantics a new method would have had to meet, and the obligations that were not discharged for any candidate.

## 3.1 Semantics that already exist

The language is integer literals, variables, parentheses, binary addition, subtraction, and multiplication, and unary plus and minus.

Mode A evaluation is the usual evaluation in `Z`. Equivalence means `eval(left, a) = eval(right, a)` for every integer assignment `a`.

Mode B evaluation at width `w` maps each variable and each legal literal into `{0, ..., 2^w-1}` and reduces every operation modulo `2^w`. Equivalence means equality for every assignment in that box. A literal outside the box is unsupported input, not a wrapped value.

Unary plus is the identity. Unary minus in Mode A is negation in `Z`. Unary minus in Mode B is `0 - x` modulo `2^w`.

These two equivalences are different relations. A method that returns one answer for both without naming the mode is incorrect.

## 3.2 Result contract that was required

Any method that had passed the gate would have had to return only:

- `EQUIVALENT` with a certificate checked by code that does not share the producer's algebraic steps, or with a complete decision argument written for that mode.
- `NOT_EQUIVALENT` only after the reference evaluator confirms a concrete assignment.
- `UNKNOWN` when the argument is unfinished.
- `TIMEOUT` when a budget stops the search.
- `UNSUPPORTED` when the syntax or the mode is outside the claim.
- `ERROR` on an internal failure.

No candidate could attach `EQUIVALENT` to a certificate simpler than the decision procedure itself without becoming one of the rejected designs. The existing Z3 proof objects are solver terms. No external checker was run on them. They are not a certificate format for a new method.

## 3.3 Correctness argument

There is no new theorem. The integer case is coefficient comparison. The modular case is the published theory of polynomial functions on `Z/2^w Z`, cited in `research/PRIOR_ART_MATRIX.md`, and it was not re-proved or implemented.

Gaps, stated rather than closed:

- This repository does not contain a proof of uniqueness of the falling-factorial canonical form. The retrieved eprint attributes it to Keller and Olson 1968, which was not opened.
- Multivariate details of that reduction were not derived here.
- A decision diagram's canonicity was not proved here.
- Random evaluation does not prove equivalence.

## 3.4 Independent validator

No certificate format is defined, because no method was accepted. A validator that calls Z3, cvc5, or `polynomial_compare` would not be an independent checker of a new method. It would be a baseline.

## What this file does not authorize

It does not authorize new production rules, a new semantic mode, a change to `datasets/held_out/cases.jsonl`, or a version bump.
