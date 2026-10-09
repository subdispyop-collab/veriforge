"""Semantic configuration and default-limit tests."""

from __future__ import annotations

import pytest

from veriforge import ResourceLimitError, ResourceLimits, SemanticConfiguration, SemanticMode
from veriforge.config import (
    DEFAULT_BIT_WIDTH,
    DEFAULT_MAX_AST_NODES,
    DEFAULT_MAX_MODE_A_LITERAL_BIT_LENGTH,
    DEFAULT_MAX_NESTING_DEPTH,
    DEFAULT_MAX_SOURCE_LENGTH,
    DEFAULT_SOLVER_TIMEOUT_SECONDS,
)


def test_locked_defaults() -> None:
    limits = ResourceLimits()
    assert limits.max_source_length == DEFAULT_MAX_SOURCE_LENGTH == 4096
    assert limits.max_ast_nodes == DEFAULT_MAX_AST_NODES == 256
    assert limits.max_nesting_depth == DEFAULT_MAX_NESTING_DEPTH == 32
    assert (
        limits.max_mode_a_literal_bit_length
        == DEFAULT_MAX_MODE_A_LITERAL_BIT_LENGTH
        == 4096
    )
    assert limits.solver_timeout_seconds == DEFAULT_SOLVER_TIMEOUT_SECONDS == 5.0

    cfg = SemanticConfiguration(mode=SemanticMode.MODE_B)
    assert cfg.bit_width == DEFAULT_BIT_WIDTH == 32
    assert cfg.modulus == 1 << 32
    assert cfg.max_unsigned == (1 << 32) - 1


def test_limits_are_configurable() -> None:
    cfg = SemanticConfiguration(mode=SemanticMode.MODE_A).with_limits(
        max_source_length=100,
        max_ast_nodes=50,
    )
    assert cfg.limits.max_source_length == 100
    assert cfg.limits.max_ast_nodes == 50
    assert cfg.limits.max_nesting_depth == 32


def test_invalid_limit_values() -> None:
    with pytest.raises(ResourceLimitError):
        ResourceLimits(max_source_length=0)
    with pytest.raises(ResourceLimitError):
        SemanticConfiguration(mode=SemanticMode.MODE_B, bit_width=0)


def test_modes_are_explicit_and_distinct() -> None:
    assert SemanticMode.MODE_A is not SemanticMode.MODE_B
    assert SemanticMode.MODE_A.value == "mode_a"
    assert SemanticMode.MODE_B.value == "mode_b"
