# Method discovery report

The procedure that was built is an implementation of the falling-factorial canonical form for unsigned wraparound. The univariate shape is the representation IACR eprint 2022/1364 attributes to Keller and Olson, Duke Mathematical Journal 35(4):835–838, 1968. That 1968 paper was not opened. The attribution is second-hand. No new theorem is claimed.

The new research is the preregistered question, the 57-pair dataset, and the measured answer. Protocol SHA-256 `e5cb120f983a8df481b1db2c52aa92d8293eb80e94251b1e536c8fa71646cd00` was written before any pair. Dataset SHA-256 `e7de7560c6fa46f23038d6f2ea3701d867d3114fdd7d1b323cf672c6f4a5f37a`. Version `1.0.0`. Held-out file: 8 lines.

## A. What was actually discovered?

On this frozen set, integer coefficient comparison is the wrong semantics for 9 of 57 unsigned pairs, and the certificate-backed checker decided all 9 of those pairs `EQUIVALENT`. Z3 4.8.17 and cvc5 1.3.2 also decided them `equivalent_within_model`. All three procedures had false equivalence 0/27 and were decisive on 57/57 pairs. The checker's wall-clock sum on these small expressions was `0.007584139995742589` seconds, against `0.3974383819877403` seconds for the Z3 call and `0.2561598999782291` seconds for the cvc5 process.

The algorithmic step is not a new reduction. `decide_mode_b` expands the integer difference, converts monomials with Stirling numbers of the second kind into the product of falling factorials, and reduces each coefficient modulo `2^{max(0, w - sum v_2(alpha_i!))}`. `EQUIVALENT` is returned only after `check_certificate` recomputes those coefficients from forward differences of integer evaluations. `NOT_EQUIVALENT` is returned only after `reference_evaluator.evaluate` confirms a witness. Mode A returns `UNSUPPORTED`.

## B. Why is it different?

It is different from the integer polynomial checker because unequal integer polynomials can agree modulo `2^w`. That is the primary subset: polynomial verdict `counterexample`, exhaustive label `equivalent`, 9 pairs, all at width 1.

It is different from Z3 and from cvc5 because it does not call either solver. On this dataset the three answers matched: 30 equivalent decisions and 27 non-equivalent decisions. Agreement is not a proof that the translation into Z3 or cvc5 is correct, and it is not a proof that the Stirling conversion is correct. The checker's separate forward-difference pass is the certificate check for `EQUIVALENT`.

Alive2 was not run. It judges LLVM IR, including poison and flags, so it is not a baseline for this expression language. No score is stated.

The closest published account is the retrieved eprint's Theorem 2, cited there as Keller and Olson, together with its Theorem 1 on null polynomials. The code's several-variable step is the product basis with the same factorial divisibility. The eprint statement that was retrieved is univariate. The product step is written in `research/NEW_METHOD_SPEC.md` and is not given a new name.

## C. What is proved and what is empirical?

The soundness argument tied to the code is in `research/NEW_METHOD_SPEC.md`: Newton coefficients in the falling-factorial basis are unique over `Z`, a falling factorial of `m` consecutive integers is divisible by `m!`, and the residue test is necessary and sufficient for the integer polynomial to be divisible by `2^w` at every integer point. That argument is not a new theorem and not a re-proof of the 1968 paper.

What the unit tests checked, before the study script ran: zero, one, nested cancellation, the width-1 literal boundary, wrap of `(a + a)` versus `(a * 2)`, integer-versus-modular traps, malformed residues and shifted coefficients, Mode A rejection, and no false `EQUIVALENT` against exhaustive search on a fixed grid of small expressions. `python3 -m pytest tests/unit/test_falling_factorial.py -q` exited 0.

What the study measured is in section D. It is one run of `scripts/run_canonical_form_study.py`.

## D. What did the experiments demonstrate?

Primary, pairs: 9/9 canonical `EQUIVALENT` where integer comparison was the wrong semantics. Wilson 95% `[0.7008549515804559, 1.0]`. Primary, families: 9/9, same interval, and each family contributes only the width-1 pair. The interval is wide because the denominator is 9. It does not estimate a rate for widths other than 1. Widths 2 and 4 of those families are outside the primary denominator because exhaustive search labels them non-equivalent.

False equivalence: canonical, Z3, and cvc5 are each 0/27, Wilson 95% `[0.0, 0.12455502974186705]`. By width the counts are 0/3, 0/12, and 0/12. Where the script's lower endpoint is `5.551115123125783e-17` or `2.7755575615628914e-17`, the numerator is 0 and the endpoint is a floating-point residue.

False rejection: each procedure 0/30, Wilson 95% `[0.0, 0.11351339317396876]`. By width: 0/16, 0/7, 0/7.

Decisive rate: each procedure 57/57, Wilson 95% `[0.9368611651470209, 0.9999999999999998]`.

Time, n=57, initialization excluded: canonical wall sum `0.007584139995742589`, median `0.00012991299809073098`; Z3 wall sum `0.3974383819877403`, median `0.006064753997634398`; Z3 solver-only sum `0.1880304170117597`, median `0.002636724999319995`; cvc5 wall sum `0.2561598999782291`, median `0.003891644002578687`. Z3 init `0.012033996001264313`. cvc5 init `0.006565760999365011`.

No pair was dropped. No budget was retuned. No false `EQUIVALENT` occurred, so the release block for a confirmed false equivalent did not fire.

## E. Can another researcher reproduce it?

Protocol file `research/PROTOCOL_CANONICAL_FORM.md`. Lock `research/protocol_canonical_form.json`. The runner aborts if those hashes differ.

```text
env -u PYTHONPATH -u LD_LIBRARY_PATH \
  PYTHONPATH=/home/ubuntu/py-z3:/workspace \
  Z3_LIBRARY_PATH=/home/ubuntu/al-root/usr/lib64 \
  python3 scripts/run_canonical_form_study.py
```

That command was executed once after the hash and after the unit tests. It wrote the 57 pairs and the report files above. Expected versions from this machine: Python 3.12.3, Z3 4.8.17, cvc5 `This is cvc5 version 1.3.2`. Re-running the script rewrites the same templates; it does not authorize new families.

Unit tests:

```text
env -u PYTHONPATH \
  PYTHONPATH=/home/ubuntu/py-clean/usr/lib/python3/dist-packages:/workspace \
  python3 -m pytest tests/unit/test_falling_factorial.py -q
```

Exit code 0 on this machine.

## F. What remains incomplete?

The primary denominator contains only width 1. Nothing in the measurement estimates the same rate at width 8, 32, or on expressions that hit the term budget. Those budgets were not stressed by this dataset: decisive rate 57/57 is the rate on expressions the protocol chose to be small.

The 1968 Keller and Olson paper, the Carlitz article body, Zippel, and DeMillo and Lipton were not opened. Alive2 is not installed. GitHub Actions was not run: `github.com:443` fails with `SSL_ERROR_SYSCALL`. `z3-solver==5.1.0.0`, `hypothesis==6.168.5`, and mutmut remain uninstalled from earlier fetch failures. The full historical pytest suite was not rerun for this study. The nine unit tests of the new module were run.

No external proof checker was applied to Z3's proof objects. The certificate checker is the forward-difference pass in `veriforge/canonical_certificate.py`, not a published proof assistant.

The earlier NO-GO writeup on `cursor/method-discovery-7f34` remains history. This branch implements the procedure that writeup refused to call new, because the order was to build it and measure this question.

## G. Final research verdict

**A technically useful implementation without a demonstrated novel method.**

The representation is the Keller–Olson form as attributed second-hand in the retrieved eprint, extended in code to a product basis by the divisibility argument in the spec. The measured answer on the preregistered 57 pairs is: certificate-backed `EQUIVALENT` on 9/9 pairs where integer coefficient comparison was the wrong semantics; false equivalence 0/27 for the checker, Z3 4.8.17, and cvc5 1.3.2; decisive rate 57/57 for each; canonical wall sum `0.007584139995742589` seconds against solver wall sums `0.3974383819877403` and `0.2561598999782291` seconds on this small set.
