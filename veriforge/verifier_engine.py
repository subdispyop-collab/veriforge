"""Z3 equivalence checking for Phase 2.

Translates the Phase 1 expression IR into Z3 under the selected semantic mode,
asks whether an input exists that makes the original and candidate differ,
classifies the solver outcome into explicit states, and independently validates
SAT models with the reference evaluator before confirming a counterexample.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

try:
    import z3
except ImportError:  # solver is optional at import time; checks fail closed
    z3 = None  # type: ignore[assignment]

from veriforge.config import SemanticConfiguration
from veriforge.exceptions import (
    InvalidLiteralError,
    ParseError,
    ResourceLimitError,
    TranslationError,
    UnapprovedASTNodeError,
    UnsupportedSyntaxError,
    VerificationEngineError,
)
from veriforge.models import (
    BinaryOp,
    BinaryOperator,
    Counterexample,
    CounterexampleValidationStatus,
    Expr,
    Expression,
    IntLiteral,
    SemanticMode,
    UnaryOp,
    UnaryOperator,
    Variable,
    VerificationResult,
    VerificationStatus,
)
from veriforge.parser_engine import parse_expression
from veriforge.reference_evaluator import evaluate

def _require_z3():
    """Return the z3 module or fail closed if it is not installed."""

    if z3 is None:
        raise VerificationEngineError(
            "z3-solver is not installed; SMT equivalence checking is unavailable"
        )
    return z3


# Z3 check outcomes that indicate a configured timeout or interruption.
_TIMEOUT_REASON_MARKERS: tuple[str, ...] = (
    "timeout",
    "canceled",
    "cancelled",
    "interrupted",
)


def verify_equivalence(
    original: Expression | str,
    candidate: Expression | str,
    config: SemanticConfiguration,
) -> VerificationResult:
    """Ask whether there exists an input where ``original`` and ``candidate`` differ.

    The query is ``exists x: E_o(x) != E_c(x)`` under ``config``. Results are
    always one of the explicit ``VerificationStatus`` values.
    """

    timed = verify_equivalence_timed(original, candidate, config)
    return timed.result


@dataclass(frozen=True, slots=True)
class TimedVerificationResult:
    """Verification outcome with translation and solver times stored separately.

    ``end_to_end_seconds`` covers parse/coerce through classification. Solver
    latency and expression execution time remain distinct measurements (§10).
    """

    result: VerificationResult
    parsing_seconds: float | None
    translation_seconds: float | None
    solver_seconds: float | None
    end_to_end_seconds: float


def verify_equivalence_timed(
    original: Expression | str,
    candidate: Expression | str,
    config: SemanticConfiguration,
) -> TimedVerificationResult:
    """Equivalence check with independently measured stage timings (§10)."""

    from time import perf_counter

    timeout_seconds = config.limits.solver_timeout_seconds
    bit_width = config.bit_width if config.mode is SemanticMode.MODE_B else None
    e2e_start = perf_counter()
    parsing_seconds: float | None = None
    translation_seconds: float | None = None
    solver_seconds: float | None = None

    try:
        parse_start = perf_counter()
        original_expr, original_source = _coerce_expression(original, config)
        candidate_expr, candidate_source = _coerce_expression(candidate, config)
        parsing_seconds = perf_counter() - parse_start
    except (UnsupportedSyntaxError, UnapprovedASTNodeError) as exc:
        result = VerificationResult(
            status=VerificationStatus.UNSUPPORTED,
            mode=config.mode,
            bit_width=bit_width,
            timeout_seconds=timeout_seconds,
            original_source=_source_of(original),
            candidate_source=_source_of(candidate),
            reason=str(exc),
        )
        return TimedVerificationResult(
            result=result,
            parsing_seconds=parsing_seconds,
            translation_seconds=None,
            solver_seconds=None,
            end_to_end_seconds=perf_counter() - e2e_start,
        )
    except (ResourceLimitError, InvalidLiteralError, ParseError) as exc:
        result = VerificationResult(
            status=VerificationStatus.INVALID_INPUT,
            mode=config.mode,
            bit_width=bit_width,
            timeout_seconds=timeout_seconds,
            original_source=_source_of(original),
            candidate_source=_source_of(candidate),
            reason=str(exc),
        )
        return TimedVerificationResult(
            result=result,
            parsing_seconds=parsing_seconds,
            translation_seconds=None,
            solver_seconds=None,
            end_to_end_seconds=perf_counter() - e2e_start,
        )

    try:
        result, translation_seconds, solver_seconds = _solve_difference_timed(
            original_expr,
            candidate_expr,
            config,
            original_source=original_source,
            candidate_source=candidate_source,
        )
        return TimedVerificationResult(
            result=result,
            parsing_seconds=parsing_seconds,
            translation_seconds=translation_seconds,
            solver_seconds=solver_seconds,
            end_to_end_seconds=perf_counter() - e2e_start,
        )
    except TranslationError as exc:
        result = VerificationResult(
            status=VerificationStatus.TRANSLATION_ERROR,
            mode=config.mode,
            bit_width=bit_width,
            timeout_seconds=timeout_seconds,
            original_source=original_source,
            candidate_source=candidate_source,
            reason=str(exc),
        )
    except VerificationEngineError as exc:
        result = VerificationResult(
            status=VerificationStatus.VERIFICATION_ERROR,
            mode=config.mode,
            bit_width=bit_width,
            timeout_seconds=timeout_seconds,
            original_source=original_source,
            candidate_source=candidate_source,
            reason=str(exc),
        )
    except Exception as exc:  # noqa: BLE001 — classify unexpected solver failures
        result = VerificationResult(
            status=VerificationStatus.VERIFICATION_ERROR,
            mode=config.mode,
            bit_width=bit_width,
            timeout_seconds=timeout_seconds,
            original_source=original_source,
            candidate_source=candidate_source,
            reason=f"unexpected verification failure: {exc}",
        )
    return TimedVerificationResult(
        result=result,
        parsing_seconds=parsing_seconds,
        translation_seconds=translation_seconds,
        solver_seconds=solver_seconds,
        end_to_end_seconds=perf_counter() - e2e_start,
    )


def translate_to_z3(
    expression: Expression,
    config: SemanticConfiguration,
    symbols: Mapping[str, z3.ExprRef] | None = None,
) -> tuple[z3.ExprRef, dict[str, z3.ExprRef]]:
    """Translate a parsed expression into a Z3 term for the active mode.

    Mode A uses integer sorts. Mode B uses bit-vector sorts of ``config.bit_width``.
    Returns the Z3 term and the symbol map (created or reused).
    """

    _require_z3()
    env: dict[str, z3.ExprRef]
    if symbols is None:
        env = {
            name: _fresh_symbol(name, config) for name in sorted(expression.variables)
        }
    else:
        env = dict(symbols)
        for name in expression.variables:
            if name not in env:
                env[name] = _fresh_symbol(name, config)

    try:
        term = _translate_node(expression.root, config, env)
    except TranslationError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise TranslationError(f"translation failed: {exc}") from exc
    return term, env


def classify_check_result(
    check_result: z3.CheckSatResult,
    reason_unknown: str | None = None,
) -> VerificationStatus:
    """Map a raw Z3 ``check`` outcome to an explicit verification status.

    ``sat`` is classified here as a provisional counterexample signal; callers
    must still validate the model before emitting ``COUNTEREXAMPLE_FOUND``.
    """

    z3mod = _require_z3()
    if check_result == z3mod.unsat:
        return VerificationStatus.EQUIVALENT_WITHIN_MODEL
    if check_result == z3mod.sat:
        return VerificationStatus.COUNTEREXAMPLE_FOUND
    if check_result == z3mod.unknown:
        reason = (reason_unknown or "").lower()
        if any(marker in reason for marker in _TIMEOUT_REASON_MARKERS):
            return VerificationStatus.TIMEOUT
        return VerificationStatus.UNKNOWN
    raise VerificationEngineError(
        f"unrecognized solver check result: {check_result!r}"
    )


def _solve_difference(
    original: Expression,
    candidate: Expression,
    config: SemanticConfiguration,
    *,
    original_source: str,
    candidate_source: str,
) -> VerificationResult:
    result, _translation, _solver = _solve_difference_timed(
        original,
        candidate,
        config,
        original_source=original_source,
        candidate_source=candidate_source,
    )
    return result


def _solve_difference_timed(
    original: Expression,
    candidate: Expression,
    config: SemanticConfiguration,
    *,
    original_source: str,
    candidate_source: str,
) -> tuple[VerificationResult, float | None, float | None]:
    from time import perf_counter

    z3mod = _require_z3()
    timeout_seconds = config.limits.solver_timeout_seconds
    bit_width = config.bit_width if config.mode is SemanticMode.MODE_B else None
    names = sorted(original.variables | candidate.variables)
    symbols = {name: _fresh_symbol(name, config) for name in names}

    try:
        t0 = perf_counter()
        original_term, symbols = translate_to_z3(original, config, symbols)
        candidate_term, symbols = translate_to_z3(candidate, config, symbols)
        translation_seconds = perf_counter() - t0
    except TranslationError:
        raise

    if original_term.sort() != candidate_term.sort():
        raise TranslationError(
            "original and candidate translated to incompatible Z3 sorts "
            f"({original_term.sort()} vs {candidate_term.sort()})"
        )

    solver = z3mod.Solver()
    timeout_ms = max(1, int(timeout_seconds * 1000))
    solver.set("timeout", timeout_ms)
    solver.add(original_term != candidate_term)

    t1 = perf_counter()
    check_result = solver.check()
    solver_seconds = perf_counter() - t1
    reason_unknown: str | None = None
    if check_result == z3mod.unknown:
        try:
            reason_unknown = solver.reason_unknown()
        except Exception:  # noqa: BLE001
            reason_unknown = None

    provisional = classify_check_result(check_result, reason_unknown)

    if provisional is VerificationStatus.EQUIVALENT_WITHIN_MODEL:
        return (
            VerificationResult(
                status=VerificationStatus.EQUIVALENT_WITHIN_MODEL,
                mode=config.mode,
                bit_width=bit_width,
                timeout_seconds=timeout_seconds,
                original_source=original_source,
                candidate_source=candidate_source,
                solver_status="unsat",
                reason="no differentiating input within the encoded model",
            ),
            translation_seconds,
            solver_seconds,
        )

    if provisional is VerificationStatus.TIMEOUT:
        return (
            VerificationResult(
                status=VerificationStatus.TIMEOUT,
                mode=config.mode,
                bit_width=bit_width,
                timeout_seconds=timeout_seconds,
                original_source=original_source,
                candidate_source=candidate_source,
                solver_status="unknown",
                reason=reason_unknown or "solver timeout or interruption",
            ),
            translation_seconds,
            solver_seconds,
        )

    if provisional is VerificationStatus.UNKNOWN:
        return (
            VerificationResult(
                status=VerificationStatus.UNKNOWN,
                mode=config.mode,
                bit_width=bit_width,
                timeout_seconds=timeout_seconds,
                original_source=original_source,
                candidate_source=candidate_source,
                solver_status="unknown",
                reason=reason_unknown or "solver returned UNKNOWN",
            ),
            translation_seconds,
            solver_seconds,
        )

    # Provisional COUNTEREXAMPLE_FOUND: extract and independently validate.
    try:
        model = solver.model()
    except Exception as exc:  # noqa: BLE001
        raise VerificationEngineError(
            f"solver reported sat but model extraction failed: {exc}"
        ) from exc

    assignment = _extract_assignment(model, symbols, config)
    counterexample = _validate_counterexample(
        original, candidate, assignment, config
    )

    if counterexample.validation_status is CounterexampleValidationStatus.CONFIRMED:
        return (
            VerificationResult(
                status=VerificationStatus.COUNTEREXAMPLE_FOUND,
                mode=config.mode,
                bit_width=bit_width,
                timeout_seconds=timeout_seconds,
                original_source=original_source,
                candidate_source=candidate_source,
                counterexample=counterexample,
                solver_status="sat",
                reason="solver model independently confirmed by reference evaluator",
            ),
            translation_seconds,
            solver_seconds,
        )

    # Failed validation is a defect / discrepancy, not a confirmed counterexample.
    return (
        VerificationResult(
            status=VerificationStatus.COUNTEREXAMPLE_VALIDATION_FAILED,
            mode=config.mode,
            bit_width=bit_width,
            timeout_seconds=timeout_seconds,
            original_source=original_source,
            candidate_source=candidate_source,
            counterexample=counterexample,
            solver_status="sat",
            reason=(
                "solver reported a differentiating model, but independent "
                "reference validation did not confirm it"
            ),
        ),
        translation_seconds,
        solver_seconds,
    )


def _validate_counterexample(
    original: Expression,
    candidate: Expression,
    assignment: Mapping[str, int],
    config: SemanticConfiguration,
) -> Counterexample:
    try:
        original_value = evaluate(original, assignment, config)
        candidate_value = evaluate(candidate, assignment, config)
    except Exception as exc:  # noqa: BLE001 — any eval failure blocks confirmation
        return Counterexample(
            assignment=dict(assignment),
            original_value=None,
            candidate_value=None,
            validation_status=CounterexampleValidationStatus.UNVALIDATABLE,
            detail=f"reference evaluator could not validate model: {exc}",
        )

    if original_value != candidate_value:
        return Counterexample(
            assignment=dict(assignment),
            original_value=original_value,
            candidate_value=candidate_value,
            validation_status=CounterexampleValidationStatus.CONFIRMED,
            detail=None,
        )

    return Counterexample(
        assignment=dict(assignment),
        original_value=original_value,
        candidate_value=candidate_value,
        validation_status=CounterexampleValidationStatus.DISCREPANCY,
        detail=(
            "solver model does not differentiate the expressions under the "
            "reference evaluator; treating as verification-engine discrepancy"
        ),
    )


def _extract_assignment(
    model: z3.ModelRef,
    symbols: Mapping[str, z3.ExprRef],
    config: SemanticConfiguration,
) -> dict[str, int]:
    assignment: dict[str, int] = {}
    for name, symbol in symbols.items():
        value = model.eval(symbol, model_completion=True)
        try:
            as_int = value.as_long()
        except Exception as exc:  # noqa: BLE001
            raise VerificationEngineError(
                f"could not interpret model value for {name!r}: {exc}"
            ) from exc

        if config.mode is SemanticMode.MODE_B:
            # Bit-vector model values are interpreted as unsigned in [0, 2^w-1].
            if as_int < 0 or as_int > config.max_unsigned:
                raise VerificationEngineError(
                    f"Mode B model value for {name!r} ({as_int}) is outside "
                    f"unsigned range [0, {config.max_unsigned}]"
                )
        assignment[name] = as_int
    return assignment


def _translate_node(
    node: Expr,
    config: SemanticConfiguration,
    env: Mapping[str, z3.ExprRef],
) -> z3.ExprRef:
    if isinstance(node, IntLiteral):
        return _translate_literal(node.value, config)

    if isinstance(node, Variable):
        try:
            return env[node.name]
        except KeyError as exc:
            raise TranslationError(
                f"missing Z3 symbol for variable {node.name!r}"
            ) from exc

    if isinstance(node, UnaryOp):
        operand = _translate_node(node.operand, config, env)
        if node.op is UnaryOperator.PLUS:
            return operand
        if node.op is UnaryOperator.MINUS:
            if config.mode is SemanticMode.MODE_A:
                return -operand
            # Mode B: bit-vector negation (matches reference evaluator).
            return -operand
        raise TranslationError(f"unsupported unary operator in translation: {node.op}")

    if isinstance(node, BinaryOp):
        left = _translate_node(node.left, config, env)
        right = _translate_node(node.right, config, env)
        if node.op is BinaryOperator.ADD:
            return left + right
        if node.op is BinaryOperator.SUB:
            return left - right
        if node.op is BinaryOperator.MUL:
            return left * right
        raise TranslationError(f"unsupported binary operator in translation: {node.op}")

    raise TranslationError(f"unsupported expression node type: {type(node).__name__}")


def _translate_literal(value: int, config: SemanticConfiguration) -> z3.ExprRef:
    if config.mode is SemanticMode.MODE_A:
        return z3.IntVal(value)
    if value < 0 or value > config.max_unsigned:
        raise TranslationError(
            f"Mode B literal {value} is outside unsigned range "
            f"[0, {config.max_unsigned}] for width {config.bit_width}"
        )
    return z3.BitVecVal(value, config.bit_width)


def _fresh_symbol(name: str, config: SemanticConfiguration) -> z3.ExprRef:
    if config.mode is SemanticMode.MODE_A:
        return z3.Int(name)
    return z3.BitVec(name, config.bit_width)


def _coerce_expression(
    value: Expression | str,
    config: SemanticConfiguration,
) -> tuple[Expression, str]:
    if isinstance(value, Expression):
        return value, value.source
    if isinstance(value, str):
        parsed = parse_expression(value, config)
        return parsed, value
    raise ParseError(
        f"expression must be Expression or str; got {type(value).__name__}"
    )


def _source_of(value: Expression | str) -> str | None:
    if isinstance(value, Expression):
        return value.source
    if isinstance(value, str):
        return value
    return None
