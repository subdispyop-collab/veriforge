"""Semantic configuration and configurable resource limits."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from veriforge.exceptions import ResourceLimitError
from veriforge.models import SemanticMode

# Locked Phase 1 defaults (internal/phase-1-decisions.md).
DEFAULT_MAX_SOURCE_LENGTH = 4096
DEFAULT_MAX_AST_NODES = 256
DEFAULT_MAX_NESTING_DEPTH = 32
DEFAULT_MAX_MODE_A_LITERAL_BIT_LENGTH = 4096
DEFAULT_SOLVER_TIMEOUT_SECONDS = 5.0
DEFAULT_BIT_WIDTH = 32


@dataclass(frozen=True, slots=True)
class ResourceLimits:
    """Configurable resource bounds. All fields are enforced where applicable."""

    max_source_length: int = DEFAULT_MAX_SOURCE_LENGTH
    max_ast_nodes: int = DEFAULT_MAX_AST_NODES
    max_nesting_depth: int = DEFAULT_MAX_NESTING_DEPTH
    max_mode_a_literal_bit_length: int = DEFAULT_MAX_MODE_A_LITERAL_BIT_LENGTH
    solver_timeout_seconds: float = DEFAULT_SOLVER_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        if self.max_source_length < 1:
            raise ResourceLimitError("max_source_length must be at least 1")
        if self.max_ast_nodes < 1:
            raise ResourceLimitError("max_ast_nodes must be at least 1")
        if self.max_nesting_depth < 1:
            raise ResourceLimitError("max_nesting_depth must be at least 1")
        if self.max_mode_a_literal_bit_length < 1:
            raise ResourceLimitError("max_mode_a_literal_bit_length must be at least 1")
        if self.solver_timeout_seconds <= 0:
            raise ResourceLimitError("solver_timeout_seconds must be positive")


def default_limits() -> ResourceLimits:
    """Return the locked Phase 1 default resource limits."""

    return ResourceLimits()


@dataclass(frozen=True, slots=True)
class SemanticConfiguration:
    """Explicit semantic mode and Mode B width, with enforced resource limits.

    Mode A uses unbounded mathematical integers. Mode B uses unsigned
    fixed-width bit-vectors of ``bit_width`` bits. The two modes are not
    interchangeable.
    """

    mode: SemanticMode
    bit_width: int = DEFAULT_BIT_WIDTH
    limits: ResourceLimits = field(default_factory=default_limits)

    def __post_init__(self) -> None:
        if not isinstance(self.mode, SemanticMode):
            raise TypeError("mode must be a SemanticMode")
        if self.bit_width < 1:
            raise ResourceLimitError("bit_width must be at least 1")

    @property
    def modulus(self) -> int:
        """Return 2^bit_width. Meaningful for Mode B only."""

        return 1 << self.bit_width

    @property
    def max_unsigned(self) -> int:
        """Return 2^bit_width - 1. Meaningful for Mode B only."""

        return self.modulus - 1

    def with_limits(self, **changes: int | float) -> SemanticConfiguration:
        """Return a copy with updated resource-limit fields."""

        return replace(self, limits=replace(self.limits, **changes))
