# Phase 10 held-out evaluation protocol

- **Protocol id:** `veriforge-phase10-held-out-evaluation`  
- **Protocol version:** `1.0.0`  
- **Frozen before scoring:** yes (this document + `docs/EXPERIMENT_PROTOCOL.md` + `docs/RESEARCH_PLAN.md`)  
- **Partition:** `datasets/held_out/` only (development unused for scoring)  
- **Dataset version:** `0.5.0`  
- **Random seed:** `20261009`  
- **Solver timeout:** `5.0` seconds (fixed policy)  
- **Execution iterations per timed expression:** `50`  
- **Trials per case:** `1` (seed partition is small; do not inflate n with related variants)

## Baselines measured

| Baseline id | Measured in Phase 10 harness | Notes |
| --- | --- | --- |
| `baseline.original_no_optimization` | yes (when deps allow) | No rewrite; execution only |
| `baseline.rule_based_without_smt` | yes (when deps allow) | Evaluation harness; production `optimize()` remains verification-guided |
| `baseline.verification_enabled` | yes (when deps allow) | Production verification-guided path |
| `baseline.testing_only_validation` | yes (when deps allow) | SMT check of dataset candidates; never production acceptance |
| `baseline.external_tool` | **not_selected** | No fair same-workload external tool integrated |

## Metrics

- Report by `transformation_category` with **sample sizes**.  
- Separate **solver latency** from **expression execution** latency.  
- Detection metrics apply to cases with expected non-equivalence (and explicit detection observations).  
- TIMEOUT / UNKNOWN never count as equivalence.  
- No execution-speedup claim from shorter expressions or faster solver returns alone.

## Reproduction

```bash
python3 -m pip install -e ".[dev]"
python3 scripts/run_held_out_evaluation.py \
  --seed 20261009 \
  --timeout 5.0 \
  --execution-iterations 50 \
  --trials 1
```

Configuration JSON: `experiments/configurations/phase10-held-out-config.json`  
Reports: `experiments/reports/phase10-held-out-evaluation.{json,md}`  
Raw observations: `experiments/raw/<run_id>/` (local; gitignored)

If `z3` cannot be imported, the script must record a dependency blocker and label baseline results **unavailable** without fabricating numbers.
