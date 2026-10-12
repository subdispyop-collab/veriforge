# Wider canonical evaluation

Record `veriforge-canonical-wide-v1`. This is not a new theorem. The 57-pair study was not rewritten. Version `1.0.0`. Held-out file: 8 lines.

Protocol SHA-256 `65ad64b6d5275f402f4a736a6613ce99352cb4d22d61b81e9e9016ea81c249ca`, locked before the dataset. Dataset `datasets/canonical_wide_v1/cases.jsonl`, 105 lines, SHA-256 `4ca42c4ddfa73e26e74fa10077e56b237f18921662d26b8e0ea6eb1f9c941c82`. Raw rows `experiments/reports/canonical-wide-v1/cases.jsonl`. Summary `experiments/reports/canonical-wide-v1/summary.json`.

Python 3.12.3. Z3 `4.8.17`. cvc5 line `This is cvc5 version 1.3.2`. Term cap `256`. The ten `UNKNOWN` rows all say `term count 462 exceeds 256`. They were kept. `UNKNOWN` is not equivalence.

Initialization, excluded from per-case sums: Z3 `0.029187585998442955` seconds, cvc5 `0.01233195199893089` seconds.

## Ground truth

| Width | equivalent | non_equivalent | not_computed |
| --- | --- | --- | --- |
| 1 | 17 | 4 | 0 |
| 2 | 8 | 13 | 0 |
| 4 | 7 | 13 | 1 |
| 8 | 6 | 13 | 2 |
| 32 | 0 | 13 | 8 |

Width 32 has no exhaustive `equivalent` label. Eight rows are `not_computed`, including seven on which the canonical checker returned `EQUIVALENT`. Those seven are not scored as correct acceptances and are not in the false-rejection denominator.

## False equivalence

Denominator is ground-truth `non_equivalent`. Numerator is a claim of equivalence. Canonical, Z3, and cvc5 are the same counts.

| Slice | Numerator | Denominator | Wilson 95% |
| --- | --- | --- | --- |
| width 1 | 0 | 4 | `[0.0, 0.4898908364545973]` |
| width 2 | 0 | 13 | `[0.0, 0.22809537235419838]` |
| width 4 | 0 | 13 | `[0.0, 0.22809537235419838]` |
| width 8 | 0 | 13 | `[0.0, 0.22809537235419838]` |
| width 32 | 0 | 13 | `[0.0, 0.22809537235419838]` |
| control (1, 2, 4) | 0 | 30 | `[0.0, 0.11351339317396876]` |
| wide (8, 32) | 0 | 26 | `[0.0, 0.1287289218592153]` |
| all | 0 | 56 | `[6.938893903907228e-18, 0.06419393671876342]` |

The all-set lower endpoint is a floating-point residue. The numerator is 0.

## False rejection

Denominator is ground-truth `equivalent`. Numerator is a claim of non-equivalence. Canonical, Z3, and cvc5 match.

| Slice | Numerator | Denominator | Wilson 95% |
| --- | --- | --- | --- |
| width 1 | 0 | 17 | `[0.0, 0.1843181350088518]` |
| width 2 | 0 | 8 | `[0.0, 0.32440756488388023]` |
| width 4 | 0 | 7 | `[5.551115123125783e-17, 0.35433043506668743]` |
| width 8 | 0 | 6 | `[2.7755575615628914e-17, 0.3903342879021653]` |
| width 32 | 0 | 0 | null |
| control | 0 | 32 | `[0.0, 0.1071791982550706]` |
| wide | 0 | 6 | `[2.7755575615628914e-17, 0.3903342879021653]` |
| all | 0 | 38 | `[0.0, 0.09180986822558396]` |

Width 32 is an empty denominator, not a zero rate. Width 4, 8, and the wide-arm lower endpoints that are not `0.0` are floating-point residues of a zero numerator.

The degree-6 self-comparisons at widths 1 and 2 are ground-truth `equivalent` and canonical `UNKNOWN`. They are not false rejections. They are non-decisive.

## Decisive rate

Denominator is every row, including the term-cap rows.

| Slice | Canonical | Z3 | cvc5 |
| --- | --- | --- | --- |
| each width, 21 rows | 19/21, Wilson `[0.7108586092608176, 0.9734812325619255]` | 21/21, `[0.8453609810751531, 1.0]` | 21/21, same |
| control, 63 rows | 57/63, `[0.8073829893716311, 0.955616515723108]` | 63/63, `[0.9425288004111484, 1.0]` | 63/63, same |
| wide, 42 rows | 38/42, `[0.7793489419142897, 0.9623377511944261]` | 42/42, `[0.916201209134296, 0.9999999999999999]` | 42/42, same |
| all, 105 rows | 95/105, `[0.8335087237779633, 0.9474436901365668]` | 105/105, `[0.9647059230708901, 1.0]` | 105/105, same |

## Time

Per-case wall-clock seconds. `n` is 21 at each width, 63 on the control, 42 on the wide arm, and 105 overall.

| Clock | Width 8 sum / median | Width 32 sum / median | All sum / median |
| --- | --- | --- | --- |
| Canonical | `0.007149832003051415` / `0.00014261199976317585` | `0.006881995010189712` / `0.0001177240010292735` | `0.03505429602228105` / `0.00012999899990973063` |
| Z3 | `0.1518048509969958` / `0.0074258479980926495` | `0.26835986799778766` / `0.007192460998339811` | `0.8667877950138063` / `0.00631002900263411` |
| cvc5 | `0.09209144600390573` / `0.004039313000248512` | `0.19458908100205008` / `0.004334667999501107` | `0.5507287519940292` / `0.003986095998698147` |

Control sums: canonical `0.021022469009039924`, Z3 `0.44662307601902285`, cvc5 `0.26404822498807334`. Wide sums: canonical `0.014031827013241127`, Z3 `0.42016471899478347`, cvc5 `0.2866805270059558`.
