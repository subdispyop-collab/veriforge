"""Concrete evaluator with its own integer and unsigned bit-vector arithmetic.

Does not import the production Z3 translator, ``semantics.wrap_unsigned``,
or ``semantics.bv_negate``. Does not use ``eval`` or ``exec``.

Mode A uses Python's unbounded integers, which are the host representation
of mathematical integers. Mode B reduces with Python's non-negative modulo
(``value % 2**w``). That operation is implemented in this module. Agreement
with the production evaluator is not treated as a proof that either is correct.
"""

from __future__ import annotations

from veriforge.config import SemanticConfiguration
from veriforge.exceptions import DomainError, MissingVariableError
from veriforge.independent_parser import (
    IBinary,
    IExpr,
    ILit,
    IUnary,
    IVar,
    IndependentExpression,
    parse_independent,
)
from veriforge.models import SemanticMode


def unsigned_modulus(width: int) -> int:
    if width < 1:
        raise DomainError("bit width must be at least 1")
    return 1 << width


def unsigned_wrap(value: int, width: int) -> int:
    """Return ``value`` in ``[0, 2**width - 1]``.

    Python's ``%`` on a positive modulus yields a non-negative remainder,
    including when ``value`` is negative. This is unsigned wrap, not a
    signed reinterpretation.
    """

    if not isinstance(value, int) or isinstance(value, bool):
        raise DomainError(f"expected int, got {type(value).__name__}")
    return value % unsigned_modulus(width)


def evaluate_independent(
    expression: IndependentExpression | IExpr,
    assignment: dict[str, int],
    config: SemanticConfiguration,
) -> int:
    """Evaluate an independently parsed expression."""

    root = expression.root if isinstance(expression, IndependentExpression) else expression
    names = (
        expression.variables
        if isinstance(expression, IndependentExpression)
        else _names(root)
    )
    env: dict[str, int] = {}
    for name in names:
        if name not in assignment:
            raise MissingVariableError(f"missing assignment for variable {name!r}")
        env[name] = _check_value(name, assignment[name], config)
    return _eval(root, env, config)


def evaluate_source(
    source: str,
    assignment: dict[str, int],
    config: SemanticConfiguration,
) -> int:
    """Parse with the independent parser and evaluate."""

    parsed = parse_independent(source, config)
    return evaluate_independent(parsed, assignment, config)


def _names(node: IExpr) -> frozenset[str]:
    found: set[str] = set()

    def walk(current: IExpr) -> None:
        if isinstance(current, IVar):
            found.add(current.name)
        elif isinstance(current, IUnary):
            walk(current.operand)
        elif isinstance(current, IBinary):
            walk(current.left)
            walk(current.right)

    walk(node)
    return frozenset(found)


def _check_value(name: str, value: int, config: SemanticConfiguration) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise DomainError(
            f"variable {name!r} requires an integer assignment; got {type(value).__name__}"
        )
    if config.mode is SemanticMode.MODE_A:
        return value
    if config.mode is SemanticMode.MODE_B:
        maximum = unsigned_modulus(config.bit_width) - 1
        if value < 0 or value > maximum:
            raise DomainError(
                f"variable {name!r} value {value} is outside Mode B unsigned range "
                f"[0, {maximum}] for width {config.bit_width}"
            )
        return value
    raise DomainError(f"unsupported semantic mode {config.mode!r}")


def _eval(node: IExpr, env: dict[str, int], config: SemanticConfiguration) -> int:
    if isinstance(node, ILit):
        if config.mode is SemanticMode.MODE_B:
            # Literals were range-checked at parse time. Wrapping here would
            # hide an out-of-range literal, so reject instead of reducing.
            maximum = unsigned_modulus(config.bit_width) - 1
            if node.value < 0 or node.value > maximum:
                raise DomainError(
                    f"Mode B literal {node.value} is outside unsigned range"
                )
            return node.value
        return node.value
    if isinstance(node, IVar):
        return env[node.name]
    if isinstance(node, IUnary):
        operand = _eval(node.operand, env, config)
        if node.op == "+":
            return operand
        if node.op == "-":
            if config.mode is SemanticMode.MODE_A:
                return -operand
            return unsigned_wrap(-operand, config.bit_width)
        raise DomainError(f"unsupported unary operator {node.op!r}")
    if isinstance(node, IBinary):
        left = _eval(node.left, env, config)
        right = _eval(node.right, env, config)
        if config.mode is SemanticMode.MODE_A:
            return _arith(node.op, left, right)
        return unsigned_wrap(_arith(node.op, left, right), config.bit_width)
    raise DomainError(f"unexpected node {type(node).__name__}")


def _arith(op: str, left: int, right: int) -> int:
    if op == "+":
        return left + right
    if op == "-":
        return left - right
    if op == "*":
        return left * right
    raise DomainError(f"unsupported binary operator {op!r}")
