# Release checklist — VERIFORGE §20 Definition of Done

Software version under review: **`1.0.0rc1`** (release candidate; **not** labeled `1.0.0` because DoD is not fully met).  
Checklist date (UTC): 2026-10-09  
Release branch: `cursor/phase-12-release-b430`  
Base commit: `6848fd4` (`cursor/phase-11-independent-review-0667`)  
Controlling specification: §20

Honesty rule: each criterion is judged against **executed** evidence. Failures disclose severity and next action. The project is **not** labeled fully complete.

## Evidence sources used

| Source | Result |
| --- | --- |
| Warm-host pytest on `cursor/phase-11-independent-review-0667` @ `6848fd4` | **359 passed, 0 failed, 0 skipped** (coordinator-provided Phase 11 warm-host evidence) |
| Warm-host held-out evaluation (Phase 10 tip; in-tree) | `dependency_available=true`; fingerprint `1b5a4a762b6485eca8668cc6e7dba93cd829246479cbeee00caf977c8fea5464`; seed `20261009` |
| Phase 12 authoring host clean install | **FAILED** — `SSLEOFError` / `UNEXPECTED_EOF_WHILE_READING` to `pypi.org` (`/opt/cursor/artifacts/phase12-clean-install.log`) |
| Phase 12 authoring host held-out re-run | **unavailable** — `z3 import failed` (artifacts under `experiments/reports/phase12-release-attempt/`; warm-host report **not** overwritten) |
| Phase 12 static review | `PYTHONPATH=. python3 scripts/phase11_static_review_checks.py` → **PASS** (0 failures) |
| `ast.parse` over Python tree | **OK** |

## §20 criteria

| # | Criterion | Status | Evidence | Severity if fail | Next action |
| --- | --- | --- | --- | --- | --- |
| 1 | Supported grammar documented and enforced | **met** | `docs/SEMANTICS.md`; parser tests in warm-host suite; fail-closed AST validation | — | Maintain |
| 2 | Semantic modes explicit and tested | **met** | Mode A/B in `docs/SEMANTICS.md`; `test_semantics_mode_a/b.py`; Phase 1 decisions locked | — | Maintain |
| 3 | Unsupported inputs fail safely | **met** | Parser + security/adversarial tests; no `eval`/`exec` on user input | — | Maintain |
| 4 | Optimizer accepted transforms preserve equivalence under encoded model | **met (within TCB)** | Verification-guided acceptance; optimizer + regression gates in suite; residual TCB risk R1 disclosed | — | Optional second semantics impl (R2) |
| 5 | Verifier distinguishes UNSAT, SAT, UNKNOWN, timeout, errors | **met** | `docs/FORMAL_MODEL.md`; verifier unit/property tests in suite | — | Maintain |
| 6 | Counterexamples independently checked where possible | **met** | Reference-evaluator validation path; Phase 11 static rechecks PASS | — | Maintain |
| 7 | Artificially incorrect transforms isolated from production | **met** | `fuzzer_suite` EVALUATION_ONLY; isolation/mutation tests | — | Maintain |
| 8 | Required unit, integration, property, and regression tests pass | **met (warm host)** | Warm-host @ `6848fd4`: **359 passed / 0 failed / 0 skipped**. Authoring-host pytest **unavailable** (deps) | — | Re-run on egress-enabled host after install |
| 9 | Benchmark metrics independently tested | **met** | `tests/unit/test_benchmark_engine.py` included in warm-host 359 | — | Maintain |
| 10 | Solver latency and expression execution reported separately | **met** | Evaluation/benchmark engines; held-out latency_separation section | — | Maintain |
| 11 | Raw experimental data and configuration metadata preserved | **met** | Config fingerprint + protocol docs; raw under `experiments/raw/` (gitignored when present); config JSON committed | — | Keep raw on measurement hosts |
| 12 | Held-out evaluation is reproducible | **met (command + prior run)** | Command below reproduces protocol; prior warm-host run recorded. Fresh SMT re-run on this host **unavailable** | low (host env) | Re-run on Z3-capable host; compare fingerprint/hypothesis wording |
| 13 | Interface does not fabricate results | **met** | UI presentation tests; honesty helpers; unavailable states | — | Maintain |
| 14 | Clean installation procedure works | **failed on this host** | `pip install -e ".[dev]"` → SSL EOF to `pypi.org` | **high for local attestation**; procedure itself is documented | Allowlist PyPI domains; re-attest clean install; until then do not claim host-local install success |
| 15 | Documentation matches implemented behavior | **met** | README / ARCHITECTURE / SEMANTICS / LIMITATIONS updated for Phase 12 reality | — | Keep docs in sync |
| 16 | Limitations and unresolved defects disclosed | **met** | `docs/LIMITATIONS.md`, ledger R1–R4, this checklist | — | Maintain |
| 17 | Every major research claim maps to supporting evidence | **met** | `docs/EVIDENCE_LEDGER.md` | — | Maintain |
| 18 | No unsupported novelty, correctness, or performance claim in final report | **met** | N1/N2 `NOT_SUPPORTED`; H3 `UNRESOLVED`; final report states no novelty | — | Maintain |

## Overall DoD verdict

**Not fully complete.** Criterion **14** fails on the Phase 12 authoring host (PyPI egress). All other applicable criteria are **met** against warm-host suite evidence (`359/0/0` @ `6848fd4`) and committed held-out artifacts, with residual research limitations (small n, TCB R1/R2, baseline 5 not selected) disclosed rather than waived.

Therefore the release tag is **`1.0.0rc1`**, not `1.0.0`.

## Reproduction command (saved held-out experiment)

On a host with pinned dependencies installed (`z3-solver==5.1.0.0` and the rest of `requirements.lock`):

```bash
python3 -m pip install -e ".[dev]"
python3 scripts/run_held_out_evaluation.py --seed 20261009 --timeout 5.0 --execution-iterations 50 --trials 1
```

Expected when successful (prior warm-host evidence; do not invent new numbers if the run fails):

- `dependency_available`: `true`
- Configuration fingerprint (prior): `1b5a4a762b6485eca8668cc6e7dba93cd829246479cbeee00caf977c8fea5464`
- Protocol: `veriforge-phase10-held-out-evaluation` v`1.0.0`
- Reports: `experiments/reports/phase10-held-out-evaluation.{json,md}`

Phase 12 authoring-host attempt (honest unavailable; does **not** replace the warm-host report):

```bash
PYTHONPATH=. python3 scripts/run_held_out_evaluation.py --seed 20261009 --timeout 5.0 \
  --execution-iterations 50 --trials 1 --skip-persist \
  --config-out experiments/reports/phase12-release-attempt/phase12-repro-attempt-config.json \
  --report-json experiments/reports/phase12-release-attempt/phase12-repro-attempt.json \
  --report-md experiments/reports/phase12-release-attempt/phase12-repro-attempt.md
```

Result: `dependency_available=false`; blocker `z3 import failed: No module named 'z3'`.

## Release gate summary

| Gate | Status |
| --- | --- |
| Ship as `1.0.0` | **blocked** (DoD criterion 14 on this host; residual research caveats) |
| Ship as `1.0.0rc1` release candidate | **allowed** with disclosed gaps |
| Merge to `main` | Prefer leaving release branch + this checklist; do not merge unless forge/policy explicitly allows and install re-attested |
