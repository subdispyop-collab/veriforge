# Baseline audit

Audit host date: 2026-10-11. Starting commit: `004415fe54451ac7a84488d1e05bf44de924b216` on `cursor/phase-12-release-b430`. Working tree was clean. Software version remains `1.0.0`.

## Repository state that was checked

| Claim | Checked result |
| --- | --- |
| Version 1.0.0 | Matches `veriforge/version.py` and `pyproject.toml`. Not bumped. |
| Python, Z3, Streamlit, Plotly | Declared in `pyproject.toml`. On this host `import z3` fails. Streamlit, Plotly, pandas, pytest, and Hypothesis were not importable. |
| Mode A and unsigned Mode B | Present in `docs/SEMANTICS.md` and `veriforge/semantics.py`. |
| Four production rewrites | `identity.add_zero`, `identity.sub_zero`, `identity.mul_one`, `identity.mul_zero`. Still the only rules in `default_rules()`. |
| Fail-closed parsing | Production parser rejects unsupported syntax. Confirmed again by the independent parser on the same benchmark sources (0 accept/reject splits at audit time). |
| Eight historical held-out cases | `datasets/held_out/cases.jsonl` still has 8 lines. It was not overwritten. |
| 359-test suite | Historical warm-host result at `6848fd4`, recorded in `PROJECT_STATUS.md`. This host did not re-run it. |
| No novel empirical finding in the 1.0.0 release | The Phase 10 report and literature review say so. This audit does not reopen that claim. |

## Commands actually run for the baseline

```bash
git status
git rev-parse HEAD
python3 -m pip install -e ".[dev]"
python3 -c "import z3"
```

`pip install` failed: `SSLError(SSLEOFError)` talking to `pypi.org`, then `No matching distribution found for setuptools>=68`. Apt repositories returned HTTP 403. Egress is restricted to a Cursor allowlist that does not include PyPI. That is an environment failure, not a test failure.

`import z3` raised `ModuleNotFoundError`. No application test count is claimed for the historical suite on this host.

## Configuration

Phase 1 limits remain: source length 4096, AST nodes 256, nesting 32, Mode A literal bit length 4096, solver timeout 5 seconds, Mode B default width 32, unsigned. Signed Mode B is not a production mode.

## Known limitations carried forward

Correlated parser/translator/evaluator error can still yield a false `EQUIVALENT_WITHIN_MODEL` when the only proof is one Z3 encoding. The historical held-out set has n=8. Baseline 5 (external tool) was not selected in Phase 10. H3 was unresolved. No execution-speed claim was established.
