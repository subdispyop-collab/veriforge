# VERIFORGE

Formal-verification-guided arithmetic expression optimization and research platform.

**Current phase:** Phase 4 — adversarial validation (property tests, isolated mutations, differential tests, reproducible seeds).

Phases 5–12 (benchmarks, experiment framework, Streamlit UI, and related modules) are not implemented.

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

## Optimization (verification-guided)

```python
from veriforge import SemanticConfiguration, SemanticMode, optimize

cfg = SemanticConfiguration(mode=SemanticMode.MODE_A)
result = optimize("(x + 0) * 1", cfg)
print(result.accepted.source)  # x
for step in result.trace:
    print(step.rule_id, step.decision, step.verification_result.status)
```

Default policy is conservative: each candidate must receive `EQUIVALENT_WITHIN_MODEL` from the Phase 2 verifier before acceptance. `COUNTEREXAMPLE_FOUND`, `UNKNOWN`, `TIMEOUT`, and error statuses are recorded as rejections and never silently accepted.

Initial production rules: `x+0→x`, `x-0→x`, `x*1→x`, `x*0→0` (validated under Mode A and Mode B separately).

## Adversarial validation (EVALUATION_ONLY harness)

```python
from veriforge import (
    SemanticConfiguration,
    SemanticMode,
    mutate_and_analyze,
    DEFAULT_MUTATION_SEED,
)

cfg = SemanticConfiguration(mode=SemanticMode.MODE_A)
results = mutate_and_analyze("x + y", cfg, seed=DEFAULT_MUTATION_SEED)
for item in results:
    print(
        item.mutation.mutation_id,
        item.verification_result.status,
        item.detected_as_non_equivalent,
        item.accepted_into_production,  # always False
    )
```

Artificial mutations live only in `veriforge.fuzzer_suite`. They are labeled, seeded, stored with `mutation_id` + `generation_method`, and never mixed into production rules. `optimize(..., policy=EVALUATION_ONLY)` remains rejected.

## Verification

```python
from veriforge import SemanticConfiguration, SemanticMode, verify_equivalence

cfg = SemanticConfiguration(mode=SemanticMode.MODE_A)
result = verify_equivalence("x + 1", "x + 2", cfg)
print(result.status)  # VerificationStatus.COUNTEREXAMPLE_FOUND
```

Result states are explicit (`EQUIVALENT_WITHIN_MODEL`, `COUNTEREXAMPLE_FOUND`, `UNKNOWN`, `TIMEOUT`, `UNSUPPORTED`, `INVALID_INPUT`, `TRANSLATION_ERROR`, `VERIFICATION_ERROR`) and are never collapsed to a Boolean. Confirmed counterexamples are independently checked by the reference evaluator.

## Safety

User input is parsed with Python’s `ast` module only. `eval` and `exec` are never used on user input.
