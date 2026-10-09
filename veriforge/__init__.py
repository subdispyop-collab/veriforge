"""VERIFORGE: semantic foundation (Phase 1) and formal verification (Phase 2)."""

from veriforge.config import ResourceLimits, SemanticConfiguration, default_limits
from veriforge.exceptions import (
    DomainError,
    EvaluationError,
    InvalidLiteralError,
    MissingVariableError,
    ParseError,
    ResourceLimitError,
    TranslationError,
    UnapprovedASTNodeError,
    UnsupportedSyntaxError,
    VerificationEngineError,
    VeriforgeError,
)
from veriforge.models import (
    BinaryOp,
    BinaryOperator,
    Counterexample,
    CounterexampleValidationStatus,
    Expression,
    ExpressionInput,
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
from veriforge.verifier_engine import (
    classify_check_result,
    translate_to_z3,
    verify_equivalence,
)

__all__ = [
    "BinaryOp",
    "BinaryOperator",
    "Counterexample",
    "CounterexampleValidationStatus",
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
    "TranslationError",
    "UnapprovedASTNodeError",
    "UnaryOp",
    "UnaryOperator",
    "UnsupportedSyntaxError",
    "Variable",
    "VerificationEngineError",
    "VerificationResult",
    "VerificationStatus",
    "VeriforgeError",
    "classify_check_result",
    "default_limits",
    "evaluate",
    "parse_expression",
    "translate_to_z3",
    "verify_equivalence",
]

__version__ = "0.2.0"
