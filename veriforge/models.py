"""Typed models used by Phases 1–5: parsing, verification, optimization, mutations, experiments."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Mapping, Union

if TYPE_CHECKING:
    from veriforge.config import SemanticConfiguration


class SemanticMode(Enum):
    """Explicit semantic mode selection."""

    MODE_A = "mode_a"
    MODE_B = "mode_b"


class UnaryOperator(Enum):
    PLUS = "plus"
    MINUS = "minus"


class BinaryOperator(Enum):
    ADD = "add"
    SUB = "sub"
    MUL = "mul"


class VerificationStatus(Enum):
    """Explicit verifier outcomes. Never collapse these to a Boolean."""

    EQUIVALENT_WITHIN_MODEL = "equivalent_within_model"
    COUNTEREXAMPLE_FOUND = "counterexample_found"
    UNKNOWN = "unknown"
    TIMEOUT = "timeout"
    UNSUPPORTED = "unsupported"
    INVALID_INPUT = "invalid_input"
    TRANSLATION_ERROR = "translation_error"
    VERIFICATION_ERROR = "verification_error"


class CounterexampleValidationStatus(Enum):
    """Independent reference-evaluator check of a solver model."""

    CONFIRMED = "confirmed"
    DISCREPANCY = "discrepancy"
    UNVALIDATABLE = "unvalidatable"


class CorrectnessPolicy(Enum):
    """How the optimizer decides whether a candidate may be accepted.

    ``VERIFICATION_GUIDED`` is the default production path: a candidate is
    accepted only when the Phase 2 verifier reports
    ``EQUIVALENT_WITHIN_MODEL``.

    ``EVALUATION_ONLY`` marks analysis of deliberately incorrect candidates
    in the isolated Phase 4 mutation harness (``veriforge.fuzzer_suite``).
    It is not a production acceptance path: ``optimize()`` rejects it, and
    the harness never accepts candidates into the production optimizer.
    """

    VERIFICATION_GUIDED = "verification_guided"
    EVALUATION_ONLY = "evaluation_only"


class MutationCategory(Enum):
    """Artificial mutation categories used only by the Phase 4 fuzzer suite.

    These identifiers are never production optimization rule ids.
    """

    LITERAL_PLUS_ONE = "mutation.literal_plus_one"
    ADD_TO_SUB = "mutation.add_to_sub"
    MUL_TO_ADD = "mutation.mul_to_add"
    SWAP_SUB_OPERANDS = "mutation.swap_sub_operands"
    DROP_RIGHT_OF_ADD = "mutation.drop_right_of_add"
    ZERO_TO_ONE = "mutation.zero_to_one"


class VerificationPolicy(Enum):
    """Per-rule requirement for accepting a rewrite under verification guidance."""

    REQUIRE_EQUIVALENT_WITHIN_MODEL = "require_equivalent_within_model"


class CandidateDecision(Enum):
    """Outcome recorded for one generated optimization candidate."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class IntLiteral:
    """A non-Boolean integer constant accepted by the grammar."""

    value: int


@dataclass(frozen=True, slots=True)
class Variable:
    """A symbolic variable name (not a Python object lookup)."""

    name: str


@dataclass(frozen=True, slots=True)
class UnaryOp:
    op: UnaryOperator
    operand: Expr


@dataclass(frozen=True, slots=True)
class BinaryOp:
    op: BinaryOperator
    left: Expr
    right: Expr


Expr = Union[IntLiteral, Variable, UnaryOp, BinaryOp]


@dataclass(frozen=True, slots=True)
class Expression:
    """A successfully parsed expression in the internal representation."""

    source: str
    root: Expr
    variables: frozenset[str]


@dataclass(frozen=True, slots=True)
class ExpressionInput:
    """User-supplied expression text together with its semantic configuration."""

    source: str
    config: SemanticConfiguration


Assignment = Mapping[str, int]


@dataclass(frozen=True, slots=True)
class Counterexample:
    """A candidate counterexample with independent validation status.

    Only ``validation_status == CONFIRMED`` may be treated as a confirmed
    counterexample. Discrepancy and unvalidatable outcomes are defects or
    unresolved cases, not confirmed counterexamples.
    """

    assignment: Mapping[str, int]
    original_value: int | None
    candidate_value: int | None
    validation_status: CounterexampleValidationStatus
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """Outcome of an equivalence query under an encoded semantic model.

    ``status`` is always one of the explicit ``VerificationStatus`` values.
    A Boolean success/failure field is intentionally absent.
    """

    status: VerificationStatus
    mode: SemanticMode
    bit_width: int | None
    timeout_seconds: float
    original_source: str | None = None
    candidate_source: str | None = None
    counterexample: Counterexample | None = None
    solver_status: str | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class OptimizationRule:
    """Metadata for one identifiable, auditable rewrite rule.

    The executable matching/rewriting logic lives in the optimizer engine and
    is bound by ``rule_id``. This record carries the audit surface required
    by the specification: identity, description, preconditions, modes, and
    verification policy.
    """

    rule_id: str
    name: str
    formal_description: str
    preconditions: tuple[str, ...]
    supported_modes: frozenset[SemanticMode]
    verification_policy: VerificationPolicy


@dataclass(frozen=True, slots=True)
class TransformationStep:
    """One candidate generation attempt in the optimization trace."""

    step_index: int
    rule_id: str
    rule_name: str
    formal_description: str
    preconditions: tuple[str, ...]
    matched_preconditions: tuple[str, ...]
    supported_modes: frozenset[SemanticMode]
    verification_policy: VerificationPolicy
    before_source: str
    after_source: str
    decision: CandidateDecision
    verification_result: VerificationResult | None
    rejection_reason: str | None = None


@dataclass(frozen=True, slots=True)
class OptimizationResult:
    """Accepted expression plus the complete transformation trace.

    Under the default verification-guided policy, every accepted step has a
    recorded ``VerificationResult`` with status ``EQUIVALENT_WITHIN_MODEL``.
    Rejected candidates and their reasons remain in ``trace``.
    """

    original: Expression
    accepted: Expression
    config: SemanticConfiguration
    policy: CorrectnessPolicy
    trace: tuple[TransformationStep, ...]

    @property
    def accepted_steps(self) -> tuple[TransformationStep, ...]:
        return tuple(
            step for step in self.trace if step.decision is CandidateDecision.ACCEPTED
        )

    @property
    def rejected_steps(self) -> tuple[TransformationStep, ...]:
        return tuple(
            step for step in self.trace if step.decision is CandidateDecision.REJECTED
        )


@dataclass(frozen=True, slots=True)
class MutationRecord:
    """One artificially incorrect candidate for detection testing (§7.2).

    Always marked ``artificial=True``. Never mixed into production rules.
    Reproducible via ``seed`` and ``generation_method``.
    """

    mutation_id: str
    category: MutationCategory
    generation_method: str
    seed: int
    original_source: str
    mutated_source: str
    site_path: tuple[str, ...]
    artificial: bool = True

    def __post_init__(self) -> None:
        if not self.artificial:
            raise ValueError(
                "MutationRecord.artificial must be True; synthetic mutations "
                "must remain explicitly labeled"
            )
        if not self.mutation_id:
            raise ValueError("mutation_id must be non-empty")
        if not self.generation_method:
            raise ValueError("generation_method must be non-empty")


@dataclass(frozen=True, slots=True)
class MutationAnalysisResult:
    """EVALUATION_ONLY analysis of one artificial mutation.

    ``accepted_into_production`` is always False. The harness may observe
    verifier outcomes for deliberately incorrect candidates but must not
    feed them into the production optimizer acceptance path.
    """

    mutation: MutationRecord
    config: SemanticConfiguration
    policy: CorrectnessPolicy
    verification_result: VerificationResult
    detected_as_non_equivalent: bool
    accepted_into_production: bool = False

    def __post_init__(self) -> None:
        if self.policy is not CorrectnessPolicy.EVALUATION_ONLY:
            raise ValueError(
                "MutationAnalysisResult.policy must be EVALUATION_ONLY"
            )
        if self.accepted_into_production:
            raise ValueError(
                "MutationAnalysisResult must never accept into production"
            )


# ---------------------------------------------------------------------------
# Phase 5 — experimental framework
# ---------------------------------------------------------------------------


class DatasetPartition(Enum):
    """Development vs held-out separation (§9.4)."""

    DEVELOPMENT = "development"
    HELD_OUT = "held_out"


class TransformationCategory(Enum):
    """Coarse transformation / case category for stratified reporting."""

    VALID_REWRITE = "valid_rewrite"
    INCORRECT_REWRITE = "incorrect_rewrite"
    BOUNDARY_VALUE = "boundary_value"
    NESTED_EXPRESSION = "nested_expression"
    DIFFICULT_SOLVER = "difficult_solver"
    UNSUPPORTED_OR_MALFORMED = "unsupported_or_malformed"
    REGRESSION = "regression"
    HAND_CHECKED_SEMANTIC = "hand_checked_semantic"
    IDENTITY_PRESERVING = "identity_preserving"
    ARTIFICIAL_MUTATION = "artificial_mutation"


class ExpectedOutcome(Enum):
    """Independently known expected outcome for a dataset case, when known."""

    EQUIVALENT = "equivalent"
    NON_EQUIVALENT = "non_equivalent"
    PARSE_REJECT = "parse_reject"
    UNSUPPORTED = "unsupported"
    UNKNOWN_EXPECTED = "unknown_expected"


class BaselineId(Enum):
    """Named baselines from §9.3. None measured in Phase 5."""

    ORIGINAL_NO_OPTIMIZATION = "baseline.original_no_optimization"
    RULE_BASED_WITHOUT_SMT = "baseline.rule_based_without_smt"
    VERIFICATION_ENABLED = "baseline.verification_enabled"
    TESTING_ONLY_VALIDATION = "baseline.testing_only_validation"
    EXTERNAL_TOOL = "baseline.external_tool"


class ObservationKind(Enum):
    """Kind of raw experimental observation stored for later analysis."""

    EQUIVALENCE_CHECK = "equivalence_check"
    OPTIMIZATION_TRACE = "optimization_trace"
    MUTATION_DETECTION = "mutation_detection"
    PARSE_OUTCOME = "parse_outcome"
    METRIC_FIXTURE = "metric_fixture"


@dataclass(frozen=True, slots=True)
class ComplexityCharacteristics:
    """Complexity descriptors recorded per dataset case (§9.4)."""

    source_length: int
    ast_node_count: int
    nesting_depth: int
    variable_count: int
    operator_count: int
    literal_count: int


@dataclass(frozen=True, slots=True)
class DatasetCase:
    """One versioned research case with §9.4 metadata fields."""

    case_id: str
    original_source: str
    candidate_source: str | None
    semantic_mode: SemanticMode
    bit_width: int | None
    transformation_category: TransformationCategory
    expected_outcome: ExpectedOutcome
    complexity: ComplexityCharacteristics
    inclusion_reason: str
    exclusion_reason: str | None = None
    near_duplicate_key: str | None = None
    notes: str | None = None
    labels: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.case_id:
            raise ValueError("case_id must be non-empty")
        if not self.inclusion_reason and not self.exclusion_reason:
            raise ValueError(
                "each case needs an inclusion_reason or exclusion_reason"
            )


@dataclass(frozen=True, slots=True)
class DatasetMetadata:
    """Dataset-level provenance required by §9.4."""

    dataset_version: str
    generation_procedure: str
    semantic_model: str
    random_seed: int | None
    partition: DatasetPartition
    case_count: int
    created_at_utc: str
    description: str
    controlled_mix: bool = False
    controlled_mix_label: str | None = None

    def __post_init__(self) -> None:
        if not self.dataset_version:
            raise ValueError("dataset_version must be non-empty")
        if self.controlled_mix and not self.controlled_mix_label:
            raise ValueError(
                "controlled_mix datasets must carry an explicit label "
                "(e.g. artificial 90/10 — not real-world prevalence)"
            )


@dataclass(frozen=True, slots=True)
class DatasetBundle:
    """A loaded partition: metadata plus cases."""

    metadata: DatasetMetadata
    cases: tuple[DatasetCase, ...]


@dataclass(frozen=True, slots=True)
class BaselineDefinition:
    """Documented baseline configuration (§9.3). Not a measurement."""

    baseline_id: BaselineId
    name: str
    description: str
    uses_smt_verification: bool
    uses_production_optimizer: bool
    status: str
    selection_notes: str | None = None


@dataclass(frozen=True, slots=True)
class ControlledMixConfiguration:
    """Artificial correct/incorrect mix used only as a controlled test config.

    Must never be presented as an estimate of real-world error prevalence.
    """

    correct_fraction: float
    incorrect_fraction: float
    label: str = (
        "controlled artificial mix — not an estimate of real-world prevalence"
    )

    def __post_init__(self) -> None:
        if abs(self.correct_fraction + self.incorrect_fraction - 1.0) > 1e-9:
            raise ValueError("correct_fraction + incorrect_fraction must be 1.0")
        if self.correct_fraction < 0 or self.incorrect_fraction < 0:
            raise ValueError("fractions must be non-negative")


# Default controlled configuration named by §9.4.
ARTIFICIAL_90_10_MIX = ControlledMixConfiguration(
    correct_fraction=0.9,
    incorrect_fraction=0.1,
)


@dataclass(frozen=True, slots=True)
class ExperimentRun:
    """One experiment run with unique id and configuration fingerprint (§12)."""

    run_id: str
    created_at_utc: str
    protocol_version: str
    software_version: str
    configuration_fingerprint: str
    baseline_id: BaselineId | None
    dataset_version: str | None
    dataset_partition: DatasetPartition | None
    random_seed: int | None
    semantic_mode: SemanticMode | None
    bit_width: int | None
    configuration: Mapping[str, Any]
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("run_id must be non-empty")
        if not self.configuration_fingerprint:
            raise ValueError("configuration_fingerprint must be non-empty")


@dataclass(frozen=True, slots=True)
class RawObservation:
    """One raw experimental observation preserved separately from summaries."""

    observation_id: str
    run_id: str
    case_id: str | None
    kind: ObservationKind
    transformation_category: TransformationCategory | None
    verification_status: VerificationStatus | None
    detected_as_non_equivalent: bool | None
    expected_outcome: ExpectedOutcome | None
    payload: Mapping[str, Any]
    recorded_at_utc: str

    def __post_init__(self) -> None:
        if not self.observation_id:
            raise ValueError("observation_id must be non-empty")
        if not self.run_id:
            raise ValueError("run_id must be non-empty")


@dataclass(frozen=True, slots=True)
class ClassMetricRow:
    """Per-class / per-category metric row derived from raw observations."""

    class_key: str
    sample_count: int
    detected_count: int
    undetected_count: int
    equivalent_count: int
    counterexample_count: int
    timeout_count: int
    unknown_count: int
    other_count: int
    detection_rate: float | None
    timeout_rate: float | None
    unknown_rate: float | None


@dataclass(frozen=True, slots=True)
class MetricSummary:
    """Aggregate metrics computed only from stored raw observations.

    Phase 5 validates the calculation functions against known fixture cases.
    This type does not assert that a research experiment was completed.
    """

    run_id: str
    observation_count: int
    by_class: tuple[ClassMetricRow, ...]
    overall: ClassMetricRow
    computed_from: str = "raw_observations"
