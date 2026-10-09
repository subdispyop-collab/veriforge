# VERIFORGE

Formal-verification-guided arithmetic expression optimization and research platform.

**Current phase:** Phase 5 — experimental framework (frozen protocol, versioned datasets, experiment identifiers, raw persistence, metric validation).

Phases 6–12 (benchmark engine, full audit/export, Streamlit UI, and related modules) are not implemented. **No held-out evaluation has been run.**

## Requirements

- Python 3.11 or newer (developed and tested on 3.12)
- `z3-solver==5.1.0.0` (pinned in `pyproject.toml` / `requirements.lock`)
- Dev: `pytest`, `hypothesis` (see `requirements.lock`)

## Setup

```bash
python3 -m pip install -e ".[dev]"
```

## Run tests

```bash
python3 -m pytest
```

## Semantic modes

- **Mode A:** unbounded mathematical integers (Z3 `Int` sorts)
- **Mode B:** unsigned fixed-width bit-vectors (default width 32; Z3 `BitVec` sorts), modular wrap for `+`, `-`, `*`; literals outside `[0, 2^w-1]` are rejected

See `docs/SEMANTICS.md` for the full contract and `docs/FORMAL_MODEL.md` for the encoded equivalence query and TCB assumptions.

## Research protocol (Phase 5)

- Preregistered plan: `docs/RESEARCH_PLAN.md` (hypotheses are not findings)
- Frozen protocol: `docs/EXPERIMENT_PROTOCOL.md` (version `0.5.0`)
- Datasets: `datasets/development/`, `datasets/held_out/` — see `datasets/README.md`
- Experiment APIs: `veriforge.experiment_engine`, `veriforge.dataset_engine`

```python
from veriforge import (
    DatasetPartition,
    create_experiment_run,
    configuration_fingerprint,
    baseline_catalog,
    load_all_partitions,
)

bundles = load_all_partitions()  # asserts no cross-partition near-duplicate leakage
run = create_experiment_run(
    configuration={"note": "framework check only"},
    dataset_partition=DatasetPartition.DEVELOPMENT,
)
print(run.run_id, run.configuration_fingerprint)
print([b.baseline_id for b in baseline_catalog()])
```

Creating a run does not execute held-out evaluation. An artificial 90/10 mix, if used, is a controlled configuration — not real-world prevalence.

## Optimization (verification-guided)

```python
from veriforge import SemanticConfiguration, SemanticMode, optimize

cfg = SemanticConfiguration(mode=SemanticMode.MODE_A)
result = optimize("(x + 0) * 1", cfg)
print(result.accepted.source)  # x
```

Default policy is conservative: each candidate must receive `EQUIVALENT_WITHIN_MODEL` before acceptance.

## Adversarial validation (EVALUATION_ONLY harness)

Artificial mutations live only in `veriforge.fuzzer_suite`. They are labeled, seeded, and never mixed into production rules.

## Verification

```python
from veriforge import SemanticConfiguration, SemanticMode, verify_equivalence

cfg = SemanticConfiguration(mode=SemanticMode.MODE_A)
result = verify_equivalence("x + 1", "x + 2", cfg)
print(result.status)  # VerificationStatus.COUNTEREXAMPLE_FOUND
```

Result states are explicit and never collapsed to a Boolean.

## Safety

User input is parsed with Python’s `ast` module only. `eval` and `exec` are never used on user input.
