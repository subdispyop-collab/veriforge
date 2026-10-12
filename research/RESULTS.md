# Results

Record id `veriforge-method-discovery-nogo-v1`. Gate **NO-GO**. Software version `1.0.0`. Base commit `8ad58149d1ee1fcf7248cbf4d9e7618e66daec14`. Branch `cursor/method-discovery-7f34`.

No new method was implemented. No new pairs were generated. No solver was run for this gate.

## Analysis script

Command, run from the repository root after the preregistration hash was locked:

```text
python3 scripts/method_discovery_analysis.py
```

Exit code: 0.

Stdout, also saved at `experiments/reports/method-discovery/analysis.json`:

```json
{
  "gate": "NO-GO",
  "protocol_sha256": "d0b112064b93acb4b19aecd62cac865eedb2f653a1a9aade65ee10d2255869cb",
  "primary_hypothesis": "not_tested",
  "pair_count": 0,
  "false_equivalence": null,
  "reason": "no candidate survived the gate; no confirmatory rows exist"
}
```

`research/PREREGISTRATION.md` SHA-256 is `d0b112064b93acb4b19aecd62cac865eedb2f653a1a9aade65ee10d2255869cb`. The script checked that hash against `research/method_discovery_preregistration.json` and refused to invent a rate.

## Primary outcome

H_new is **not tested**. It is not supported and it is not rejected by a measurement.

There is no new false-equivalence count. `pair_count` is 0. `false_equivalence` is null. A Wilson interval was not computed. An empty denominator is not a zero rate.

There is no effect size, no confidence interval, and no trade-off between accuracy and latency for a new method, because there is no new method and no new rows.

## Raw records

There are no raw per-case records. Creating them would have required pairs. The preregistration forbids that generation.

`research/method_discovery_dataset_manifest.json` records `dataset_generated: false`, `fingerprint: null`, `pair_count: 0`, and `family_count: 0`.

## What was not measured

Z3 4.8.17 and cvc5 1.3.2 were present and were not rerun. The 463-pair census and the 72-pair confirmatory-v2 run stay historical context. They are not evidence about an unimplemented method. Their false-equivalence counts are not copied here as a result of this gate.

Alive2 was not installed and was not run. GitHub Actions was not started. Existing pytest was not rerun for this gate. No new unit tests were added, because no new module was added.

## Decision

Phase 9 success conditions are not met. There is no defensible distinction that passed the gate, no implemented certificate checker, and no confirmatory experiment. The outcome is not manufactured into an improvement.

Verdict: **No defensible novel contribution established.**
