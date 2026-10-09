"""Semantic helpers shared by the parser and reference evaluator."""

from __future__ import annotations

from veriforge.config import SemanticConfiguration
from veriforge.exceptions import DomainError, InvalidLiteralError
from veriforge.models import SemanticMode


def mode_b_max(config: SemanticConfiguration) -> int:
    """Largest unsigned value representable at the configured width."""

    return config.max_unsigned


def validate_literal(value: int, config: SemanticConfiguration) -> None:
    """Reject a literal that is illegal under the active configuration.

    Literals from Python's ``ast`` for integer constants are non-negative
    after Boolean rejection. Mode A enforces the configured bit-length
    limit. Mode B rejects values outside ``[0, 2^w - 1]`` without reducing
    them modulo ``2^w``.
    """

    if value < 0:
        raise InvalidLiteralError(
            f"integer literal must be non-negative; got {value}"
        )

    if config.mode is SemanticMode.MODE_A:
        bit_length = value.bit_length()
        limit = config.limits.max_mode_a_literal_bit_length
        if bit_length > limit:
            raise InvalidLiteralError(
                f"Mode A integer literal bit length {bit_length} exceeds "
                f"limit {limit}"
            )
        return

    # Mode B: fail closed on out-of-range literals (unsigned domain).
    maximum = mode_b_max(config)
    if value > maximum:
        raise InvalidLiteralError(
            f"Mode B integer literal {value} is outside unsigned range "
            f"[0, {maximum}] for width {config.bit_width}"
        )


def validate_assignment_value(name: str, value: int, config: SemanticConfiguration) -> int:
    """Check that an assigned variable value is in the mode's domain."""

    if not isinstance(value, int) or isinstance(value, bool):
        raise DomainError(
            f"variable {name!r} requires an integer assignment; got {type(value).__name__}"
        )

    if config.mode is SemanticMode.MODE_A:
        return value

    maximum = mode_b_max(config)
    if value < 0 or value > maximum:
        raise DomainError(
            f"variable {name!r} value {value} is outside Mode B unsigned range "
            f"[0, {maximum}] for width {config.bit_width}"
        )
    return value


def wrap_unsigned(value: int, config: SemanticConfiguration) -> int:
    """Reduce ``value`` into ``[0, 2^w - 1]`` under Mode B modular wrap."""

    if config.mode is not SemanticMode.MODE_B:
        raise DomainError("wrap_unsigned applies only to Mode B")
    return value % config.modulus


def bv_negate(value: int, config: SemanticConfiguration) -> int:
    """Mode B unary minus: unsigned bit-vector negation at the configured width."""

    if config.mode is not SemanticMode.MODE_B:
        raise DomainError("bv_negate applies only to Mode B")
    return wrap_unsigned(-value, config)
