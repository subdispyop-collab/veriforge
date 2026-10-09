"""Classified errors for Phase 1 parsing and evaluation."""


class VeriforgeError(Exception):
    """Base error for VERIFORGE."""


class ParseError(VeriforgeError):
    """Input could not be accepted as a supported expression."""


class UnsupportedSyntaxError(ParseError):
    """The input uses syntax outside the initial grammar."""


class UnapprovedASTNodeError(ParseError):
    """The AST contains a node type that is not approved."""


class ResourceLimitError(ParseError):
    """A configured resource limit was exceeded."""


class InvalidLiteralError(ParseError):
    """An integer literal is illegal under the active semantic configuration."""


class EvaluationError(VeriforgeError):
    """A supported expression could not be evaluated under the given assignment."""


class MissingVariableError(EvaluationError):
    """An assignment is missing a required variable."""


class DomainError(EvaluationError):
    """An assigned value is outside the domain of the active semantic mode."""
