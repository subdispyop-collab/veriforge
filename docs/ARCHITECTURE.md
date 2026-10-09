# Architecture

Status: Phases 1–12 are implemented. Version `1.0.0rc1` (release candidate). §20 DoD not fully met on egress-blocked hosts — see `docs/RELEASE_CHECKLIST.md`.

## Implemented

| Boundary | Responsibility | Status |
| --- | --- | --- |
| Parser | Parse one expression with Python's `ast` module. Do not execute it. Accept only the initial grammar. Reject every other form. Enforce resource limits. | Implemented: `veriforge/parser_engine.py` |
| Semantics / configuration | Hold the selected mode and Mode B bit width. Defaults and limits from the locked Phase 1 decisions. | Implemented: `veriforge/config.py`, `veriforge/semantics.py` |
| Reference evaluator | Evaluate a supported expression under the selected mode without using Z3. | Implemented: `veriforge/reference_evaluator.py` |
| Verifier | Translate original and candidate into the Z3 sort for the active mode. Ask whether an input exists that makes them differ. Classify the solver outcome. Independently validate counterexamples. Do not treat the solver result as proof that the application is correct. | Implemented: `veriforge/verifier_engine.py` |
| Optimizer | Apply a small set of identifiable, conservative rules. Record preconditions and a full trace. Accept a candidate on the default path only after the required equivalence check. | Implemented: `veriforge/optimizer_engine.py` |
| Mutation facility | Generate incorrect candidates for detection tests. Keep them labeled, seeded, and off the production rule set. They must not bypass verification. | Implemented: `veriforge/fuzzer_suite.py` |
| Datasets | Versioned development / held-out cases, §9.4 metadata, near-duplicate leakage controls, controlled-mix labeling. | Implemented: `veriforge/dataset_engine.py`, `datasets/` |
| Experiments | Run identifiers, configuration fingerprints, baseline catalog, raw observation persistence, metric calculations from stored observations. | Implemented: `veriforge/experiment_engine.py`, `veriforge/storage/` |
| Benchmarks | Separate §10 timings, repeated trials, warmups, timeout/environment records, raw saves, medians/variability, reproduction. | Implemented: `veriforge/benchmark_engine.py` |
| Audit / storage deepening | Run history, §13 optimization-run records, JSON/CSV export with result links, secret redaction, replay from recorded configuration, integrity checks, raw vs derived separation. | Implemented: `veriforge/audit_engine.py`, `veriforge/storage/repositories.py`, `veriforge/storage/migrations/` |
| Interface | Six Streamlit pages; logic outside presentation; unavailable states; no fabricated results. | Implemented: `veriforge/app.py`, `veriforge/ui/` |
| Security | Classified errors, secret-safe messages, controlled exports, threat model docs. | Implemented: `veriforge/security.py`, `docs/SECURITY.md` |
| Research evaluation | Held-out baselines, literature review, evidence ledger. | Implemented: `veriforge/evaluation_engine.py`, `docs/LITERATURE_REVIEW.md`, `docs/EVIDENCE_LEDGER.md` |
| Independent review | Adversarial review of semantics, TCB, counterexamples, design, claims. | Implemented: `docs/INDEPENDENT_REVIEW.md`; TCB in `docs/FORMAL_MODEL.md` / `docs/SECURITY.md` |
| Release | §20 checklist + §22 final research report from actual behavior. | Implemented: `docs/RELEASE_CHECKLIST.md`, `docs/FINAL_RESEARCH_REPORT.md` |
| Typed models / exceptions | Phase 1–10 records including audit and integrity types. | Implemented: `veriforge/models.py`, `veriforge/exceptions.py` |

Package layout present after Phase 12:

```
veriforge/
    __init__.py
    app.py
    version.py
    config.py
    models.py
    exceptions.py
    parser_engine.py
    semantics.py
    reference_evaluator.py
    verifier_engine.py
    optimizer_engine.py
    fuzzer_suite.py
    dataset_engine.py
    experiment_engine.py
    benchmark_engine.py
    audit_engine.py
    evaluation_engine.py
    security.py
    storage/
        __init__.py
        database.py
        repositories.py
        migrations/
    ui/
        __init__.py
        catalog.py
        presentation.py
        actions.py
        components.py
        visualizations.py
        pages.py
datasets/
    README.md
    development/
    held_out/
experiments/
    protocols/
    configurations/
    raw/
    reports/
    exports/
tests/
    unit/
    properties/
    adversarial/
    regression/
docs/
scripts/
    seed_phase5_datasets.py
    run_benchmarks.py
    run_held_out_evaluation.py
    phase11_static_review_checks.py
    run_ui.py
pyproject.toml
requirements.lock
```

## Verifier data flow

1. Accept original and candidate as source strings or parsed `Expression` values under one `SemanticConfiguration`.
2. Parse/validate (fail closed → `INVALID_INPUT` or `UNSUPPORTED`).
3. Translate both IR trees to Z3: Mode A → `Int`; Mode B → `BitVec(w)`.
4. Assert `[[E_o]] ≠ [[E_c]]` and `check` with the configured timeout (default 5s).
5. Classify `unsat` / `sat` / `unknown` into explicit `VerificationStatus` values.
6. On `sat`, extract the model, evaluate both expressions with the reference evaluator, and emit `COUNTEREXAMPLE_FOUND` only when outputs differ.

## Optimizer data flow (Phase 3)

1. Parse and validate under one `SemanticConfiguration` (fail closed).
2. Select applicable production rules for the active mode (leftmost-innermost).
3. Generate one candidate rewrite; record rule id, name, formal description, and preconditions.
4. Verify the candidate against the *original* expression with `verify_equivalence`.
5. Accept only when status is `EQUIVALENT_WITHIN_MODEL` under `CorrectnessPolicy.VERIFICATION_GUIDED`.
6. Record rejections (including `COUNTEREXAMPLE_FOUND`, `UNKNOWN`, `TIMEOUT`, and error statuses) with reasons; never accept them silently.
7. Return the accepted expression and the complete `TransformationStep` trace.

## Mutation / EVALUATION_ONLY data flow (Phase 4)

1. Enumerate artificial mutation sites on a parsed IR under selected `MutationCategory` values.
2. Build `MutationRecord` values with `mutation_id`, `generation_method`, `seed`, and `artificial=True`.
3. Analyze each record with `verify_equivalence` under `CorrectnessPolicy.EVALUATION_ONLY`.
4. Record detection (`detected_as_non_equivalent`) from the verifier status.
5. Never set `accepted_into_production`. Never register mutation categories as production rules.
6. Production `optimize()` continues to reject `EVALUATION_ONLY` so the harness cannot share an ungated acceptor.

## Dataset / experiment data flow (Phase 5)

1. Author or generate cases with §9.4 fields; assign `near_duplicate_key`.
2. Persist under `datasets/development/` or `datasets/held_out/`; refuse cross-partition key collisions.
3. Create an `ExperimentRun` with `run_id` and `configuration_fingerprint` (does not execute held-out evaluation).
4. Store raw `RawObservation` JSON under `experiments/raw/<run_id>/`; index runs/observations in SQLite.
5. Compute metrics only from stored raw observations, including by-class rows.

Two experimental configurations stay distinct:

- Verification-guided mode. Candidates pass the required equivalence checks before acceptance. This is the default application mode (implemented).
- Evaluation-only mode. Deliberately incorrect candidates may be analyzed in the controlled harness. They are never silently accepted into the production path (implemented in `fuzzer_suite`; rejected by `optimize()`).

Verification states remain distinct: `EQUIVALENT_WITHIN_MODEL`, `COUNTEREXAMPLE_FOUND`, `UNKNOWN`, `TIMEOUT`, `UNSUPPORTED`, `INVALID_INPUT`, `TRANSLATION_ERROR`, and `VERIFICATION_ERROR`. A Boolean success flag is not an acceptable substitute.

## Benchmark data flow (Phase 6)

1. Build a `BenchmarkConfiguration` (trials, warmups, seed, timeout policy, environment).
2. Select development-partition cases for engine validation (held-out research evaluation refused).
3. For each case: optional warmup trials, then timed trials.
4. Measure §10 quantities into separate fields on `BenchmarkMeasurement` (never one merged duration).
5. Persist as `ObservationKind.BENCHMARK_TIMING` raw JSON; snapshot configuration beside the run.
6. Summarize with medians/variability and outcome rates; `is_research_conclusion=False`.
7. Rerun from saved configuration JSON; disclose timing nondeterminism.

`verify_equivalence_timed` exposes translation vs solver wall times for the verifier path.

## Audit / storage data flow (Phase 7)

1. Build an `OptimizationRunRecord` from an `OptimizationResult` with all §13 fields and a configuration fingerprint.
2. Redact secrets and unnecessary personal data before any persistence.
3. Store the raw JSON under `experiments/raw/optimization_runs/<run_id>/`; index in SQLite via `AuditRepository`.
4. Emit an `AuditEvent` whose `result_ref` links to that raw file.
5. Export audit events and linked run payloads to JSON or CSV (`result_link` column/field).
6. Replay calls `optimize` using the recorded `semantic_configuration` (not ambient defaults).
7. Write derived summaries only under `experiments/reports/`; integrity checks refuse raw/derived collision and fingerprint tampering.

## Interface data flow (Phase 8)

1. `veriforge/app.py` selects one of six pages from `veriforge.ui.catalog.PAGE_NAMES`.
2. Pages call `veriforge.ui.actions` (orchestration) and `veriforge.ui.presentation` (labels / availability).
3. Actions call existing engines (parser, optimizer, verifier, fuzzer, benchmark, audit). Streamlit widgets do not own solver or storage logic.
4. Visualizations refuse empty series and show unavailable states instead of fabricated charts.
5. Research Dashboard loads metrics only from completed stored runs.

## Security boundary (Phase 9)

| Boundary | Specified responsibility | Status |
| --- | --- | --- |
| Security helpers | Error classification, secret-safe messages, controlled export paths | Implemented: `veriforge/security.py` |
| Threat model | Document adversary, assets, controls, remaining limits | Implemented: `docs/SECURITY.md` |
| §15 enforcement | AST validation, limits, timeouts, safe files, no eval/exec | Enforced in parser/verifier/audit/UI; tested under `tests/unit/test_security.py` and `tests/adversarial/test_security_resilience.py` |

## Planned boundaries (not implemented)

| Boundary | Specified responsibility | Status |
| --- | --- | --- |
| Research evaluation | Phase 10 held-out evaluation and literature review. | Not implemented |

Typed records still pending as dedicated later-phase products: `FuzzCase`, `ResearchClaim`. Phase 7 added `AuditEvent` and `OptimizationRunRecord`. Phase 6 added benchmark timing types. Phase 5 added dataset/experiment/metric types.

Trusted computing base assumptions for verification are written in `docs/FORMAL_MODEL.md` and summarized in `docs/LIMITATIONS.md`.

Out of scope until a later phase shows a need: distributed infrastructure, cloud services, and deployment machinery.

## Known architectural risks

- The verifier, the optimizer, and the reference evaluator can drift apart if they do not share one semantic configuration object and one grammar.
- Mode B can be implemented as unbounded Python integers by mistake.
- `UNKNOWN` and timeout can be collapsed into "not SAT" and then displayed as equivalent. The result type makes that collapse a type error.
- The mutation path and the production rule path can share an acceptance function. Isolation remains structural.
- Benchmark code can mix solver latency with expression execution time if both are written into one duration field. Phase 6 stores them as separate fields and rejects §10.2 spurious speedup claims in helpers.
- Generated cases can leak between development and held-out partitions; Phase 5 adds key checks, which must stay enforced.
- Streamlit code can start calling the solver directly. Then limits, classification, and audit records will differ between the API and the UI.
- Exact replay may fail because of solver or platform nondeterminism (disclosed; audit replay restores configuration, not bit-identical timings).
- Passing Hypothesis or mutation suites is not a proof of equivalence (documented limitation).
- Fixture metric tests must not be mistaken for research findings.
- Audit exports must keep linking `result_ref` / `result_link` to raw records; derived charts must not be mixed into `raw/`.

Expression meaning is specified in `docs/SEMANTICS.md`. The Phase 2 encoding is specified in `docs/FORMAL_MODEL.md`. The Phase 5 protocol is specified in `docs/EXPERIMENT_PROTOCOL.md`. Phase 6 benchmarking is implemented in `veriforge/benchmark_engine.py`. Phase 7 audit is implemented in `veriforge/audit_engine.py`. Phase 8 UI is implemented in `veriforge/app.py` and `veriforge/ui/`. Phase 9 security is implemented in `veriforge/security.py` and documented in `docs/SECURITY.md`.
