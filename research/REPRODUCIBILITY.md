# Reproducibility

Version `1.0.0`. Branch `cursor/method-discovery-7f34`, cut from `8ad58149d1ee1fcf7248cbf4d9e7618e66daec14`. Python 3.12.3. Z3 4.8.17 through `/home/ubuntu/py-z3` and `Z3_LIBRARY_PATH=/home/ubuntu/al-root/usr/lib64`. cvc5 1.3.2 through the bundled loader under `/home/ubuntu/solvers`. Those solvers were not rerun for a new method.

## Files

- `research/METHOD_DISCOVERY_AUDIT.md`
- `research/PRIOR_ART_MATRIX.md`
- `research/CANDIDATE_METHODS.md`
- `research/NEW_METHOD_SPEC.md`
- `research/PREREGISTRATION.md`
- `research/method_discovery_preregistration.json`
- `research/THREATS_TO_VALIDITY.md`
- `research/RESULTS.md`
- `research/method_discovery_config.json`
- `research/method_discovery_dataset_manifest.json`
- `scripts/method_discovery_analysis.py`
- `research/METHOD_DISCOVERY_REPORT.md`
- `experiments/reports/method-discovery/analysis.json`

No new dataset directory was created. `datasets/held_out/cases.jsonl` stays at 8 lines. There are no raw per-case rows.

## Command

```text
python3 scripts/method_discovery_analysis.py
```

The script checks the preregistration hash and prints the NO-GO record. It does not call Z3 or cvc5. The stdout from the run recorded in `research/RESULTS.md` is `experiments/reports/method-discovery/analysis.json`. Exit code 0. `pair_count` is 0 and `false_equivalence` is null.

## Tests and CI

No new method module was added, so no new unit tests were added. Existing tests were not weakened and were not rerun for this gate. GitHub Actions was not executed: `github.com:443` fails with `SSL_ERROR_SYSCALL` from this machine, and the workflow file was not started.

## Pins that are still absent

`z3-solver==5.1.0.0`, `hypothesis==6.168.5`, and mutmut were not installed. The attempts and errors are in `research/PART15_AUDIT.md`. This gate does not depend on them.

## Offline image

The earlier Podman build and run on `cursor/research-hardening-7f34` exited 0. That image runs the old assurance script. It is not a run of the canonical-form study.

## Canonical-form study

Protocol `research/PROTOCOL_CANONICAL_FORM.md`, SHA-256 `e5cb120f983a8df481b1db2c52aa92d8293eb80e94251b1e536c8fa71646cd00`. Dataset `datasets/canonical_form_v1/cases.jsonl`, SHA-256 `e7de7560c6fa46f23038d6f2ea3701d867d3114fdd7d1b323cf672c6f4a5f37a`, 57 lines. Summary `experiments/reports/canonical-form-v1/summary.json`.

```text
env -u PYTHONPATH -u LD_LIBRARY_PATH PYTHONPATH=/home/ubuntu/py-z3:/workspace Z3_LIBRARY_PATH=/home/ubuntu/al-root/usr/lib64 python3 scripts/run_canonical_form_study.py
```

That command was run once. Python 3.12.3, Z3 4.8.17, cvc5 `This is cvc5 version 1.3.2`. Unit tests `tests/unit/test_falling_factorial.py` exited 0 before that run. GitHub Actions was not started.
