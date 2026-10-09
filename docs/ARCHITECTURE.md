# Architecture

Status: Phases 1–5 are implemented (semantic foundation, formal verification, conservative optimizer, adversarial validation, experimental framework). Later-phase components remain planned only.

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
| Typed models / exceptions | Phase 1–5 records including dataset, experiment, and metric types. | Implemented: `veriforge/models.py`, `veriforge/exceptions.py` |

Package layout present after Phase 5:

```
veriforge/
    __init__.py
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
    storage/
        __init__.py
        database.py
datasets/
    README.md
    development/
    held_out/
experiments/
    protocols/
    configurations/
    raw/
    reports/
tests/
    unit/
    properties/
    adversarial/
    regression/
docs/
scripts/
    seed_phase5_datasets.py
pyproject.toml
requirements.lock
```

Empty placeholders for unimplemented later phases (Streamlit UI, benchmark engine module) were not created.

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

## Planned boundaries (not implemented)

Logic and presentation stay separate. Streamlit is the specified interface. It calls application functions. It does not own parsing, optimization, or verification.

| Boundary | Specified responsibility | Status |
| --- | --- | --- |
| Benchmarks | Store correctness outcomes separately from timing. Solver time and expression execution time are different measurements. | Not implemented (Phase 6) |
| Audit deepening | Export/replay and richer integrity checks beyond Phase 5 persistence. | Partial (Phase 5 store); full Phase 7 pending |
| Interface | Six pages: expression workbench, verification explorer, fuzzing and mutation lab, benchmark lab, research dashboard, audit and reproducibility. Unavailable features show an unavailable state. No fabricated results. | Not implemented |

Typed records named by the specification still pending as dedicated Phase 6+ products: `FuzzCase`, `BenchmarkConfiguration`, `BenchmarkMeasurement`, `AuditEvent`, `ResearchClaim`. Phase 5 added `DatasetMetadata` / `DatasetCase`, `ExperimentRun`, `RawObservation`, and metric summary types. Earlier phases already provide `ExpressionInput`, `SemanticConfiguration`, `VerificationResult`, `Counterexample`, `OptimizationRule`, `TransformationStep`, `OptimizationResult`, `MutationRecord`, and `MutationAnalysisResult`.

Trusted computing base assumptions for verification are written in `docs/FORMAL_MODEL.md` and summarized in `docs/LIMITATIONS.md`.

Out of scope until a later phase shows a need: distributed infrastructure, cloud services, and deployment machinery.

## Known architectural risks

- The verifier, the optimizer, and the reference evaluator can drift apart if they do not share one semantic configuration object and one grammar.
- Mode B can be implemented as unbounded Python integers by mistake.
- `UNKNOWN` and timeout can be collapsed into "not SAT" and then displayed as equivalent. The result type makes that collapse a type error.
- The mutation path and the production rule path can share an acceptance function. Isolation remains structural.
- Benchmark code can mix solver latency with expression execution time if both are written into one duration field (Phase 6 risk).
- Generated cases can leak between development and held-out partitions; Phase 5 adds key checks, which must stay enforced.
- Streamlit code can start calling the solver directly. Then limits, classification, and audit records will differ between the API and the UI.
- Exact replay may fail because of solver or platform nondeterminism.
- Passing Hypothesis or mutation suites is not a proof of equivalence (documented limitation).
- Fixture metric tests must not be mistaken for research findings.

Expression meaning is specified in `docs/SEMANTICS.md`. The Phase 2 encoding is specified in `docs/FORMAL_MODEL.md`. The Phase 5 protocol is specified in `docs/EXPERIMENT_PROTOCOL.md`.
