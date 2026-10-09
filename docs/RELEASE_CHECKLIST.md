# Release checklist — VERIFORGE §20 Definition of Done

Software version under review: **`1.0.0`**  
Checklist date (UTC): 2026-10-09  
Release branch: `cursor/phase-12-release-b430`  
Base commit: `6848fd4` (`cursor/phase-11-independent-review-0667`)  
Controlling specification: §20

Honesty rule: each criterion is judged against **executed** evidence. Failures disclose severity and next action.

## Evidence sources used

| Source | Result |
| --- | --- |
| Warm-host pytest on `cursor/phase-11-independent-review-0667` @ `6848fd4` | **359 passed, 0 failed, 0 skipped** |
| Warm-host held-out evaluation (Phase 10 tip; in-tree) | `dependency_available=true`; fingerprint `1b5a4a762b6485eca8668cc6e7dba93cd829246479cbeee00caf977c8fea5464`; seed `20261009` |
| Phase 12 authoring host clean install | **FAILED** — `SSLEOFError` to `pypi.org` (historical; `/opt/cursor/artifacts/phase12-clean-install.log`) |
| Phase 5 warm host clean venv install (2026-10-09) | **SUCCEEDED** — fresh `/tmp/veriforge-rc` + `pip install -e ".[dev]"` + `pytest -v` → **359 passed, 0 failed, 0 skipped** (`/opt/cursor/artifacts/phase12-clean-install-warm-host.log`, `phase12-pytest-clean-venv.log`) |
| Phase 12 authoring host held-out re-run | **unavailable** — `z3` missing; warm-host Phase 10 report **not** overwritten |
| Phase 12 static review | `PYTHONPATH=. python3 scripts/phase11_static_review_checks.py` → **PASS** (0 failures) |
| `ast.parse` over Python tree | **OK** |

## §20 criteria

| # | Criterion | Status | Evidence | Severity if fail | Next action |
| --- | --- | --- | --- | --- | --- |
| 1 | Supported grammar documented and enforced | **met** | `docs/SEMANTICS.md`; parser tests; fail-closed AST validation | — | Maintain |
| 2 | Semantic modes explicit and tested | **met** | Mode A/B docs + `test_semantics_mode_a/b.py`; Phase 1 decisions locked | — | Maintain |
| 3 | Unsupported inputs fail safely | **met** | Parser + security/adversarial tests; no `eval`/`exec` on user input | — | Maintain |
| 4 | Optimizer accepted transforms preserve equivalence under encoded model | **met (within TCB)** | Verification-guided acceptance; residual TCB risk R1 disclosed | — | Optional second semantics impl (R2) |
| 5 | Verifier distinguishes UNSAT, SAT, UNKNOWN, timeout, errors | **met** | `docs/FORMAL_MODEL.md`; verifier tests in suite | — | Maintain |
| 6 | Counterexamples independently checked where possible | **met** | Reference-evaluator validation; Phase 11 static rechecks PASS | — | Maintain |
| 7 | Artificially incorrect transforms isolated from production | **met** | `fuzzer_suite` EVALUATION_ONLY; isolation tests | — | Maintain |
| 8 | Required unit, integration, property, and regression tests pass | **met** | Clean-venv + prior warm-host: **359 passed / 0 failed / 0 skipped** @ Phase 12 tip | — | Maintain CI when available |
| 9 | Benchmark metrics independently tested | **met** | `tests/unit/test_benchmark_engine.py` in the 359 | — | Maintain |
| 10 | Solver latency and expression execution reported separately | **met** | Evaluation/benchmark engines; held-out latency_separation | — | Maintain |
| 11 | Raw experimental data and configuration metadata preserved | **met** | Config fingerprint + protocol docs; raw under `experiments/raw/` when present | — | Keep raw on measurement hosts |
| 12 | Held-out evaluation is reproducible | **met (command + prior run)** | Reproduction command below; warm-host Phase 10 run recorded | low (host env) | Re-run on new hosts; compare fingerprint/hypothesis wording |
| 13 | Interface does not fabricate results | **met** | UI presentation tests; honesty helpers; unavailable states | — | Maintain |
| 14 | Clean installation procedure works | **met** | Phase 5 warm host: `python3 -m venv /tmp/veriforge-rc` → `pip install -U pip` → `pip install -e ".[dev]"` → `pytest -v` → **359/0/0**. Authoring-host PyPI failure remains a disclosed environment limit, not a procedure defect. | — | Prefer pinning lockfile in CI; document egress for restricted hosts |
| 15 | Documentation matches implemented behavior | **met** | README / ARCHITECTURE / SEMANTICS / LIMITATIONS / this checklist | — | Keep docs in sync |
| 16 | Limitations and unresolved defects disclosed | **met** | `docs/LIMITATIONS.md`, ledger R1–R4, this checklist | — | Maintain |
| 17 | Every major research claim maps to supporting evidence | **met** | `docs/EVIDENCE_LEDGER.md` | — | Maintain |
| 18 | No unsupported novelty, correctness, or performance claim in final report | **met** | N1/N2 `NOT_SUPPORTED`; H3 `UNRESOLVED`; final report states no novelty | — | Maintain |

## Overall DoD verdict

**Met** against executed warm-host clean-install attestation and the full test suite (**359/0/0**), plus committed held-out artifacts. Residual **research** limitations (small held-out n, TCB R1/R2, baseline 5 not selected, H3 inconclusive) remain disclosed under criterion 16; they do not reopen criterion 14.

Therefore the release version is **`1.0.0`** (promoted from `1.0.0rc1` after clean-install re-attestation on the Phase 5 warm host).

## Reproduction command (saved held-out experiment)

```bash
python3 -m venv /tmp/veriforge-rc
source /tmp/veriforge-rc/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
python -m pytest -v
python scripts/run_held_out_evaluation.py --seed 20261009 --timeout 5.0 --execution-iterations 50 --trials 1
```

Expected when successful (prior warm-host held-out evidence; do not invent new numbers if the run fails):

- `dependency_available`: `true`
- Configuration fingerprint (prior): `1b5a4a762b6485eca8668cc6e7dba93cd829246479cbeee00caf977c8fea5464`
- Protocol: `veriforge-phase10-held-out-evaluation` v`1.0.0`
- Reports: `experiments/reports/phase10-held-out-evaluation.{json,md}`

## Release gate summary

| Gate | Status |
| --- | --- |
| Ship as `1.0.0` | **allowed** (DoD criterion 14 re-attested via clean venv on Phase 5 warm host; residual research caveats disclosed) |
| Ship as `1.0.0rc1` | superseded by `1.0.0` after clean-install attestation |
| Merge to `main` | Prefer leaving release branch + this checklist; merge only if forge/policy allows |
