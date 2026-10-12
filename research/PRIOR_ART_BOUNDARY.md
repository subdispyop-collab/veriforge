# Prior-art boundary

Access date: 2026-10-12. This file does not replace `research/PRIOR_ART_MATRIX.md`. A source is cited only when its text was retrieved or when an earlier review in this repository recorded the bibliographic fields. Papers whose bodies were not opened are marked.

## Fetch log

Shell `curl` from this machine, one attempt each, all failed before any body was saved:

| URL | Error |
| --- | --- |
| `https://doi.org/10.1007/978-3-032-32519-8_20` | `OpenSSL SSL_connect: SSL_ERROR_SYSCALL` to doi.org:443, HTTP status 000 |
| `https://github.com/luigirinaldi/parabit` | `SSL_ERROR_SYSCALL` to github.com:443 |
| `https://github.com/luigirinaldi/cav` | `SSL_ERROR_SYSCALL` to github.com:443 |
| `https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.SAT.2025.4` | `SSL_ERROR_SYSCALL` to drops.dagstuhl.de:443 |
| `https://samuelcoward.co.uk/assets/pdf/Parabit.pdf` | `SSL_ERROR_SYSCALL` to samuelcoward.co.uk:443 |

The search tool still returned readable text for the Springer chapter page and for the author PDF URL. Those retrieved texts are the source of the ParaBit claims below. A direct fetch of the Dagstuhl page was also rejected as outside the network allowlist. The Berger et al. SAT 2025 paper body was not opened. Claims about that paper are only what the retrieved CAV 2026 chapter says about it.

## ParaBit, CAV 2026

- Citation, from the retrieved Springer chapter page: Rinaldi, L., Wickerson, J., and Coward, S. A Multi-width Parametric Bitvector Equivalence Solver. In Darulova, E., Lin, A.W., and Rümmer, P. (eds), Computer Aided Verification, CAV 2026, Lecture Notes in Computer Science, vol. 16682, Springer, Cham, pp. 380–402. First online 24 July 2026. DOI `10.1007/978-3-032-32519-8_20`. Open access. Affiliations on that page: Rinaldi and Coward at University College London; Wickerson at Imperial College London.
- The retrieved author PDF titles the authors as "Anonymous Anonymous". The Springer page names them. This note uses the Springer names.
- Problem: prove rewrite equivalences whose bitwidths are parameters, including several different width parameters in one problem, as in hardware rewriting.
- Language: BWLang. Width parameters attach to operands. Operators include `+`, `-`, division, multiplication, bitwise and/or/xor, shifts, `ite`, and bitwise negation, plus width expressions and preconditions on widths. Well-formed expressions wrap every intermediate result at a width. Division by zero and negative shifts are arbitrary in their semantics.
- Method: translate to modular arithmetic, then equality saturation over conditional axioms, then an Isabelle script. The tool is ParaBit. The chapter says some axioms are mechanized in Isabelle and some are not.
- What constant-width SMT cannot do, as stated there: Bitwuzla and cvc5 can decide bit-vector equivalences when the widths are constants. They do not take parametric widths.
- Closest prior solver, as stated there: Berger et al., bit-precise reasoning with parametric bit-vectors, SAT 2025, LIPIcs vol. 341, pp. 4:1–4:24, DOI `10.4230/LIPIcs.SAT.2025.4`. The Springer bibliography prints "Berger, Z., et al." The author PDF's reference list names Zohar, Niemetz, Preiner, Reynolds, Barrett, and Tinelli as the remaining authors. Their theory attaches a width to operators, so inputs and outputs share one width. The chapter says encoding a multi-width sum then requires case splits on zero-extend versus truncate.
- Reported result, Springer conclusion: ParaBit solved 87% of the problems that could be encoded in BWLang. The author PDF's conclusion says 86%. Both sentences were retrieved. They are not reconciled here.
- Author PDF section 6, prose that the table extractor did not scramble: comparison with the Berger solver they call PBV; 60 second CPU limit; 8 GB memory; ParaBit hit the memory limit on 15 benchmarks; PBV did not. Of 131 problems solved by ParaBit, Isabelle checked 116 certificates. Eight Hydra and three Industry proofs used axioms not yet mechanized. Three Alive certificates failed because of a translation error or a 5 minute Isabelle timeout. One Alive figure caption reads 62 problems, timeout 60 seconds, PBV 31 (50%), ParaBit 54 (87%), virtual best solver 57 (92%). The extracted Table 2 grid was column-scrambled, so those cells are not quoted.
- Stated limits: BWLang encodes fewer problems than PBV (no bit-vector comparisons, no data constraints such as "this value is a power of two", existential quantifiers are a poor fit for equality saturation). Some proofs need extra preconditions such as `(w+1)-w ≥ 1`. egg proof scripts can contain repeated steps; one proof exceeded 200,000 steps.
- Implementation pointer in the search snippet for `luigirinaldi/cav`: Rust source `luigirinaldi/parabit`, Isabelle 2025-2, and a PBV binary from Zenodo `10.5281/zenodo.15143242`. This shell could not open GitHub, so that repository was not inspected.

## Fixed-width SMT and the tools already in this repository

- Z3: de Moura and Bjørner, TACAS 2008, LNCS 4963:337–340, DOI `10.1007/978-3-540-78800-3_24`, from `docs/LITERATURE_REVIEW.md` (access 2026-10-09). VERIFORGE's production check is `verify_equivalence_timed`. Observed here again: Z3 4.8.17.
- cvc5: Barbosa et al., TACAS 2022, LNCS 13243:415–442, DOI `10.1007/978-3-030-99524-9_24`. The CAV 2026 bibliography repeats that DOI. Observed here again: cvc5 1.3.2. The historical census was not rerun.
- Bitwuzla: Niemetz and Preiner, CAV 2023, pp. 3–17, DOI `10.1007/978-3-031-37703-7_1`, from the CAV 2026 bibliography. An earlier census in this repository ran Bitwuzla 0.8.2. It was not rerun for this note.
- Parametric proofs inside SMT, bibliographic entries only, bodies not opened: Niemetz, Preiner, Reynolds, Zohar, Barrett, and Tinelli, CADE 2019, LNCS 11716:366–384, DOI `10.1007/978-3-030-29436-6_22`; same authors, Journal of Automated Reasoning 65(7):1001–1025, 2021, DOI `10.1007/s10817-021-09598-9`.
- Alive and Alive2 remain the LLVM peephole and IR tools in `docs/LITERATURE_REVIEW.md`. Alive2 was not installed and was not run. No score is stated. ParaBit's Alive suite is a benchmark set converted from parametric encodings, not an Alive2 execution.

## Equality saturation

Willsey, Nandi, Wang, Flatt, Tatlock, and Panchekha, egg, POPL 2021, DOI `10.1145/3434304`, retrieved earlier and cited again by the CAV 2026 chapter as the equality-saturation method ParaBit uses. A finite rule set for `+` `-` `*` does not become a new decision procedure by being placed in an e-graph. Completeness for integer polynomials returns to coefficient comparison.

## Polynomial functions modulo `2^w`

- Integer coefficient comparison is `veriforge/polynomial_oracle.py`. It decides the unbounded integer semantics. Equal polynomials agree modulo `2^w`. Unequal polynomials may still agree.
- The falling-factorial checker in `veriforge/falling_factorial.py` is an implementation of the canonical form that IACR eprint 2022/1364 attributes to Keller and Olson, Duke Mathematical Journal 35(4):835–838, 1968. That 1968 paper was not opened. The attribution is second-hand. The module does not state a new theorem. Its certificate checker recomputes Newton coefficients by forward differences.
- Measured already, not rerun here: on 57 preregistered Mode B pairs, that checker returned `EQUIVALENT` on 9/9 pairs where the integer comparison was the wrong semantics, with false equivalence 0/27, matching Z3 4.8.17 and cvc5 1.3.2. Summary SHA-256 `5f6fc25c5f25aed9836fa10edaab114b609b79a3cc65024e5465cf1ea93a3cde`.

## What is not a gap

A solver for multi-width parametric bit-vector rewrites, with equality saturation and Isabelle certificates, is the published ParaBit result. A solver for one fixed width on `+` `-` `*` is the combination already in this repository: Z3 or cvc5, the integer expansion, and the falling-factorial residues. Quantifying the same `+` `-` `*` identity over every width collapses to the integer identity, because a nonzero integer polynomial is not divisible by every power of two.
