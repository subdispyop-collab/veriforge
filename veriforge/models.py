"""Typed models used by Phases 1–4: parsing, verification, optimization, mutations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Mapping, Union

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
