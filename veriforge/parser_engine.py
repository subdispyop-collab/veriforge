"""Safe expression parsing with Python's ``ast`` module.

Never uses ``eval`` or ``exec``. Unsupported syntax, unapproved AST nodes,
and over-limit inputs fail closed with classified errors.
"""

from __future__ import annotations

import ast
from typing import Final

from veriforge.config import SemanticConfiguration
from veriforge.exceptions import (
    InvalidLiteralError,
    ParseError,
    ResourceLimitError,
    UnapprovedASTNodeError,
    UnsupportedSyntaxError,
)
from veriforge.models import (
    BinaryOp,
    BinaryOperator,
    Expression,
    IntLiteral,
    UnaryOp,
    UnaryOperator,
    Variable,
)
from veriforge.semantics import validate_literal

# Binary operators accepted by the initial grammar.
_BINARY_OPS: Final[dict[type[ast.operator], BinaryOperator]] = {
    ast.Add: BinaryOperator.ADD,
    ast.Sub: BinaryOperator.SUB,
    ast.Mult: BinaryOperator.MUL,
}

# Unary operators accepted by the initial grammar.
_UNARY_OPS: Final[dict[type[ast.unaryop], UnaryOperator]] = {
    ast.UAdd: UnaryOperator.PLUS,
    ast.USub: UnaryOperator.MINUS,
}

# AST node types that may appear in a fully validated expression tree.
# Expression root is handled separately via ast.Expression.
_APPROVED_NODE_TYPES: Final[frozenset[type[ast.AST]]] = frozenset(
    {
        ast.Constant,
        ast.Name,
        ast.Load,
        ast.BinOp,
        ast.UnaryOp,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.UAdd,
        ast.USub,
        ast.Expression,
    }
)


def parse_expression(source: str, config: SemanticConfiguration) -> Expression:
    """Parse ``source`` under ``config`` into the internal representation.

    Raises a classified ``ParseError`` subclass on any rejection.
    """

    if not isinstance(source, str):
        raise ParseError(f"source must be a string; got {type(source).__name__}")

    _enforce_source_length(source, config)

    try:
        tree = ast.parse(source, mode="eval")
    except SyntaxError as exc:
        raise UnsupportedSyntaxError(
            f"syntax error: {exc.msg}"
        ) from exc

    _reject_unapproved_nodes(tree)
    _enforce_ast_node_count(tree, config)
    _enforce_nesting_depth(tree.body, config, depth=1)

    variables: set[str] = set()
    root = _convert(tree.body, config, variables)
    return Expression(
        source=source,
        root=root,
        variables=frozenset(variables),
    )


def _enforce_source_length(source: str, config: SemanticConfiguration) -> None:
    limit = config.limits.max_source_length
    length = len(source)
    if length > limit:
        raise ResourceLimitError(
            f"source length {length} exceeds limit {limit}"
        )


def _enforce_ast_node_count(tree: ast.AST, config: SemanticConfiguration) -> None:
    count = sum(1 for _ in ast.walk(tree))
    limit = config.limits.max_ast_nodes
    if count > limit:
        raise ResourceLimitError(
            f"AST node count {count} exceeds limit {limit}"
        )


def _enforce_nesting_depth(
    node: ast.AST,
    config: SemanticConfiguration,
    depth: int,
) -> None:
    limit = config.limits.max_nesting_depth
    if depth > limit:
        raise ResourceLimitError(
            f"nesting depth {depth} exceeds limit {limit}"
        )

    if isinstance(node, ast.BinOp):
        _enforce_nesting_depth(node.left, config, depth + 1)
        _enforce_nesting_depth(node.right, config, depth + 1)
    elif isinstance(node, ast.UnaryOp):
        _enforce_nesting_depth(node.operand, config, depth + 1)


def _reject_unapproved_nodes(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if type(node) not in _APPROVED_NODE_TYPES:
            raise UnapprovedASTNodeError(
                f"unapproved AST node type: {type(node).__name__}"
            )


def _convert(
    node: ast.AST,
    config: SemanticConfiguration,
    variables: set[str],
) -> IntLiteral | Variable | UnaryOp | BinaryOp:
    if isinstance(node, ast.Constant):
        return _convert_constant(node, config)

    if isinstance(node, ast.Name):
        if not isinstance(node.ctx, ast.Load):
            raise UnsupportedSyntaxError(
                f"name context {type(node.ctx).__name__} is not allowed"
            )
        variables.add(node.id)
        return Variable(name=node.id)

    if isinstance(node, ast.UnaryOp):
        op = _UNARY_OPS.get(type(node.op))
        if op is None:
            raise UnsupportedSyntaxError(
                f"unsupported unary operator: {type(node.op).__name__}"
            )
        return UnaryOp(op=op, operand=_convert(node.operand, config, variables))

    if isinstance(node, ast.BinOp):
        op = _BINARY_OPS.get(type(node.op))
        if op is None:
            raise UnsupportedSyntaxError(
                f"unsupported binary operator: {type(node.op).__name__}"
            )
        return BinaryOp(
            op=op,
            left=_convert(node.left, config, variables),
            right=_convert(node.right, config, variables),
        )

    # Defensive: should already be blocked by _reject_unapproved_nodes.
    raise UnapprovedASTNodeError(
        f"unapproved AST node type: {type(node).__name__}"
    )


def _convert_constant(node: ast.Constant, config: SemanticConfiguration) -> IntLiteral:
    value = node.value

    # bool is a subclass of int in Python; reject True/False explicitly.
    if isinstance(value, bool):
        raise InvalidLiteralError(
            f"Boolean constant {value!r} is not an integer literal"
        )

    if isinstance(value, int):
        validate_literal(value, config)
        return IntLiteral(value=value)

    raise UnsupportedSyntaxError(
        f"non-integer constant of type {type(value).__name__} is not allowed"
    )
