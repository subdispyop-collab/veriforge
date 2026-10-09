# VERIFORGE

Formal-verification-guided arithmetic expression optimization and research platform.

**Current phase:** Phase 1 — semantic foundation (grammar, safe parsing, semantic configuration, reference evaluator).

Phases 2–12 (Z3 verifier, optimizer, benchmarks, Streamlit UI, and related modules) are not implemented.

## Requirements

- Python 3.11 or newer (developed and tested on 3.12)

## Setup

```bash
python3 -m pip install -e ".[dev]"
```

## Run tests

```bash
python3 -m pytest
```

## Semantic modes

- **Mode A:** unbounded mathematical integers
- **Mode B:** unsigned fixed-width bit-vectors (default width 32), modular wrap for `+`, `-`, `*`; literals outside `[0, 2^w-1]` are rejected

See `docs/SEMANTICS.md` for the full contract.

## Safety

User input is parsed with Python’s `ast` module only. `eval` and `exec` are never used on user input.
