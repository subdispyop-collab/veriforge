# Architecture

Status: Phase 1 semantic foundation is implemented. Later-phase components remain planned only.

## Implemented in Phase 1

| Boundary | Responsibility | Status |
| --- | --- | --- |
| Parser | Parse one expression with Python's `ast` module. Do not execute it. Accept only the initial grammar. Reject every other form. Enforce resource limits. | Implemented: `veriforge/parser_engine.py` |
| Semantics / configuration | Hold the selected mode and Mode B bit width. Defaults and limits from the locked Phase 1 decisions. | Implemented: `veriforge/config.py`, `veriforge/semantics.py` |
| Reference evaluator | Evaluate a supported expression under the selected mode without using Z3. | Implemented: `veriforge/reference_evaluator.py` |
| Typed models / exceptions | Phase 1 records and classified errors. | Implemented: `veriforge/models.py`, `veriforge/exceptions.py` |

Package layout present after Phase 1:

```
veriforge/
    __init__.py
    config.py
    models.py
    exceptions.py
    parser_engine.py
    semantics.py
    reference_evaluator.py
tests/
    unit/
docs/
pyproject.toml
requirements.lock
```

Empty placeholders for later phases were not created.

## Planned boundaries (not implemented)

Logic and presentation stay separate. Streamlit is the specified interface. It calls application functions. It does not own parsing, optimization, or verification.

| Boundary | Specified responsibility | Status |
| --- | --- | --- |
| Optimizer | Apply a small set of identifiable, conservative rules. Record preconditions and a full trace. Accept a candidate on the default path only after the required equivalence check. | Not implemented |
| Mutation facility | Generate incorrect candidates for detection tests. Keep them labeled, seeded, and off the production rule set. They must not bypass verification. | Not implemented |
| Verifier | Translate original and candidate into the Z3 sort for the active mode. Ask whether an input exists that makes them differ. Classify the solver outcome. Do not treat the solver result as proof that the application is correct. | Not implemented |
| Benchmarks | Store correctness outcomes separately from timing. Solver time and expression execution time are different measurements. | Not implemented |
| Datasets and experiments | Versioned cases, separate development and held-out partitions, run identifiers, configuration fingerprints, raw observations. | Not implemented |
| Audit and storage | Persist the run record required by section 13. Initial store for metadata: SQLite. Large raw artifacts stored separately. Export JSON or CSV. No secrets. | Not implemented |
| Interface | Six pages: expression workbench, verification explorer, fuzzing and mutation lab, benchmark lab, research dashboard, audit and reproducibility. Unavailable features show an unavailable state. No fabricated results. | Not implemented |

Typed records named by the specification that remain unimplemented as code: `OptimizationRule`, `TransformationStep`, `OptimizationResult`, `VerificationResult`, `Counterexample`, `FuzzCase`, `MutationRecord`, `BenchmarkConfiguration`, `BenchmarkMeasurement`, `ExperimentRun`, `AuditEvent`, `DatasetMetadata`, `ResearchClaim`. Phase 1 defines `ExpressionInput`, `SemanticConfiguration`, and the expression IR used by the parser and evaluator.

Two experimental configurations are specified and must stay distinct:

- Verification-guided mode. Candidates pass the required equivalence checks before acceptance. This is the default application mode.
- Evaluation-only mode. Deliberately incorrect candidates may be analyzed in a controlled harness. They are never silently accepted into the production path.

Verification states must remain distinct. The specified states are `EQUIVALENT_WITHIN_MODEL`, `COUNTEREXAMPLE_FOUND`, `UNKNOWN`, `TIMEOUT`, `UNSUPPORTED`, `INVALID_INPUT`, `TRANSLATION_ERROR`, and `VERIFICATION_ERROR`. A Boolean success flag is not an acceptable substitute.

A confirmed counterexample requires extraction, reconstruction, and evaluation by the reference evaluator under the same semantic configuration. If that check cannot be done, or the outputs do not differ, the example is not displayed as confirmed.

Trusted computing base for Phase 1 claims about expression meaning: Python's `ast` module, the VERIFORGE parser validation layer, the documented Mode A / Mode B contract in `docs/SEMANTICS.md`, and the reference evaluator. Z3 is not part of the Phase 1 TCB.

Out of scope until a later phase shows a need: distributed infrastructure, cloud services, and deployment machinery.

## Known architectural risks

- The verifier, the optimizer, and the reference evaluator can drift apart if they do not share one semantic configuration object and one grammar. Phase 1 established the shared configuration and grammar; Phase 2 must reuse them.
- Mode B can be implemented as unbounded Python integers by mistake. Phase 1's reference evaluator applies modular wrap and rejects out-of-range literals; later modules must not bypass that.
- `UNKNOWN` and timeout can be collapsed into "not SAT" and then displayed as equivalent. The result type has to make that collapse a type error, not a presentation choice.
- The mutation path and the production rule path can share an acceptance function. Isolation has to be structural, not a naming convention.
- Benchmark code can mix solver latency with expression execution time if both are written into one duration field.
- Generated cases can leak between development and held-out partitions if dataset construction and experiment execution share a writable directory without a partition check.
- Streamlit code can start calling the solver directly. Then limits, classification, and audit records will differ between the API and the UI.
- Exact replay may fail because of solver or platform nondeterminism. The reproduction path has to record that limitation instead of promising bit-for-bit output.

Expression meaning is specified and Phase-1-implemented in `docs/SEMANTICS.md`.
