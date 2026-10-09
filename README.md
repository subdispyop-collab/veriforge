# VERIFORGE

Formal-verification-guided arithmetic expression optimization and research platform.

**Current phase:** Phase 2 — formal verification (AST/IR → Z3 translation, solver-result classification, counterexample validation).

Phases 3–12 (optimizer, benchmarks, Streamlit UI, and related modules) are not implemented.

## Requirements

- Python 3.11 or newer (developed and tested on 3.12)
- `z3-solver==5.1.0.0` (pinned in `pyproject.toml` / `requirements.lock`)

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
