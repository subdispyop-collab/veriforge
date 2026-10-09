# VERIFORGE

Formal-verification-guided arithmetic expression optimization and research platform.

**Current phase:** Phase 6 — benchmark engine (separated §10 timings, repeated trials, raw saves, reproduction).

Phases 7–12 (full audit/export, Streamlit UI, and related modules) are not implemented. **No held-out evaluation has been run as a research conclusion.**

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

## Benchmark engine (Phase 6)

Measures section-10 quantities **separately** (solver latency is not expression execution time). Reports use medians and variability. Never claims execution speedup from a shorter expression or a faster solver alone.

```bash
python3 scripts/run_benchmarks.py --case-id dev-hand-001 --trials 2 --warmup 1 \
  --save-config /tmp/veriforge-bench-config.json --json-summary /tmp/veriforge-bench-summary.json
```

```python
from veriforge import make_benchmark_configuration, run_benchmark
from veriforge.benchmark_engine import load_development_cases_for_engine_validation
from veriforge.models import DatasetPartition

cases = load_development_cases_for_engine_validation()
cfg = make_benchmark_configuration(
    trials_per_case=2,
    warmup_trials=1,
    dataset_partition=DatasetPartition.DEVELOPMENT,
    case_ids=["dev-hand-001"],
)
run_id, measurements, report = run_benchmark(cfg, cases, persist=False)
assert report.is_research_conclusion is False
```

Development datasets validate the engine only. Timing nondeterminism is disclosed on every configuration and report.

## Research protocol (Phase 5, still frozen)

- Preregistered plan: `docs/RESEARCH_PLAN.md` (hypotheses are not findings)
- Frozen protocol: `docs/EXPERIMENT_PROTOCOL.md` (version `0.5.0`)
- Benchmark protocol id: `veriforge-phase6-benchmark-protocol` (version `0.6.0`)
- Datasets: `datasets/development/`, `datasets/held_out/` — see `datasets/README.md`

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
