"""VERIFORGE Phase 1: semantic foundation (parse, configure, evaluate)."""

from veriforge.config import ResourceLimits, SemanticConfiguration, default_limits
from veriforge.exceptions import (
    DomainError,
    EvaluationError,
    InvalidLiteralError,
    MissingVariableError,
    ParseError,
    ResourceLimitError,
    UnapprovedASTNodeError,
    UnsupportedSyntaxError,
    VeriforgeError,
)
from veriforge.models import (
    BinaryOp,
    BinaryOperator,
    Expression,
    ExpressionInput,
    IntLiteral,
    SemanticMode,
    UnaryOp,
    UnaryOperator,
    Variable,
)
from veriforge.parser_engine import parse_expression
from veriforge.reference_evaluator import evaluate

__all__ = [
    "BinaryOp",
    "BinaryOperator",
    "DomainError",
    "EvaluationError",
    "Expression",
    "ExpressionInput",
    "IntLiteral",
    "InvalidLiteralError",
    "MissingVariableError",
    "ParseError",
    "ResourceLimitError",
    "ResourceLimits",
    "SemanticConfiguration",
    "SemanticMode",
    "UnapprovedASTNodeError",
    "UnaryOp",
    "UnaryOperator",
    "UnsupportedSyntaxError",
    "Variable",
    "VeriforgeError",
    "default_limits",
    "evaluate",
    "parse_expression",
]

__version__ = "0.1.0"
