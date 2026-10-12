# Research gap candidates

Phases 1–4 of the original-research mission. Phase 5 was not started. No file under `veriforge/` was edited. Version remains `1.0.0`. `datasets/held_out/cases.jsonl` remains 8 lines. Historical summaries were not rewritten.

Branch `cursor/research-gap-7f34` from `7070eb60b70423cd73d4a2daed67f2b97e1621fe`. The prior-art matrix is `research/PRIOR_ART_BOUNDARY.md`. This file is the ranking and the preliminary evidence.

## Phase 1 — what is already on record

Verified by re-execution in this phase, without writing over old reports:

- `python3 scripts/method_discovery_analysis.py` exited 0 and printed gate `NO-GO`, `pair_count` 0, `false_equivalence` null, protocol SHA-256 `d0b112064b93acb4b19aecd62cac865eedb2f653a1a9aade65ee10d2255869cb`. H_new remains not tested.
- `python3 -m pytest tests/unit/test_falling_factorial.py -q` exited 0. The output was nine passing dots.
- Z3 `4.8.17` and cvc5 `1.3.2` still load. cvc5's version text includes the compile line `Jun 28 2026 22:24:21`.
- Protocol `research/PROTOCOL_CANONICAL_FORM.md` still hashes to `e5cb120f983a8df481b1db2c52aa92d8293eb80e94251b1e536c8fa71646cd00`. Canonical summary SHA-256 `5f6fc25c5f25aed9836fa10edaab114b609b79a3cc65024e5465cf1ea93a3cde`. Confirmatory-v2 summary SHA-256 `c845f25366480b15d81cb2c4e5b36f4200807b989f48853bde38227564d4f64b`. Held-out SHA-256 `36e4218e8026320a8d7988721a8051c286a980e7876a1ad226d10ef1ba866063`.

Not re-executed, so not freshly verified: the 463-pair census, confirmatory-v2, the ablation, the Z3 proof dump, and the offline image. Their files are unchanged. H3 on confirmatory-v2 stays unresolved. The NO-GO gate stays a decision not to claim a new algorithm, not a proof that none exists.

## Phase 2 — boundary

The matrix is in `research/PRIOR_ART_BOUNDARY.md`. The short form:

| Proposal that would be easy to name | What already exists | Evidence |
| --- | --- | --- |
| Multi-width parametric bit-vector equivalence | ParaBit, CAV 2026, DOI `10.1007/978-3-032-32519-8_20` | Springer chapter and author PDF retrieved. GitHub and the DOI redirect failed from this shell. |
| Parametric bit-vectors inside SMT | Berger et al., SAT 2025, as cited by that chapter; Niemetz et al. 2019 and 2021, bibliographic entries only | Berger's paper body was not opened. |
| Fixed-width `+` `-` `*` modulo `2^w` | Z3, cvc5, and the falling-factorial checker | 57-pair study already run. False equivalence 0/27 for each. |
| Same identity for every width | Integer polynomial comparison | A nonzero polynomial is not null modulo every `2^w`. |
| Equality saturation as the decision method | egg, POPL 2021, and ParaBit's use of it | Already rejected in `research/CANDIDATE_METHODS.md`. |
| Isabelle-checked certificates for parametric rewrites | ParaBit's certificate path | 116 of 131 solved problems checked, from the author PDF prose. Not re-run here. |

## Phase 3 — candidates, ranked

Rank is by whether a gap is actually open, then by whether a small experiment could kill it. None is assumed novel.

### 1. Do not build a multi-width parametric solver

Question that looks open until the 2026 paper is read: can VERIFORGE prove a rewrite for every width, or for several widths in one expression?

Hypothesis that fails: the `+` `-` `*` fragment has no published parametric decision procedure.

Domain if it were real: either one width quantified over all `w`, or BWLang's operand-tagged widths.

Why it is not open: for one width on this operator set, "for all `w`" is integer identity, already decided by `polynomial_oracle.py` when expansion finishes. For several widths inside one expression, ParaBit already translates to modular arithmetic, searches an e-graph, and emits Isabelle certificates. The chapter's own comparison point is Berger et al. 2025, not an empty field.

Correctness obligation that would have been required: preconditions on widths imply the modular identity, checked by a proof assistant. ParaBit states that obligation and does not finish it for every axiom.

Baselines: ParaBit and the PBV solver. They were not installed here. GitHub fetch failed.

Cheap disproof: the literature search itself. It succeeded through the search tool.

Negative outcome, accepted: this is not a VERIFORGE contribution. Reimplementing BWLang would be a port.

Prior art still missing only if someone wanted to re-evaluate ParaBit, not if someone wanted to claim the problem is unsolved. The missing pieces are the unopened Berger paper and the unfetched GitHub tree.

### 2. The concrete weakness is the falling-factorial budget, and closing it is not a new method

Question: on unsigned `+` `-` `*` at one fixed width, where does `decide_mode_b` return `UNKNOWN` while Z3 still decides?

Hypothesis, falsifiable and already stressed below: every pair Z3 decides inside 5 seconds is also decided by the canonical checker. The probes falsify that hypothesis.

Mechanism that would remove the `UNKNOWN`: evaluate Newton differences without building the monomial expansion, or raise the term cap. The checker already uses forward differences when the grid fits. The producer stops first, at 256 monomials or at 6 variables. Skipping the monomial basis is still Newton interpolation, which the retrieved eprint describes. It is not a new theorem.

Correctness obligation: the same residue test as `research/NEW_METHOD_SPEC.md`. No new obligation appears.

Baselines: `polynomial_oracle.py` with budget 4096, and Z3 4.8.17.

Cheap disproof of a novelty claim: name the step as Newton interpolation or as a larger budget. That naming is available now, so the candidate does not survive as research.

Expected limitation, observed: `UNKNOWN` is an abstention. It did not become a false `EQUIVALENT` in these probes.

### 3. A portfolio that calls the canonical checker and then Z3

Question: does calling the falling-factorial checker before Z3 decide pairs Z3 misses, or cut false equivalences?

Hypothesis: the checker decides a pair Z3 does not, without a false `EQUIVALENT`. Nothing in the 57-pair study or in the probes below shows such a pair. The probes show the opposite abstention.

This would be a scheduling policy over two existing procedures. Niemetz, Preiner, Reynolds, Zohar, Barrett, and Tinelli already published parametric bit-vector work inside SMT; those papers were not opened, so this note does not claim they do or do not discuss portfolios. The local evidence is enough to drop the candidate: no measured pair is decided only by the checker.

### 4. External Isabelle certificates for the fixed-width residue test

Question: can the Newton certificate be checked in Isabelle rather than in `canonical_certificate.py`?

That is a proof-engineering task on mathematics already attributed to Keller and Olson. ParaBit already shows the shape of an Isabelle reconstruction for a richer modular theory. A local Python checker already recomputes the coefficients. A second checker in another language does not create a decision procedure. Ranked last.

## Phase 4 — preliminary probes

Script `scripts/gap_preliminary.py`. Output `experiments/reports/gap-preliminary/probe.json`. These rows were not preregistered and are not a confirmatory set. They were chosen to look for abstention and disagreement, including cases where the canonical checker is the weaker tool. Z3 is `verify_equivalence_timed` at the default 5 second budget. The integer column is `polynomial_compare` with term budget 4096.

| Probe | Width | Canonical | Integer polynomials | Z3 |
| --- | --- | --- | --- | --- |
| `(a+a)` vs `0` | 1 | `EQUIVALENT` | `counterexample` | `equivalent_within_model` |
| `(a+a)` vs `0` | 2, 4, 8, 32 | `NOT_EQUIVALENT` | `counterexample` | `counterexample_found` |
| `(a*(a-1))` vs `0` | 1 | `EQUIVALENT` | `counterexample` | `equivalent_within_model` |
| `(a*(a-1))` vs `0` | 4 | `NOT_EQUIVALENT` | `counterexample` | `counterexample_found` |
| `(a*(a-1))*(b*(b-1))*(c*(c-1))` vs `0` | 1 | `EQUIVALENT` | `counterexample` | `equivalent_within_model` |
| same product | 4 | `NOT_EQUIVALENT` | `counterexample` | `counterexample_found` |
| `(a+b+c+d+e+f+g)` vs `0` | 1 | `UNKNOWN` (7 variables, cap 6) | `counterexample` | `counterexample_found` |
| degree-6 product of `(a+b+c+d+e+f)` vs itself | 4 | `UNKNOWN` (462 terms, cap 256) | `equivalent` | `equivalent_within_model` |
| that product vs `0` | 4 | `UNKNOWN` (462 terms) | `counterexample` | `counterexample_found` |

The width-1 rows repeat the known fact that integer comparison is the wrong semantics for wraparound. Z3 agrees with the canonical checker on those rows. They are not a new gap.

The last three rows are the weakness. The canonical procedure abstains on a non-equivalent seven-variable sum that Z3 rejects, and on a syntactically identical degree-6 product that both the integer expansion and Z3 accept. Detail strings in the JSON are `variable count 7 exceeds 6` and `term count 462 exceeds 256`. No timeout occurred. No false `EQUIVALENT` occurred.

That weakness is in this implementation's caps. It is not evidence that Z3, cvc5, or ParaBit lack a capability. ParaBit was not run. cvc5 was not run on these probes. Alive2 was not run.

## Judgment

No candidate survived as a research gap that is both open and distinct from ParaBit, from SMT at a fixed width, and from Newton reduction modulo `2^w`. The mission's instruction for that outcome is to report it rather than manufacture an advantage. Phase 5 was not started.
