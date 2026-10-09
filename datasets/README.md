# VERIFORGE datasets

Versioned research cases for the experimental framework (Phase 5).

## Layout

```
datasets/
  README.md
  development/     # method development, protocol checks, controlled configs
    metadata.json
    cases.jsonl
  held_out/        # reserved for final evaluation (not run in Phase 5)
    metadata.json
    cases.jsonl
```

## Partitions

| Partition | Purpose | Evaluation in Phase 5 |
| --- | --- | --- |
| `development` | Protocol freezes, metric fixtures, controlled mixes, method work | Used for framework validation only |
| `held_out` | Final evaluation set (later phase) | **Not evaluated** |

The benchmark must not be tuned against the held-out set. Phase 5 loads and validates held-out metadata and leakage controls. Phase 6 may run the benchmark engine on the **development** partition for engine validation only; it does not run held-out evaluation as a research conclusion.

## Metadata fields (§9.4)

Every dataset records:

- Dataset version
- Generation procedure
- Semantic model
- Random seed
- Case identifier (per case)
- Expected outcome where independently known (per case)
- Transformation category (per case)
- Complexity characteristics (per case)
- Inclusion or exclusion reason (per case)

## Near-duplicate leakage controls

Each case carries a `near_duplicate_key` derived from:

- semantic mode and bit width
- transformation category
- whitespace-normalized original source
- whitespace-normalized candidate source (empty if absent)

`veriforge.dataset_engine.assert_no_cross_partition_leakage` fails if any key appears in both partitions. Within a partition, duplicate keys are rejected. Variants of the same underlying transformation must not cross the development / held-out boundary.

## Artificial 90/10 mix

An artificial mixture of 90% correct and 10% incorrect candidates may be used as **one controlled test configuration**. It is labeled explicitly and **must not** be presented as an estimate of real-world error prevalence.

Development metadata may set `controlled_mix: true` with `controlled_mix_label` stating that denial. Cases participating in the mix carry labels such as `controlled_mix=90_10` and `mix_role=correct|incorrect`.

## Regenerating seed cases

```bash
python3 scripts/seed_phase5_datasets.py
```

Current seed version: `0.5.0`. Seed constant: `20261009`.

## Results status

No research evaluation results are stored here. Metric calculation tests use synthetic raw observations under the experiment store, not held-out outcomes.
