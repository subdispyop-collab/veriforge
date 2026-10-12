# Method discovery report

Phases 0–10 of the method-discovery prompt were carried through on branch `cursor/method-discovery-7f34`, cut from `cursor/research-hardening-7f34` at `8ad58149d1ee1fcf7248cbf4d9e7618e66daec14`. Version remains `1.0.0`. `datasets/held_out/cases.jsonl` remains 8 lines. No novel procedure was implemented.

## A. What was actually discovered?

Nothing that qualifies as a new decision procedure was discovered.

Five candidates were written down and rejected before implementation:

1. Exact integer expansion. This is `veriforge/polynomial_oracle.py`.
2. Schwartz evaluation returned as `EQUIVALENT`. That reading is unsound. A zero sample does not prove identity.
3. Equality saturation with a finite ring rule set. The architecture is the published e-graph method (Willsey, Nandi, Wang, Flatt, Tatlock, and Panchekha, POPL 2021, DOI `10.1145/3434304`). Completeness collapses into expansion or stays incomplete.
4. Falling-factorial canonical form of polynomial functions modulo `2^w`. The retrieved IACR eprint 2022/1364 attributes uniqueness of bounded falling-factorial coefficients to Keller and Olson, Duke Mathematical Journal 35(4):835–838, 1968. That 1968 paper was not opened. Carlitz, Acta Arithmetica 9(1):67–78, 1964, DOI `10.4064/aa-9-1-67-78`, had its landing page retrieved and its body not opened. This is the closest engineering pivot: it would decide Mode B pairs too large to enumerate without calling Z3 or cvc5. It is published mathematics, so it was not implemented under a new name.
5. A binary or algebraic decision diagram of the Mode B function. Canonical finite-function diagrams are a known method. No Bryant paper was retrieved, so no page citation is attached, and the idea is not claimed as new.

The algorithmic difference that would have mattered for candidate 4 is the reduction of the integer difference by the null polynomials of `Z/2^w Z`, rather than coefficient comparison over `Z` or an SMT query. That reduction was not coded.

## B. Why is it different?

No surviving candidate is different in the sense the gate requires.

- Z3 (de Moura and Bjørner, TACAS 2008, LNCS 4963:337–340, DOI `10.1007/978-3-540-78800-3_24`, from the 2026-10-09 review) is the production verifier. Calling it again is the existing method.
- cvc5 (Barbosa et al., TACAS 2022, LNCS 13243:415–442, DOI `10.1007/978-3-030-99524-9_24`, PDF retrieved 2026-10-12) is a second SMT baseline. Agreement with Z3 is not a new proof.
- The polynomial checker expands to monomials and compares coefficients, with a 4096-term budget. Schwartz, JACM 27(4):701–717, 1980, DOI `10.1145/322217.322225`, describes that expansion as the direct form of identity testing. Candidate 1 is that checker.
- Alive2 (Lopes, Lee, Hur, Liu, and Regehr, PLDI 2021, DOI `10.1145/3453483.3454030`) judges LLVM IR, including poison and flags. It is not comparable to this `+` `-` `*` language. It was not installed and was not run. No score is stated.
- egg is equality saturation, which is candidate 3. Similarity: both rewrite terms. Difference from SMT: no theory solver. Difference from a new method: the paper already describes the technique, and a complete rule set for this fragment is polynomial identity.
- Randomized identity testing (Schwartz 1980; Zippel, EUROSAM 1979, and DeMillo and Lipton 1978 were named on a retrieved Wikipedia page and were not opened) proves inequivalence on a nonzero evaluation and does not prove equivalence on zeros.
- Carlitz 1964 and the Keller–Olson form, as attributed by the retrieved eprint, already decide polynomial functions modulo `p^e`. Similarity to the existing oracle: both start from polynomials. Difference: integer inequality is not modular inequality. That difference is prior work, not a contribution of this repository.

## C. What is proved and what is empirical?

No new theorem is proved in this repository.

Formal facts used only as citations, not re-proved here:

- Two polynomials over `Z` agree as functions when their coefficients match, for this operator set. That is the existing oracle’s argument.
- The retrieved eprint states that two integer polynomials define the same function modulo `p^e` exactly when their difference is a null polynomial, and it attributes a unique canonical form to Keller and Olson 1968. Uniqueness was not re-proved. The 1968 paper was not opened. Multivariate reduction was not derived here.
- A decision diagram’s canonicity was not proved here.
- A finite random sample does not prove universal equivalence.

Implemented safeguards from earlier work stay in version 1.0.0. They are not a new method. Z3 proof objects saved on the confirmatory-v2 pairs are solver terms. No external checker was run on them.

Empirical results from the 463-pair census and the 72-pair confirmatory-v2 run describe Z3 4.8.17 and cvc5 1.3.2. They were not rerun. They are not observations about a new method.

Unverified assumptions that this gate does not close: that a later implementer could code the falling-factorial reduction without error; that such an implementation would be faster than Z3 on some class; that a diagram would share nodes enough to beat bit-blasting. None of those was measured.

## D. What did the experiments demonstrate?

The only command executed for this gate is `python3 scripts/method_discovery_analysis.py`. Exit code 0. It printed `pair_count` 0, `false_equivalence` null, and `primary_hypothesis` `not_tested`.

H_new, locked in `research/PREREGISTRATION.md` before any new pair existed, asked whether a procedure that does not call Z3, does not call cvc5, and does not decide by integer expansion has a lower false-equivalence count than `verify_equivalence_timed` on a frozen family-clustered set. Status: **not tested**. Denominator: none. Effect size: none. Uncertainty: a Wilson interval was not computed, because an empty denominator is not a zero rate.

Failures of the scientific claim, not of a solver: every candidate failed the novelty or soundness gate in `research/CANDIDATE_METHODS.md`. The internal adversarial notes in that file are by the same author. They are not an independent audit.

Historical false-equivalence counts (0/96 on the census, 0/33 on confirmatory-v2) stay attached to those old denominators. They are not results of H_new. H3 on confirmatory-v2 remains unresolved and was not reopened. No families were added.

## E. Can another researcher reproduce it?

Start from commit `8ad58149d1ee1fcf7248cbf4d9e7618e66daec14` and the files named in `research/REPRODUCIBILITY.md`.

```text
python3 scripts/method_discovery_analysis.py
```

Expected stdout is the JSON in `experiments/reports/method-discovery/analysis.json`. The script exits 2 if `research/PREREGISTRATION.md` no longer hashes to `d0b112064b93acb4b19aecd62cac865eedb2f653a1a9aade65ee10d2255869cb`, if the gate is not NO-GO, or if `new_pairs_authorized` is not false.

Observed environment at the audit, not a new install: Python 3.12.3, Z3 4.8.17, cvc5 line `This is cvc5 version 1.3.2`. Alive2: not installed.

Dataset fingerprint for a new method: null. `research/method_discovery_dataset_manifest.json` records zero pairs. Held-out file: `datasets/held_out/cases.jsonl`, 8 lines, not rewritten.

Configuration: `research/method_discovery_config.json` (`implemented: false`, `method_id: null`, `new_module: null`).

## F. What remains incomplete?

Environment failures, recorded and not retried in this gate:

- GitHub Actions was not run. `github.com:443` fails with `SSL_ERROR_SYSCALL` from this machine.
- mutmut, `z3-solver==5.1.0.0`, and `hypothesis==6.168.5` remain uninstalled. Earlier one-shot failures are in the hardening audit. This gate does not depend on them.
- Alive2 is not installed.
- The 1968 Keller and Olson paper, the Carlitz article body, the Zippel paper, and the DeMillo and Lipton paper were not opened. No Bryant page was retrieved.

Algorithmic and process gaps, which are the reason for NO-GO rather than a download failure:

- No candidate survived. Nothing novel was implemented.
- No certificate format and no independent validator were built.
- No confirmatory dataset, no raw per-case rows, and no new-method tests exist.
- Existing pytest was not rerun for this gate.
- The offline Podman image from the previous branch runs the old assurance script. It is not a run of a new method.
- No independent reviewer was available. Phase 4 is an internal review.

## G. Final research verdict

**No defensible novel contribution established.**

The gate required a core step that is not Z3, not cvc5, not the existing polynomial checker, not a finite sample treated as proof, and not a renamed published method. None of the five candidates met that test. H_new was therefore not run. The measurements that do exist belong to the earlier verifier study and are not converted into a novelty claim.
