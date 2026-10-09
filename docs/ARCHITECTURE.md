# Architecture

Status: Phase 1 semantic foundation and Phase 2 formal verification are implemented. Later-phase components remain planned only.

## Implemented

| Boundary | Responsibility | Status |
| --- | --- | --- |
| Parser | Parse one expression with Python's `ast` module. Do not execute it. Accept only the initial grammar. Reject every other form. Enforce resource limits. | Implemented: `veriforge/parser_engine.py` |
| Semantics / configuration | Hold the selected mode and Mode B bit width. Defaults and limits from the locked Phase 1 decisions. | Implemented: `veriforge/config.py`, `veriforge/semantics.py` |
| Reference evaluator | Evaluate a supported expression under the selected mode without using Z3. | Implemented: `veriforge/reference_evaluator.py` |
| Verifier | Translate original and candidate into the Z3 sort for the active mode. Ask whether an input exists that makes them differ. Classify the solver outcome. Independently validate counterexamples. Do not treat the solver result as proof that the application is correct. | Implemented: `veriforge/verifier_engine.py` |
| Typed models / exceptions | Phase 1 records plus Phase 2 `VerificationResult` / `Counterexample` and translation/verification errors. | Implemented: `veriforge/models.py`, `veriforge/exceptions.py` |

Package layout present after Phase 2:

```
veriforge/
    __init__.py
    config.py
    models.py
    exceptions.py
    parser_engine.py
    semantics.py
    reference_evaluator.py
    verifier_engine.py
tests/
    unit/
docs/
pyproject.toml
requirements.lock
```

Empty placeholders for later phases were not created.

## Verifier data flow

1. Accept original and candidate as source strings or parsed `Expression` values under one `SemanticConfiguration`.
2. Parse/validate (fail closed → `INVALID_INPUT` or `UNSUPPORTED`).
3. Translate both IR trees to Z3: Mode A → `Int`; Mode B → `BitVec(w)`.
4. Assert `[[E_o]] ≠ [[E_c]]` and `check` with the configured timeout (default 5s).
5. Classify `unsat` / `sat` / `unknown` into explicit `VerificationStatus` values.
6. On `sat`, extract the model, evaluate both expressions with the reference evaluator, and emit `COUNTEREXAMPLE_FOUND` only when outputs differ.

## Planned boundaries (not implemented)

Logic and presentation stay separate. Streamlit is the specified interface. It calls application functions. It does not own parsing, optimization, or verification.

| Boundary | Specified responsibility | Status |
| --- | --- | --- |
| Optimizer | Apply a small set of identifiable, conservative rules. Record preconditions and a full trace. Accept a candidate on the default path only after the required equivalence check. | Not implemented |
| Mutation facility | Generate incorrect candidates for detection tests. Keep them labeled, seeded, and off the production rule set. They must not bypass verification. | Not implemented |
| Benchmarks | Store correctness outcomes separately from timing. Solver time and expression execution time are different measurements. | Not implemented |
| Datasets and experiments | Versioned cases, separate development and held-out partitions, run identifiers, configuration fingerprints, raw observations. | Not implemented |
| Audit and storage | Persist the run record required by section 13. Initial store for metadata: SQLite. Large raw artifacts stored separately. Export JSON or CSV. No secrets. | Not implemented |
| Interface | Six pages: expression workbench, verification explorer, fuzzing and mutation lab, benchmark lab, research dashboard, audit and reproducibility. Unavailable features show an unavailable state. No fabricated results. | Not implemented |

Typed records named by the specification that remain unimplemented as code: `OptimizationRule`, `TransformationStep`, `OptimizationResult`, `FuzzCase`, `MutationRecord`, `BenchmarkConfiguration`, `BenchmarkMeasurement`, `ExperimentRun`, `AuditEvent`, `DatasetMetadata`, `ResearchClaim`. Implemented through Phase 2: `ExpressionInput`, `SemanticConfiguration`, `VerificationResult`, `Counterexample`, and the expression IR.

Two experimental configurations are specified and must stay distinct:

- Verification-guided mode. Candidates pass the required equivalence checks before acceptance. This is the default application mode.
- Evaluation-only mode. Deliberately incorrect candidates may be analyzed in a controlled harness. They are never silently accepted into the production path.

Verification states remain distinct: `EQUIVALENT_WITHIN_MODEL`, `COUNTEREXAMPLE_FOUND`, `UNKNOWN`, `TIMEOUT`, `UNSUPPORTED`, `INVALID_INPUT`, `TRANSLATION_ERROR`, and `VERIFICATION_ERROR`. A Boolean success flag is not an acceptable substitute.

Trusted computing base assumptions for Phase 2 are written in `docs/FORMAL_MODEL.md` and summarized in `docs/LIMITATIONS.md`.

Out of scope until a later phase shows a need: distributed infrastructure, cloud services, and deployment machinery.

## Known architectural risks

- The verifier, the optimizer, and the reference evaluator can drift apart if they do not share one semantic configuration object and one grammar. Phase 2 reuses the Phase 1 configuration, grammar, and reference evaluator.
- Mode B can be implemented as unbounded Python integers by mistake. Phase 1's reference evaluator applies modular wrap; Phase 2 uses Z3 bit-vector sorts of the configured width.
- `UNKNOWN` and timeout can be collapsed into "not SAT" and then displayed as equivalent. The result type makes that collapse a type error, not a presentation choice.
- The mutation path and the production rule path can share an acceptance function. Isolation has to be structural, not a naming convention (Phase 3+).
- Benchmark code can mix solver latency with expression execution time if both are written into one duration field.
- Generated cases can leak between development and held-out partitions if dataset construction and experiment execution share a writable directory without a partition check.
- Streamlit code can start calling the solver directly. Then limits, classification, and audit records will differ between the API and the UI.
- Exact replay may fail because of solver or platform nondeterminism. The reproduction path has to record that limitation instead of promising bit-for-bit output.

Expression meaning is specified in `docs/SEMANTICS.md`. The Phase 2 encoding is specified in `docs/FORMAL_MODEL.md`.
