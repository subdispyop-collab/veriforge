# Architecture

Status: planned boundaries only. Nothing in this document is implemented unless a later phase says so after code exists.

Current status on 2026-10-09: no package tree, no modules, no storage, no interface, and no tests. The diagram in section 11 of the controlling specification was not created as directories or files. Section 11 says not to add empty modules only to match that diagram, and this phase stops at the audit.

## Planned boundaries

Logic and presentation stay separate. Streamlit is the specified interface. It calls application functions. It does not own parsing, optimization, or verification.

| Boundary | Specified responsibility | Status |
| --- | --- | --- |
| Parser | Parse one expression with Python's `ast` module. Do not execute it. Accept only the initial grammar. Reject every other form. | Not implemented |
| Semantics | Hold the selected mode, and the bit width when the mode is fixed-width. Mode A is mathematical integers. Mode B is bit-vectors, initial width 32. | Not implemented |
| Reference evaluator | Evaluate a supported expression under the selected mode without using Z3. Used to check counterexamples and differential tests. | Not implemented |
| Optimizer | Apply a small set of identifiable, conservative rules. Record preconditions and a full trace. Accept a candidate on the default path only after the required equivalence check. | Not implemented |
| Mutation facility | Generate incorrect candidates for detection tests. Keep them labeled, seeded, and off the production rule set. They must not bypass verification. | Not implemented |
| Verifier | Translate original and candidate into the Z3 sort for the active mode. Ask whether an input exists that makes them differ. Classify the solver outcome. Do not treat the solver result as proof that the application is correct. | Not implemented |
| Benchmarks | Store correctness outcomes separately from timing. Solver time and expression execution time are different measurements. | Not implemented |
| Datasets and experiments | Versioned cases, separate development and held-out partitions, run identifiers, configuration fingerprints, raw observations. | Not implemented |
| Audit and storage | Persist the run record required by section 13. Initial store for metadata: SQLite. Large raw artifacts stored separately. Export JSON or CSV. No secrets. | Not implemented |
| Interface | Six pages: expression workbench, verification explorer, fuzzing and mutation lab, benchmark lab, research dashboard, audit and reproducibility. Unavailable features show an unavailable state. No fabricated results. | Not implemented |

Planned module names from the specification, none of which exist yet: `parser_engine`, `semantics`, `reference_evaluator`, `optimizer_engine`, `verifier_engine`, `fuzzer_suite`, `benchmark_engine`, `audit_engine`, `dataset_engine`, `experiment_engine`, plus configuration, typed models, specific exceptions, logging, a Streamlit `ui` package, and a `storage` package. Tests are planned under `tests/` with separate suites for the categories in section 8.2. Scripts, datasets, and experiment directories are planned and were not created.

Typed records named by the specification, not defined as code: `ExpressionInput`, `SemanticConfiguration`, `OptimizationRule`, `TransformationStep`, `OptimizationResult`, `VerificationResult`, `Counterexample`, `FuzzCase`, `MutationRecord`, `BenchmarkConfiguration`, `BenchmarkMeasurement`, `ExperimentRun`, `AuditEvent`, `DatasetMetadata`, `ResearchClaim`. Field-level schemas are not invented in this phase. Section 13 already lists what a run must preserve; that list is the content requirement when storage is built.

Two experimental configurations are specified and must stay distinct:

- Verification-guided mode. Candidates pass the required equivalence checks before acceptance. This is the default application mode.
- Evaluation-only mode. Deliberately incorrect candidates may be analyzed in a controlled harness. They are never silently accepted into the production path.

Verification states must remain distinct. The specified states are `EQUIVALENT_WITHIN_MODEL`, `COUNTEREXAMPLE_FOUND`, `UNKNOWN`, `TIMEOUT`, `UNSUPPORTED`, `INVALID_INPUT`, `TRANSLATION_ERROR`, and `VERIFICATION_ERROR`. A Boolean success flag is not an acceptable substitute.

Specified interpretation of solver outcomes:

| Solver result | Specified interpretation |
| --- | --- |
| UNSAT | Equivalent within the encoded model and assumptions |
| SAT | A counterexample exists within the encoded model |
| UNKNOWN | Equivalence remains undetermined |
| Timeout or interruption | Verification incomplete |
| Translation failure | Verification could not be performed |
| Unsupported expression | No verification claim may be made |

A confirmed counterexample requires extraction, reconstruction, and evaluation by the reference evaluator under the same semantic configuration. If that check cannot be done, or the outputs do not differ, the example is not displayed as confirmed.

The trusted computing base is not established. No component exists on which a correctness claim could depend.

Out of scope until a later phase shows a need: distributed infrastructure, cloud services, and deployment machinery. The specification says not to add them without a demonstrated need. None has been demonstrated.

## Known architectural risks

- The verifier, the optimizer, and the reference evaluator can drift apart if they do not share one semantic configuration object and one grammar.
- Mode B can be implemented as unbounded Python integers by mistake. That would erase wrapping and make equivalence checks look stronger than the machine model.
- Signedness and literal conversion for Mode B are unspecified. An architecture that stores only a width, without an explicit interpretation and conversion rule, cannot support an honest Mode B claim.
- `UNKNOWN` and timeout can be collapsed into "not SAT" and then displayed as equivalent. The result type has to make that collapse a type error, not a presentation choice.
- The mutation path and the production rule path can share an acceptance function. Isolation has to be structural, not a naming convention.
- Benchmark code can mix solver latency with expression execution time if both are written into one duration field.
- Generated cases can leak between development and held-out partitions if dataset construction and experiment execution share a writable directory without a partition check.
- Streamlit code can start calling the solver directly. Then limits, classification, and audit records will differ between the API and the UI.
- SQLite can become a place where raw artifacts, summaries, and secrets are mixed. The specification separates metadata, raw artifacts, and derived charts, and it forbids secrets in experiment artifacts.
- Host Python is 3.12.3, and the specified libraries are not installed. The process boundary assumes a locked environment that does not exist yet. Behavior of Z3 timeouts and UNKNOWN on that future pin is unverified.
- Exact replay may fail because of solver or platform nondeterminism. The reproduction path has to record that limitation instead of promising bit-for-bit output.

Risks that are assumptions about mathematical validity of particular rules are listed in `PROJECT_STATUS.md`. Expression meaning is specified, not implemented, in `docs/SEMANTICS.md`.
