"""Recursive-descent parser for the restricted arithmetic grammar.

This parser does not use Python ``ast``, ``eval``, or ``exec``, and it does
not call the production parser. Integer and bit-vector literal checks are
reimplemented here. Shared configuration objects supply limits only.

A difference between this parser and ``parser_engine`` is a trust-boundary
event, not evidence that either parser is correct.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from veriforge.config import SemanticConfiguration
from veriforge.exceptions import (
    InvalidLiteralError,
    ParseError,
    ResourceLimitError,
    UnsupportedSyntaxError,
)
from veriforge.models import SemanticMode

IExpr = Union["ILit", "IVar", "IUnary", "IBinary"]


@dataclass(frozen=True, slots=True)
class ILit:
    value: int


@dataclass(frozen=True, slots=True)
class IVar:
    name: str


@dataclass(frozen=True, slots=True)
class IUnary:
    op: str
    operand: IExpr


@dataclass(frozen=True, slots=True)
class IBinary:
    op: str
    left: IExpr
    right: IExpr


@dataclass(frozen=True, slots=True)
class IndependentExpression:
    """Parsed expression in the independent intermediate form."""

    source: str
    root: IExpr
    variables: frozenset[str]


class _Lexer:
    def __init__(self, source: str) -> None:
        self.source = source
        self.n = len(source)
        self.i = 0

    def peek(self) -> str:
        self._skip()
        if self.i >= self.n:
            return ""
        return self.source[self.i]

    def _skip(self) -> None:
        while self.i < self.n and self.source[self.i] in " \t\r\n":
            self.i += 1

    def startswith_ident(self) -> bool:
        self._skip()
        if self.i >= self.n:
            return False
        return self.source[self.i].isascii() and (
            self.source[self.i].isalpha() or self.source[self.i] == "_"
        )

    def take_ident(self) -> str:
        self._skip()
        start = self.i
        if self.i >= self.n or not (
            self.source[self.i].isascii()
            and (self.source[self.i].isalpha() or self.source[self.i] == "_")
        ):
            raise UnsupportedSyntaxError("expected an identifier")
        self.i += 1
        while self.i < self.n and self.source[self.i].isascii() and (
            self.source[self.i].isalnum() or self.source[self.i] == "_"
        ):
            self.i += 1
        return self.source[start : self.i]

    def take_number(self) -> int:
        self._skip()
        if self.i >= self.n or not self.source[self.i].isdigit():
            raise ParseError("expected an integer literal")
        if self.source[self.i] == "0" and self.i + 1 < self.n:
            nxt = self.source[self.i + 1]
            if nxt in "xX":
                return self._prefixed(16, "hexadecimal", "0123456789abcdefABCDEF")
            if nxt in "bB":
                return self._prefixed(2, "binary", "01")
            if nxt in "oO":
                return self._prefixed(8, "octal", "01234567")
        return self._decimal()

    def _prefixed(self, base: int, name: str, digits: str) -> int:
        self.i += 2  # 0 and prefix
        if self.i < self.n and self.source[self.i] == "_":
            self.i += 1
        raw: list[str] = []
        while self.i < self.n:
            ch = self.source[self.i]
            if ch == "_":
                if not raw or self.i + 1 >= self.n or self.source[self.i + 1] not in digits:
                    raise InvalidLiteralError(f"invalid underscore in {name} literal")
                self.i += 1
                continue
            if ch not in digits:
                break
            raw.append(ch)
            self.i += 1
        if not raw:
            raise InvalidLiteralError(f"invalid {name} literal")
        return int("".join(raw), base)

    def _decimal(self) -> int:
        raw: list[str] = []
        while self.i < self.n:
            ch = self.source[self.i]
            if ch == "_":
                if not raw or self.i + 1 >= self.n or not self.source[self.i + 1].isdigit():
                    raise InvalidLiteralError("invalid underscore in decimal literal")
                self.i += 1
                continue
            if not ch.isdigit():
                break
            raw.append(ch)
            self.i += 1
        text = "".join(raw)
        if not text:
            raise InvalidLiteralError("invalid decimal literal")
        if len(text) > 1 and text[0] == "0" and any(ch != "0" for ch in text):
            raise UnsupportedSyntaxError(
                "leading zeros in decimal integer literals are not permitted"
            )
        return int(text)

    def eat(self, ch: str) -> bool:
        if self.peek() == ch:
            self.i += 1
            return True
        return False


def parse_independent(source: str, config: SemanticConfiguration) -> IndependentExpression:
    """Parse ``source`` into the independent IR under ``config``."""

    if not isinstance(source, str):
        raise ParseError(f"source must be a string; got {type(source).__name__}")
    if len(source) > config.limits.max_source_length:
        raise ResourceLimitError(
            f"source length {len(source)} exceeds limit {config.limits.max_source_length}"
        )
    lexer = _Lexer(source)
    counter = _Counter(config.limits.max_ast_nodes)
    root = _parse_expr(lexer, config, counter, depth=1)
    if lexer.peek() != "":
        raise UnsupportedSyntaxError(
            f"unsupported or trailing syntax at {lexer.source[lexer.i : lexer.i + 12]!r}"
        )
    variables: set[str] = set()
    _collect(root, variables)
    return IndependentExpression(source=source, root=root, variables=frozenset(variables))


class _Counter:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.count = 0

    def add(self) -> None:
        self.count += 1
        if self.count > self.limit:
            raise ResourceLimitError(
                f"independent node count {self.count} exceeds limit {self.limit}"
            )


def _check_depth(depth: int, config: SemanticConfiguration) -> None:
    if depth > config.limits.max_nesting_depth:
        raise ResourceLimitError(
            f"nesting depth {depth} exceeds limit {config.limits.max_nesting_depth}"
        )


def _parse_expr(
    lexer: _Lexer,
    config: SemanticConfiguration,
    counter: _Counter,
    depth: int,
) -> IExpr:
    _check_depth(depth, config)
    node = _parse_term(lexer, config, counter, depth)
    while lexer.peek() in "+-":
        # A following number or name or '(' or unary sign continues the operator.
        op = lexer.peek()
        saved = lexer.i
        lexer.i += 1
        if op == "-" or op == "+":
            # Could be a binary operator. Always binary here because a term
            # has already been parsed; unary signs bind inside terms.
            right = _parse_term(lexer, config, counter, depth + 1)
            counter.add()
            node = IBinary(op=op, left=node, right=right)
        else:  # pragma: no cover
            lexer.i = saved
            break
    return node


def _parse_term(
    lexer: _Lexer,
    config: SemanticConfiguration,
    counter: _Counter,
    depth: int,
) -> IExpr:
    node = _parse_unary(lexer, config, counter, depth)
    while lexer.peek() == "*":
        lexer.i += 1
        right = _parse_unary(lexer, config, counter, depth + 1)
        counter.add()
        node = IBinary(op="*", left=node, right=right)
    return node


def _parse_unary(
    lexer: _Lexer,
    config: SemanticConfiguration,
    counter: _Counter,
    depth: int,
) -> IExpr:
    _check_depth(depth, config)
    sign = lexer.peek()
    if sign in "+-":
        # Look ahead: a sign is unary when we are inside unary position.
        lexer.i += 1
        operand = _parse_unary(lexer, config, counter, depth + 1)
        counter.add()
        return IUnary(op=sign, operand=operand)
    return _parse_primary(lexer, config, counter, depth)


def _parse_primary(
    lexer: _Lexer,
    config: SemanticConfiguration,
    counter: _Counter,
    depth: int,
) -> IExpr:
    _check_depth(depth, config)
    if lexer.eat("("):
        node = _parse_expr(lexer, config, counter, depth + 1)
        if not lexer.eat(")"):
            raise UnsupportedSyntaxError("missing closing parenthesis")
        if lexer.peek() == ",":
            raise UnsupportedSyntaxError("tuples are not expressions")
        return node
    if lexer.startswith_ident():
        name = lexer.take_ident()
        if name in {"True", "False"}:
            raise InvalidLiteralError(
                f"Boolean constant {name} is not an integer literal"
            )
        if lexer.peek() == "(":
            raise UnsupportedSyntaxError("calls are not allowed")
        counter.add()
        return IVar(name=name)
    if lexer.peek().isdigit():
        value = lexer.take_number()
        _check_literal(value, config)
        counter.add()
        return ILit(value=value)
    ch = lexer.peek()
    if ch == "":
        raise ParseError("unexpected end of expression")
    raise UnsupportedSyntaxError(f"unsupported syntax starting at {ch!r}")


def _check_literal(value: int, config: SemanticConfiguration) -> None:
    if value < 0:
        raise InvalidLiteralError(f"integer literal must be non-negative; got {value}")
    if config.mode is SemanticMode.MODE_A:
        limit = config.limits.max_mode_a_literal_bit_length
        if value.bit_length() > limit:
            raise InvalidLiteralError(
                f"Mode A integer literal bit length {value.bit_length()} exceeds limit {limit}"
            )
        return
    if config.mode is SemanticMode.MODE_B:
        maximum = (1 << config.bit_width) - 1
        if value > maximum:
            raise InvalidLiteralError(
                f"Mode B integer literal {value} is outside unsigned range "
                f"[0, {maximum}] for width {config.bit_width}"
            )
        return
    raise ParseError(f"unsupported semantic mode {config.mode!r}")


def _collect(node: IExpr, names: set[str]) -> None:
    if isinstance(node, IVar):
        names.add(node.name)
    elif isinstance(node, IUnary):
        _collect(node.operand, names)
    elif isinstance(node, IBinary):
        _collect(node.left, names)
        _collect(node.right, names)


def render_independent(node: IExpr) -> str:
    """Render an independent expression with explicit parentheses."""

    if isinstance(node, ILit):
        return str(node.value)
    if isinstance(node, IVar):
        return node.name
    if isinstance(node, IUnary):
        return f"({node.op}{render_independent(node.operand)})"
    if isinstance(node, IBinary):
        return (
            f"({render_independent(node.left)}{node.op}{render_independent(node.right)})"
        )
    raise ParseError(f"unexpected independent node {type(node).__name__}")


def variables_of(node: IExpr) -> frozenset[str]:
    names: set[str] = set()
    _collect(node, names)
    return frozenset(names)


def operator_count(node: IExpr) -> int:
    if isinstance(node, (ILit, IVar)):
        return 0
    if isinstance(node, IUnary):
        return 1 + operator_count(node.operand)
    if isinstance(node, IBinary):
        return 1 + operator_count(node.left) + operator_count(node.right)
    return 0


def nesting_depth(node: IExpr) -> int:
    if isinstance(node, (ILit, IVar)):
        return 1
    if isinstance(node, IUnary):
        return 1 + nesting_depth(node.operand)
    if isinstance(node, IBinary):
        return 1 + max(nesting_depth(node.left), nesting_depth(node.right))
    return 1
