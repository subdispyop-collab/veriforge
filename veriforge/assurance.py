"""Audited equivalence pipeline and the authoritative status contract.

Equivalence is reported only when at least one completed establishing check
says the expressions match and every completed check agrees. Timeout,
unknown, unavailable, disagreement, validation failure, and translation
failure never become an equivalent verdict.

A second Z3 encoder is not a separate proof system. Exhaustive enumeration
is a proof only for the finite domain it covered. Polynomial identity is a
proof only for mathematical integers inside the term budget.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from veriforge.config import SemanticConfiguration
from veriforge.exceptions import (
    DomainError,
    InvalidLiteralError,
    MissingVariableError,
    ParseError,
    ResourceLimitError,
    UnsupportedSyntaxError,
    VerificationEngineError,
)
from veriforge.exhaustive_oracle import ExhaustiveResult, exhaustive_compare
from veriforge.independent_encoder import EncoderResult, encode_difference
from veriforge.independent_evaluator import evaluate_independent
from veriforge.independent_parser import (
    IExpr,
    IndependentExpression,
    parse_independent,
)
from veriforge.models import SemanticMode, VerificationStatus
from veriforge.parser_engine import parse_expression
from veriforge.polynomial_oracle import PolynomialResult, polynomial_compare
from veriforge.reference_evaluator import evaluate

DEFAULT_EXHAUSTIVE_BUDGET = 65536
DEFAULT_POLY_BUDGET = 4096


@dataclass(frozen=True, slots=True)
class GateResult:
    """One completed or skipped check."""

    name: str
    verdict: str
    detail: str
    witness: dict[str, int] | None = None
    original_value: int | None = None
    candidate_value: int | None = None
    domain_size: int | None = None
    assignments_evaluated: int | None = None
    elapsed_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class AssuranceReport:
    status: VerificationStatus
    establishing_method: str
    reason: str
    gates: tuple[GateResult, ...]
    mode: str
    bit_width: int | None
    witness: dict[str, int] | None = None
    smt_available: bool = False
    notes: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "establishing_method": self.establishing_method,
            "reason": self.reason,
            "mode": self.mode,
            "bit_width": self.bit_width,
            "witness": self.witness,
            "smt_available": self.smt_available,
            "notes": list(self.notes),
            "gates": [
                {
                    "name": gate.name,
                    "verdict": gate.verdict,
                    "detail": gate.detail,
                    "witness": gate.witness,
                    "original_value": gate.original_value,
                    "candidate_value": gate.candidate_value,
                    "domain_size": gate.domain_size,
                    "assignments_evaluated": gate.assignments_evaluated,
                    "elapsed_seconds": gate.elapsed_seconds,
                }
                for gate in self.gates
            ],
        }


_IGNORED = frozenset({"not_computed", "not_applicable", "unavailable"})
_EQUIV = "equivalent"
_CEX = "counterexample"


def combine_gates(gates: tuple[GateResult, ...] | list[GateResult]) -> tuple[VerificationStatus, str, str]:
    """Apply the status contract. Returns status, establishing method, reason."""

    decisive = [gate for gate in gates if gate.verdict not in _IGNORED]
    if not decisive:
        return (
            VerificationStatus.UNKNOWN,
            "none",
            "no establishing check completed; result is unresolved",
        )

    def has(verdict: str) -> bool:
        return any(gate.verdict == verdict for gate in decisive)

    equiv_names = [gate.name for gate in decisive if gate.verdict == _EQUIV]
    cex_names = [gate.name for gate in decisive if gate.verdict == _CEX]

    if equiv_names and cex_names:
        return (
            VerificationStatus.SEMANTIC_DISAGREEMENT,
            "none",
            "completed checks disagree: "
            + ",".join(equiv_names)
            + " vs "
            + ",".join(cex_names),
        )
    if has("semantic_disagreement"):
        return (
            VerificationStatus.SEMANTIC_DISAGREEMENT,
            "none",
            "a check reported semantic disagreement",
        )
    if cex_names:
        return (
            VerificationStatus.COUNTEREXAMPLE_FOUND,
            cex_names[0],
            "a completed check found a differentiating assignment",
        )
    if has("counterexample_validation_failed"):
        return (
            VerificationStatus.COUNTEREXAMPLE_VALIDATION_FAILED,
            "none",
            "counterexample validation failed",
        )
    if has("invalid_input"):
        if has(_EQUIV) or has("unsupported"):
            return (
                VerificationStatus.SEMANTIC_DISAGREEMENT,
                "none",
                "validity disagrees across checks",
            )
        return (
            VerificationStatus.INVALID_INPUT,
            "none",
            "input rejected",
        )
    if has("unsupported"):
        return (
            VerificationStatus.UNSUPPORTED,
            "none",
            "unsupported syntax",
        )
    if has("translation_error"):
        return (
            VerificationStatus.TRANSLATION_ERROR,
            "none",
            "translation failed",
        )
    if has("verification_error"):
        return (
            VerificationStatus.VERIFICATION_ERROR,
            "none",
            "verification error",
        )
    if has("timeout") and not equiv_names:
        return (
            VerificationStatus.TIMEOUT,
            "none",
            "solver timeout; not an equivalence result",
        )
    if has("unknown") and not equiv_names:
        return (
            VerificationStatus.UNKNOWN,
            "none",
            "solver UNKNOWN; not an equivalence result",
        )
    if equiv_names and all(gate.verdict == _EQUIV for gate in decisive):
        return (
            VerificationStatus.EQUIVALENT_WITHIN_MODEL,
            "+".join(equiv_names),
            "every completed check established equivalence within its model",
        )
    if equiv_names and (has("timeout") or has("unknown")):
        # A separate completed proof may stand, but a conflicting unresolved
        # SMT result must not be dropped silently. Treat this as disagreement
        # about whether equivalence was established by all required channels
        # only when the unresolved check was required. Here the contract is:
        # an independent proof (exhaustive or polynomial) may establish
        # equivalence while an unresolved solver is recorded, because the
        # solver did not contradict it. The establishing method names only
        # the equivalent gates. Timeout is not converted into the verdict;
        # it is absent from establishing_method.
        provers = [
            gate.name
            for gate in decisive
            if gate.verdict == _EQUIV
            and gate.name in {"exhaustive", "polynomial", "production_smt", "independent_encoder"}
        ]
        if provers and not has("timeout") and not has("unknown"):
            return (
                VerificationStatus.EQUIVALENT_WITHIN_MODEL,
                "+".join(provers),
                "establishing checks agree",
            )
        if provers:
            return (
                VerificationStatus.EQUIVALENT_WITHIN_MODEL,
                "+".join(provers),
                "equivalence established by "
                + "+".join(provers)
                + "; unresolved solver status was not used as proof",
            )
    return (
        VerificationStatus.UNKNOWN,
        "none",
        "checks were inconclusive",
    )


def audit_equivalence(
    original_source: str,
    candidate_source: str,
    config: SemanticConfiguration,
    *,
    exhaustive_budget: int = DEFAULT_EXHAUSTIVE_BUDGET,
    polynomial_budget: int = DEFAULT_POLY_BUDGET,
    run_smt: bool = True,
) -> AssuranceReport:
    """Run independent and, when available, SMT checks on one pair."""

    notes: list[str] = []
    gates: list[GateResult] = []
    width = config.bit_width if config.mode is SemanticMode.MODE_B else None

    indy_original, indy_gate = _parse_indy(original_source, config, "independent_parse_original")
    indy_candidate, indy_gate_c = _parse_indy(candidate_source, config, "independent_parse_candidate")
    if indy_gate is not None:
        gates.append(indy_gate)
    if indy_gate_c is not None:
        gates.append(indy_gate_c)

    prod_original_ok, prod_gate = _parse_prod(original_source, config, "production_parse_original")
    prod_candidate_ok, prod_gate_c = _parse_prod(
        candidate_source, config, "production_parse_candidate"
    )
    if prod_gate is not None:
        gates.append(prod_gate)
    if prod_gate_c is not None:
        gates.append(prod_gate_c)

    if indy_original is None or indy_candidate is None or not prod_original_ok or not prod_candidate_ok:
        status, method, reason = combine_gates(gates)
        return AssuranceReport(
            status=status,
            establishing_method=method,
            reason=reason,
            gates=tuple(gates),
            mode=config.mode.value,
            bit_width=width,
            smt_available=False,
            notes=tuple(notes),
        )

    assert indy_original is not None and indy_candidate is not None
    poly: PolynomialResult | None = None
    if config.mode is SemanticMode.MODE_A:
        poly = polynomial_compare(
            indy_original.root,
            indy_candidate.root,
            term_budget=polynomial_budget,
        )
        gates.append(
            GateResult(
                name="polynomial",
                verdict=poly.verdict,
                detail=poly.detail,
                witness=poly.witness,
            )
        )
    else:
        gates.append(
            GateResult(
                name="polynomial",
                verdict="not_applicable",
                detail="polynomial identity is not a Mode B decision procedure",
            )
        )

    exhaustive: ExhaustiveResult = exhaustive_compare(
        indy_original.root,
        indy_candidate.root,
        config,
        assignment_budget=exhaustive_budget,
    )
    gates.append(
        GateResult(
            name="exhaustive",
            verdict=exhaustive.verdict,
            detail=exhaustive.detail,
            witness=exhaustive.witness,
            original_value=exhaustive.original_value,
            candidate_value=exhaustive.candidate_value,
            domain_size=exhaustive.domain_size,
            assignments_evaluated=exhaustive.assignments_evaluated,
            elapsed_seconds=exhaustive.elapsed_seconds,
        )
    )

    smt_available = False
    if run_smt:
        prod_gate_smt, available = _production_smt(original_source, candidate_source, config)
        gates.append(prod_gate_smt)
        smt_available = available
        encoder: EncoderResult = encode_difference(
            indy_original.root,
            indy_candidate.root,
            config,
        )
        gates.append(
            GateResult(
                name="independent_encoder",
                verdict=encoder.verdict,
                detail=encoder.detail,
                witness=encoder.witness,
                elapsed_seconds=encoder.elapsed_seconds,
            )
        )
        if encoder.verdict == "unavailable":
            notes.append("independent Z3 encoder unavailable")
        if not available:
            notes.append("production Z3 verifier unavailable")
    else:
        gates.append(
            GateResult(
                name="production_smt",
                verdict="unavailable",
                detail="SMT path not requested",
            )
        )
        gates.append(
            GateResult(
                name="independent_encoder",
                verdict="unavailable",
                detail="SMT path not requested",
            )
        )

    if poly is not None and poly.witness:
        confirmed = _confirm_witness(indy_original, indy_candidate, poly.witness, config)
        if confirmed is not None:
            gates.append(confirmed)

    status, method, reason = combine_gates(gates)
    witness = _first_witness(gates)
    if status is VerificationStatus.EQUIVALENT_WITHIN_MODEL and "timeout" in {
        gate.verdict for gate in gates
    }:
        notes.append("timeout was recorded and was not the establishing method")
    return AssuranceReport(
        status=status,
        establishing_method=method,
        reason=reason,
        gates=tuple(gates),
        mode=config.mode.value,
        bit_width=width,
        witness=witness,
        smt_available=smt_available,
        notes=tuple(notes),
    )


def _confirm_witness(
    original: IndependentExpression,
    candidate: IndependentExpression,
    witness: dict[str, int],
    config: SemanticConfiguration,
) -> GateResult | None:
    """Re-evaluate a polynomial witness with the concrete evaluator."""

    try:
        left = evaluate_independent(original, witness, config)
        right = evaluate_independent(candidate, witness, config)
    except (DomainError, MissingVariableError, ValueError) as exc:
        return GateResult(
            name="witness_confirmation",
            verdict="counterexample_validation_failed",
            detail=f"witness could not be evaluated: {exc}",
            witness=witness,
        )
    if left != right:
        return GateResult(
            name="witness_confirmation",
            verdict="counterexample",
            detail="concrete evaluator confirms the polynomial witness",
            witness=witness,
            original_value=left,
            candidate_value=right,
        )
    return GateResult(
        name="witness_confirmation",
        verdict="semantic_disagreement",
        detail="polynomial witness did not differentiate concrete values",
        witness=witness,
        original_value=left,
        candidate_value=right,
    )


def _parse_indy(
    source: str,
    config: SemanticConfiguration,
    name: str,
) -> tuple[IndependentExpression | None, GateResult | None]:
    try:
        return parse_independent(source, config), None
    except UnsupportedSyntaxError as exc:
        return None, GateResult(name=name, verdict="unsupported", detail=str(exc))
    except (InvalidLiteralError, ResourceLimitError, ParseError) as exc:
        return None, GateResult(name=name, verdict="invalid_input", detail=str(exc))


def _parse_prod(
    source: str,
    config: SemanticConfiguration,
    name: str,
) -> tuple[bool, GateResult | None]:
    try:
        parse_expression(source, config)
        return True, None
    except UnsupportedSyntaxError as exc:
        return False, GateResult(name=name, verdict="unsupported", detail=str(exc))
    except (InvalidLiteralError, ResourceLimitError, ParseError) as exc:
        return False, GateResult(name=name, verdict="invalid_input", detail=str(exc))


def _production_smt(
    original_source: str,
    candidate_source: str,
    config: SemanticConfiguration,
) -> tuple[GateResult, bool]:
    try:
        from veriforge.verifier_engine import verify_equivalence
    except Exception as exc:  # noqa: BLE001
        return (
            GateResult(
                name="production_smt",
                verdict="unavailable",
                detail=f"verifier import failed: {exc}",
            ),
            False,
        )
    try:
        result = verify_equivalence(original_source, candidate_source, config)
    except VerificationEngineError as exc:
        return (
            GateResult(name="production_smt", verdict="unavailable", detail=str(exc)),
            False,
        )
    if result.status is VerificationStatus.VERIFICATION_ERROR and result.reason and (
        "not installed" in result.reason or "unavailable" in result.reason
    ):
        return (
            GateResult(
                name="production_smt",
                verdict="unavailable",
                detail=result.reason,
            ),
            False,
        )
    mapping = {
        VerificationStatus.EQUIVALENT_WITHIN_MODEL: "equivalent",
        VerificationStatus.COUNTEREXAMPLE_FOUND: "counterexample",
        VerificationStatus.UNKNOWN: "unknown",
        VerificationStatus.TIMEOUT: "timeout",
        VerificationStatus.UNSUPPORTED: "unsupported",
        VerificationStatus.INVALID_INPUT: "invalid_input",
        VerificationStatus.TRANSLATION_ERROR: "translation_error",
        VerificationStatus.VERIFICATION_ERROR: "verification_error",
        VerificationStatus.COUNTEREXAMPLE_VALIDATION_FAILED: (
            "counterexample_validation_failed"
        ),
        VerificationStatus.SEMANTIC_DISAGREEMENT: "semantic_disagreement",
    }
    witness = None
    if result.counterexample is not None:
        witness = dict(result.counterexample.assignment)
    return (
        GateResult(
            name="production_smt",
            verdict=mapping[result.status],
            detail=result.reason or result.status.value,
            witness=witness,
        ),
        True,
    )


def _first_witness(gates: list[GateResult]) -> dict[str, int] | None:
    for gate in gates:
        if gate.witness and gate.verdict in {"counterexample", "semantic_disagreement"}:
            return dict(gate.witness)
    return None


def concrete_values_agree(
    source: str,
    assignment: dict[str, int],
    config: SemanticConfiguration,
) -> tuple[bool, int | None, int | None, str]:
    """Compare production and independent evaluators on one assignment.

    Returns agreement, production value, independent value, and detail.
    Parser disagreement is agreement=False.
    """

    try:
        indy = parse_independent(source, config)
        indy_value = evaluate_independent(indy, assignment, config)
    except Exception as exc:  # noqa: BLE001
        return False, None, None, f"independent path failed: {exc}"
    try:
        prod = parse_expression(source, config)
        prod_value = evaluate(prod, assignment, config)
    except Exception as exc:  # noqa: BLE001
        return False, None, indy_value, f"production path failed: {exc}"
    if prod_value != indy_value:
        return (
            False,
            prod_value,
            indy_value,
            f"evaluator disagreement {prod_value} vs {indy_value}",
        )
    return True, prod_value, indy_value, "evaluators agree on this assignment"
