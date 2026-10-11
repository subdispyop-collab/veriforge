# Threat model for this hardening pass

This note extends `docs/SECURITY.md`. It does not replace it. VERIFORGE still does not claim resistance to every attack.

## Assets

Equivalence verdicts, dataset labels, and exported records.

## Adversaries considered

- A malformed expression that the parser executes. Both parsers reject calls, and neither uses `eval` or `exec` on the source. The unit test `tests/unit/test_no_eval_exec.py` was not re-run here because pytest is not installed. The new parser has no `eval` or `exec` call.
- A timeout or missing solver reported as equivalence. `combine_gates` returns `TIMEOUT` or `UNKNOWN` for those gates. The judge demo executed that contract.
- A non-equivalent rewrite accepted because only one translator was used. The Z3 arm did not run, so this residual risk is unchanged for the production optimizer.
- A corrupted label. Construction intent is stored beside the oracle label. Two intent mismatches are `not_computed` budget overflows, not silent flips to equivalence.
- Cross-partition leakage. Held-out membership is the whole family. The historical n=8 files were not edited.

## Not shown

No penetration test was run. Secret redaction was not re-measured. Supply-chain checks of uninstalled wheels were not performed.
