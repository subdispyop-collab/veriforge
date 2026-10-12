# Degree-7 canonical evaluation

Record `veriforge-canonical-degree7-v1`. This is not a new theorem. The 57-pair study and the 105-row study were not rewritten. Version `1.0.0`. Held-out file: 8 lines.

Protocol SHA-256 `6ce6df1d90998fc38ed52f78da5edef49b8a06b7e85601644fff656be74564b3`, locked before the dataset. Dataset `datasets/canonical_degree7_v1/cases.jsonl`, 20 lines, SHA-256 `d6bf6fa8fe76f24c7d64d6b460419b15d26488645445366ed0f0abdf615683a1`. Raw rows `experiments/reports/canonical-degree7-v1/cases.jsonl`. Summary `experiments/reports/canonical-degree7-v1/summary.json`.

Python 3.12.3. Z3 `4.8.17`. cvc5 line `This is cvc5 version 1.3.2`.

## Cap and term counts

The runner measured these counts on the template expressions:

| Degree | Monomial terms | Falling-factorial terms |
| --- | --- | --- |
| 6 | 462 | 923 |
| 7 | 792 | 1715 |

Term cap `1715`. Certificate grid budget `262144`, the syntactic box `8^6` of the degree-7 product. No row exceeded either budget. `canonical_nondecisive.count` is 0. `UNKNOWN` is not equivalence, and `TIMEOUT` is not equivalence.

Initialization, excluded from per-case sums: Z3 `0.011736959000700153` seconds, cvc5 `0.007220929997856729` seconds.

## Ground truth

Each degree-width cell has two rows: the product compared with itself, and the product compared with `0`.

Widths 1 and 2 are exhaustive (`2^(w*6)` is 64 and 4096). The self row is `equivalent` and the zero row is `non_equivalent`. Widths 4, 8, and 32 have domains above 65536. The zero row has a confirmed counterexample. The self row is `not_computed`, because the sample does not find a difference and absence of a witness is not equivalence. Those six self rows are canonical `EQUIVALENT` and are unlabeled. They are not in the false-rejection denominator.

## False equivalence

Denominator is ground-truth `non_equivalent`. Numerator is a claim of equivalence. Canonical, Z3, and cvc5 match.

| Slice | Count | Wilson 95% |
| --- | --- | --- |
| each degree-width cell | 0/1 | `[0.0, 0.7934506856227626]` |
| each width, both degrees | 0/2 | `[0.0, 0.6576197724933469]` |
| each degree, all five widths | 0/5 | `[0.0, 0.43448246478317476]` |
| all 20 rows | 0/10 | `[0.0, 0.2775327998628892]` |

## Decisive rate

Denominator is every row in the slice. Canonical, Z3, and cvc5 match. Every row is `EQUIVALENT` or `NOT_EQUIVALENT` for the checker, and `equivalent_within_model` or `counterexample_found` for the solvers.

| Slice | Count | Wilson 95% |
| --- | --- | --- |
| each degree-width cell | 2/2 | `[0.34238022750665303, 1.0]` |
| each width | 4/4 | `[0.5101091635454027, 1.0]` |
| each degree | 10/10 | `[0.7224672001371107, 0.9999999999999999]` |
| all | 20/20 | `[0.8388748419471806, 1.0]` |

The degree-level upper endpoint `0.9999999999999999` is the value `wilson_interval` printed.

## Time

Per-case wall-clock seconds. `n` is 2 in each degree-width cell, 10 for a degree, 4 for a width, and 20 overall.

Degree sums. Canonical degree 6: sum `11.794027497995557`, median `1.181182546501077`. Canonical degree 7: sum `29.69017564799651`, median `2.9579783374992985`. Z3 degree 6: sum `0.15159663500526221`, median `0.008493923000060022`. Z3 degree 7: sum `0.2244309349989635`, median `0.01082146750013635`. cvc5 degree 6: sum `0.13313646399546997`, median `0.006771525999283767`. cvc5 degree 7: sum `0.1881937740072317`, median `0.00825813900155481`.

Width 8 sums, n=4: canonical `8.241901911998866`, Z3 `0.05403455399937229`, cvc5 `0.03326440300588729`. Width 32 sums, n=4: canonical `8.313948169998184`, Z3 `0.19527899300373974`, cvc5 `0.19230976899780217`.

All 20 rows: canonical sum `41.48420314599207`, median `1.9251161664997198`; Z3 sum `0.3760275700042257`, median `0.009964356999262236`; cvc5 sum `0.32133023800270166`, median `0.007760644999507349`.

Degree-by-width canonical sums, n=2: degree 6 is `2.363624154997524`, `2.3505399629975727`, `2.35760303799907`, `2.3449889200019243`, and `2.377271421999467` at widths 1, 2, 4, 8, and 32. Degree 7 is `6.021557266001764`, `5.945048853001936`, `5.889979788997152`, `5.896912991996942`, and `5.9366767479987175` at those widths. The Z3 and cvc5 cells are in the summary file.
