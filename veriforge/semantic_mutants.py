"""Controlled semantic mutants of copies of the independent implementation.

Mutants are functions in this module. They do not modify production code.
A mutant is detected when its behavior differs from the unmutated independent
evaluator or from the reference status contract on a fixed fixture.
"""

from __future__ import annotations

from dataclasses import dataclass

from veriforge.assurance import GateResult, combine_gates
from veriforge.config import SemanticConfiguration
from veriforge.independent_evaluator import evaluate_independent, unsigned_wrap
from veriforge.independent_parser import IBinary, IExpr, ILit, IUnary, IVar, parse_independent
from veriforge.models import SemanticMode, VerificationStatus


@dataclass(frozen=True, slots=True)
class MutantSpec:
    mutant_id: str
    defect: str
    why_realistic: str
    expected_detector: str


MUTANTS: tuple[MutantSpec, ...] = (
    MutantSpec(
        "m01_add_as_sub",
        "Binary addition is computed as subtraction.",
        "Operator-translation mixups are a common encoding fault.",
        "differential evaluation against the unmutated evaluator",
    ),
    MutantSpec(
        "m02_mul_without_wrap",
        "Mode B multiplication returns the mathematical product without wrap.",
        "Forgetting modular reduction is a fixed-width semantics fault.",
        "differential evaluation on a wrapping product",
    ),
    MutantSpec(
        "m03_unsigned_as_signed",
        "Values at or above 2**(w-1) are returned as negative signed integers.",
        "Unsigned results are sometimes reinterpreted with the sign bit.",
        "differential evaluation on a high unsigned value",
    ),
    MutantSpec(
        "m04_unary_minus_dropped",
        "Unary minus returns its operand unchanged.",
        "A dropped unary operator changes polarity.",
        "differential evaluation on a negated variable",
    ),
    MutantSpec(
        "m05_unary_minus_no_wrap",
        "Mode B unary minus returns a negative Python integer.",
        "Negation implemented as mathematical negation omits bit-vector wrap.",
        "differential evaluation on unary minus",
    ),
    MutantSpec(
        "m06_div_accepted_as_mul",
        "The source operator '/' is parsed as multiplication.",
        "A parser can accept a prohibited operator under a nearby meaning.",
        "reference parser rejects '/' while the mutant accepts it",
    ),
    MutantSpec(
        "m07_timeout_as_equivalent",
        "A timeout gate is combined as equivalence.",
        "Solver timeouts have been misreported as successful proofs.",
        "reference combine_gates on a timeout fixture",
    ),
    MutantSpec(
        "m08_validator_always_confirms",
        "Equal concrete values are still reported as a confirmed counterexample.",
        "A bypassed validator can bless a non-differentiating model.",
        "comparison with the reference confirmation rule",
    ),
    MutantSpec(
        "m09_div_accepted_as_add",
        "The source operator '/' is parsed as addition.",
        "Unsupported syntax can be rewritten into a supported operator.",
        "reference parser rejects '/' while the mutant accepts it",
    ),
    MutantSpec(
        "m10_mul_zero_to_one",
        "The candidate rewrite x*0 is treated as 1 rather than 0.",
        "A constant substitution fault changes a sound identity.",
        "differential evaluation of 0 versus 1",
    ),
)


def mutant_ids() -> tuple[str, ...]:
    return tuple(spec.mutant_id for spec in MUTANTS)


def evaluate_mutant(
    mutant_id: str,
    node: IExpr,
    assignment: dict[str, int],
    config: SemanticConfiguration,
) -> int:
    """Evaluate ``node`` under one injected arithmetic fault."""

    if mutant_id == "m01_add_as_sub":
        return _eval(node, assignment, config, add_op="-")
    if mutant_id == "m02_mul_without_wrap":
        return _eval(node, assignment, config, wrap_mul=False)
    if mutant_id == "m03_unsigned_as_signed":
        value = evaluate_independent(node, assignment, config)
        if config.mode is SemanticMode.MODE_B and value >= (1 << (config.bit_width - 1)):
            return value - (1 << config.bit_width)
        return value
    if mutant_id == "m04_unary_minus_dropped":
        return _eval(node, assignment, config, drop_neg=True)
    if mutant_id == "m05_unary_minus_no_wrap":
        return _eval(node, assignment, config, wrap_neg=False)
    if mutant_id == "m10_mul_zero_to_one":
        return _eval(node, assignment, config, mul_zero_is_one=True)
    raise KeyError(mutant_id)


def parse_mutant(mutant_id: str, source: str, config: SemanticConfiguration):
    """Parse with a faulty operator reading. Only div mutants accept '/'."""

    if mutant_id == "m06_div_accepted_as_mul":
        return parse_independent(source.replace("/", "*"), config)
    if mutant_id == "m09_div_accepted_as_add":
        return parse_independent(source.replace("/", "+"), config)
    raise KeyError(mutant_id)


def mutant_combine_timeout_as_equivalent() -> VerificationStatus:
    """The faulty combiner the harness compares with ``combine_gates``."""

    status, _method, _reason = combine_gates(
        [GateResult(name="production_smt", verdict="timeout", detail="timed out")]
    )
    if status is VerificationStatus.TIMEOUT:
        return VerificationStatus.EQUIVALENT_WITHIN_MODEL
    return status


def reference_confirms_difference(left: int, right: int) -> bool:
    return left != right


def mutant_always_confirms(_left: int, _right: int) -> bool:
    return True


def _eval(
    node: IExpr,
    assignment: dict[str, int],
    config: SemanticConfiguration,
    *,
    add_op: str = "+",
    wrap_mul: bool = True,
    drop_neg: bool = False,
    wrap_neg: bool = True,
    mul_zero_is_one: bool = False,
) -> int:
    if isinstance(node, ILit):
        return node.value
    if isinstance(node, IVar):
        if node.name not in assignment:
            raise KeyError(node.name)
        return assignment[node.name]
    if isinstance(node, IUnary):
        operand = _eval(
            node.operand,
            assignment,
            config,
            add_op=add_op,
            wrap_mul=wrap_mul,
            drop_neg=drop_neg,
            wrap_neg=wrap_neg,
            mul_zero_is_one=mul_zero_is_one,
        )
        if node.op == "+":
            return operand
        if drop_neg:
            return operand
        negated = -operand
        if config.mode is SemanticMode.MODE_B and wrap_neg:
            return unsigned_wrap(negated, config.bit_width)
        return negated
    if isinstance(node, IBinary):
        left = _eval(
            node.left,
            assignment,
            config,
            add_op=add_op,
            wrap_mul=wrap_mul,
            drop_neg=drop_neg,
            wrap_neg=wrap_neg,
            mul_zero_is_one=mul_zero_is_one,
        )
        right = _eval(
            node.right,
            assignment,
            config,
            add_op=add_op,
            wrap_mul=wrap_mul,
            drop_neg=drop_neg,
            wrap_neg=wrap_neg,
            mul_zero_is_one=mul_zero_is_one,
        )
        op = node.op
        if op == "+" and add_op == "-":
            value = left - right
        elif op == "+":
            value = left + right
        elif op == "-":
            value = left - right
        elif op == "*":
            if mul_zero_is_one and (left == 0 or right == 0):
                value = 1
            else:
                value = left * right
            if config.mode is SemanticMode.MODE_B and not wrap_mul:
                return value
        else:
            raise ValueError(op)
        if config.mode is SemanticMode.MODE_B and op != "*":
            return unsigned_wrap(value, config.bit_width)
        if config.mode is SemanticMode.MODE_B and op == "*" and wrap_mul:
            return unsigned_wrap(value, config.bit_width)
        return value
    raise ValueError(type(node).__name__)
