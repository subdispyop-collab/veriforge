"""Conservative, verification-guided arithmetic optimizer (Phase 3).

Pipeline (controlling specification §7.1):

1. Parse and validate.
2. Build the supported internal representation.
3. Select applicable rules.
4. Generate a candidate.
5. Record the rule and its preconditions.
6. Verify the candidate against the original expression (Phase 2 verifier).
7. Accept only under the configured correctness policy.
8. Record rejected candidates and the reasons for rejection.
9. Return the accepted expression and the complete trace.

Default policy is verification-guided: a candidate is accepted only when the
verifier reports ``EQUIVALENT_WITHIN_MODEL``. Outcomes
``COUNTEREXAMPLE_FOUND``, ``UNKNOWN``, ``TIMEOUT``, and error statuses never
cause silent acceptance.

``CorrectnessPolicy.EVALUATION_ONLY`` is handled only by the isolated
Phase 4 module ``veriforge.fuzzer_suite``. This production ``optimize()``
path rejects that policy so deliberately incorrect candidates cannot
enter production acceptance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

from veriforge.config import SemanticConfiguration
from veriforge.exceptions import OptimizerError, ParseError
from veriforge.models import (
    BinaryOp,
    BinaryOperator,
    CandidateDecision,
    CorrectnessPolicy,
    Expr,
    Expression,
    IntLiteral,
    OptimizationResult,
    OptimizationRule,
    SemanticMode,
    TransformationStep,
    UnaryOp,
    UnaryOperator,
    Variable,
    VerificationPolicy,
    VerificationResult,
    VerificationStatus,
)
from veriforge.parser_engine import parse_expression
from veriforge.verifier_engine import verify_equivalence

# Maximum accepted rewrites in one optimize() call (safety bound, not a
# semantic limit of the language).
DEFAULT_MAX_ACCEPTED_STEPS = 64

Path = tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _RuleImpl:
    """Bound metadata plus matching/rewriting implementation for one rule."""

    metadata: OptimizationRule
    try_rewrite: Callable[[Expr], Expr | None]


def _is_int_literal(node: Expr, value: int) -> bool:
    return isinstance(node, IntLiteral) and node.value == value


def _try_add_zero(node: Expr) -> Expr | None:
    if (
        isinstance(node, BinaryOp)
        and node.op is BinaryOperator.ADD
        and _is_int_literal(node.right, 0)
    ):
        return node.left
    return None


def _try_sub_zero(node: Expr) -> Expr | None:
    if (
        isinstance(node, BinaryOp)
        and node.op is BinaryOperator.SUB
        and _is_int_literal(node.right, 0)
    ):
        return node.left
    return None


def _try_mul_one(node: Expr) -> Expr | None:
    if (
        isinstance(node, BinaryOp)
        and node.op is BinaryOperator.MUL
        and _is_int_literal(node.right, 1)
    ):
        return node.left
    return None


def _try_mul_zero(node: Expr) -> Expr | None:
    if (
        isinstance(node, BinaryOp)
        and node.op is BinaryOperator.MUL
        and _is_int_literal(node.right, 0)
    ):
        return IntLiteral(value=0)
    return None


def _same_expr(left: Expr, right: Expr) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, IntLiteral) and isinstance(right, IntLiteral):
        return left.value == right.value
    if isinstance(left, Variable) and isinstance(right, Variable):
        return left.name == right.name
    if isinstance(left, UnaryOp) and isinstance(right, UnaryOp):
        return left.op is right.op and _same_expr(left.operand, right.operand)
    if isinstance(left, BinaryOp) and isinstance(right, BinaryOp):
        return (
            left.op is right.op
            and _same_expr(left.left, right.left)
            and _same_expr(left.right, right.right)
        )
    return False


def _try_distributivity(node: Expr) -> Expr | None:
    """a * (b + c) → (a * b) + (a * c). The proved orientation only."""

    if (
        isinstance(node, BinaryOp)
        and node.op is BinaryOperator.MUL
        and isinstance(node.right, BinaryOp)
        and node.right.op is BinaryOperator.ADD
    ):
        return BinaryOp(
            op=BinaryOperator.ADD,
            left=BinaryOp(op=BinaryOperator.MUL, left=node.left, right=node.right.left),
            right=BinaryOp(op=BinaryOperator.MUL, left=node.left, right=node.right.right),
        )
    return None


def _try_factoring(node: Expr) -> Expr | None:
    """(a * b) + (a * c) → a * (b + c), matching the left factor."""

    if not (
        isinstance(node, BinaryOp)
        and node.op is BinaryOperator.ADD
        and isinstance(node.left, BinaryOp)
        and node.left.op is BinaryOperator.MUL
        and isinstance(node.right, BinaryOp)
        and node.right.op is BinaryOperator.MUL
        and _same_expr(node.left.left, node.right.left)
    ):
        return None
    return BinaryOp(
        op=BinaryOperator.MUL,
        left=node.left.left,
        right=BinaryOp(
            op=BinaryOperator.ADD,
            left=node.left.right,
            right=node.right.right,
        ),
    )


def _try_const_fold(node: Expr) -> Expr | None:
    """Fold addition of two integer literals. Other folds stay unproved."""

    if (
        isinstance(node, BinaryOp)
        and node.op is BinaryOperator.ADD
        and isinstance(node.left, IntLiteral)
        and isinstance(node.right, IntLiteral)
    ):
        return IntLiteral(value=node.left.value + node.right.value)
    return None


def _try_sub_self(node: Expr) -> Expr | None:
    if (
        isinstance(node, BinaryOp)
        and node.op is BinaryOperator.SUB
        and _same_expr(node.left, node.right)
    ):
        return IntLiteral(value=0)
    return None


def _try_add_self(node: Expr) -> Expr | None:
    if (
        isinstance(node, BinaryOp)
        and node.op is BinaryOperator.ADD
        and _same_expr(node.left, node.right)
    ):
        return BinaryOp(
            op=BinaryOperator.MUL,
            left=node.left,
            right=IntLiteral(value=2),
        )
    return None


def _try_double_neg(node: Expr) -> Expr | None:
    if (
        isinstance(node, UnaryOp)
        and node.op is UnaryOperator.MINUS
        and isinstance(node.operand, UnaryOp)
        and node.operand.op is UnaryOperator.MINUS
    ):
        return node.operand.operand
    return None


def _try_neg_sub(node: Expr) -> Expr | None:
    if (
        isinstance(node, UnaryOp)
        and node.op is UnaryOperator.MINUS
        and isinstance(node.operand, BinaryOp)
        and node.operand.op is BinaryOperator.SUB
    ):
        return BinaryOp(
            op=BinaryOperator.SUB,
            left=node.operand.right,
            right=node.operand.left,
        )
    return None


def _try_const_reassoc(node: Expr) -> Expr | None:
    """(e + c1) + c2 → e + (c1 + c2) for integer literals c1 and c2."""

    if (
        isinstance(node, BinaryOp)
        and node.op is BinaryOperator.ADD
        and isinstance(node.right, IntLiteral)
        and isinstance(node.left, BinaryOp)
        and node.left.op is BinaryOperator.ADD
        and isinstance(node.left.right, IntLiteral)
    ):
        return BinaryOp(
            op=BinaryOperator.ADD,
            left=node.left.left,
            right=IntLiteral(value=node.left.right.value + node.right.value),
        )
    return None


_BOTH_MODES = frozenset({SemanticMode.MODE_A, SemanticMode.MODE_B})

RULE_ADD_ZERO = OptimizationRule(
    rule_id="identity.add_zero",
    name="Add-zero elimination",
    formal_description="x + 0 → x",
    preconditions=(
        "The matched node is a binary addition",
        "The right operand is the integer literal 0",
        "The active semantic mode is Mode A or Mode B",
    ),
    supported_modes=_BOTH_MODES,
    verification_policy=VerificationPolicy.REQUIRE_EQUIVALENT_WITHIN_MODEL,
)

RULE_SUB_ZERO = OptimizationRule(
    rule_id="identity.sub_zero",
    name="Subtract-zero elimination",
    formal_description="x - 0 → x",
    preconditions=(
        "The matched node is a binary subtraction",
        "The right operand is the integer literal 0",
        "The active semantic mode is Mode A or Mode B",
    ),
    supported_modes=_BOTH_MODES,
    verification_policy=VerificationPolicy.REQUIRE_EQUIVALENT_WITHIN_MODEL,
)

RULE_MUL_ONE = OptimizationRule(
    rule_id="identity.mul_one",
    name="Multiply-by-one elimination",
    formal_description="x * 1 → x",
    preconditions=(
        "The matched node is a binary multiplication",
        "The right operand is the integer literal 1",
        "The active semantic mode is Mode A or Mode B",
    ),
    supported_modes=_BOTH_MODES,
    verification_policy=VerificationPolicy.REQUIRE_EQUIVALENT_WITHIN_MODEL,
)

RULE_MUL_ZERO = OptimizationRule(
    rule_id="identity.mul_zero",
    name="Multiply-by-zero folding",
    formal_description="x * 0 → 0",
    preconditions=(
        "The matched node is a binary multiplication",
        "The right operand is the integer literal 0",
        "The active semantic mode is Mode A or Mode B",
    ),
    supported_modes=_BOTH_MODES,
    verification_policy=VerificationPolicy.REQUIRE_EQUIVALENT_WITHIN_MODEL,
)

RULE_DISTRIBUTIVITY = OptimizationRule(
    rule_id="algebra.distributivity",
    name="Distribute multiplication over addition",
    formal_description="a * (b + c) → (a * b) + (a * c)",
    preconditions=(
        "The matched node is a binary multiplication",
        "The right operand is a binary addition",
        "Production Z3 returned EQUIVALENT_WITHIN_MODEL for this template in Mode A and in Mode B width 4",
    ),
    supported_modes=_BOTH_MODES,
    verification_policy=VerificationPolicy.REQUIRE_EQUIVALENT_WITHIN_MODEL,
)

RULE_FACTORING = OptimizationRule(
    rule_id="algebra.factoring",
    name="Factor a common left multiplier",
    formal_description="(a * b) + (a * c) → a * (b + c)",
    preconditions=(
        "The matched node is a binary addition of two multiplications",
        "The two multiplications share the same left operand",
        "Production Z3 returned EQUIVALENT_WITHIN_MODEL for this template in Mode A and in Mode B width 4",
    ),
    supported_modes=_BOTH_MODES,
    verification_policy=VerificationPolicy.REQUIRE_EQUIVALENT_WITHIN_MODEL,
)

RULE_CONST_FOLD = OptimizationRule(
    rule_id="algebra.const_fold",
    name="Fold addition of two literals",
    formal_description="c1 + c2 → (c1 + c2) for integer literals",
    preconditions=(
        "Both operands are integer literals",
        "The operator is addition",
        "Production Z3 returned EQUIVALENT_WITHIN_MODEL for (2 + 3) versus 5 in Mode A and in Mode B width 4",
    ),
    supported_modes=_BOTH_MODES,
    verification_policy=VerificationPolicy.REQUIRE_EQUIVALENT_WITHIN_MODEL,
)

RULE_SUB_SELF = OptimizationRule(
    rule_id="algebra.sub_self",
    name="Subtract a term from itself",
    formal_description="e - e → 0",
    preconditions=(
        "The matched node is a binary subtraction",
        "The two operands are structurally identical",
        "Production Z3 returned EQUIVALENT_WITHIN_MODEL for (x - x) versus 0 in Mode A and in Mode B width 4",
    ),
    supported_modes=_BOTH_MODES,
    verification_policy=VerificationPolicy.REQUIRE_EQUIVALENT_WITHIN_MODEL,
)

RULE_ADD_SELF = OptimizationRule(
    rule_id="algebra.add_self",
    name="Add a term to itself",
    formal_description="e + e → e * 2",
    preconditions=(
        "The matched node is a binary addition",
        "The two operands are structurally identical",
        "The literal 2 must be legal in the active mode; width 1 is not an admission case",
        "Production Z3 returned EQUIVALENT_WITHIN_MODEL for (x + x) versus (x * 2) in Mode A and in Mode B width 8",
    ),
    supported_modes=_BOTH_MODES,
    verification_policy=VerificationPolicy.REQUIRE_EQUIVALENT_WITHIN_MODEL,
)

RULE_DOUBLE_NEG = OptimizationRule(
    rule_id="algebra.double_neg",
    name="Cancel double negation",
    formal_description="--e → e",
    preconditions=(
        "The matched node is unary minus of unary minus",
        "Production Z3 returned EQUIVALENT_WITHIN_MODEL for (-(-x)) versus x in Mode A and in Mode B width 4",
    ),
    supported_modes=_BOTH_MODES,
    verification_policy=VerificationPolicy.REQUIRE_EQUIVALENT_WITHIN_MODEL,
)

RULE_NEG_SUB = OptimizationRule(
    rule_id="algebra.neg_sub",
    name="Negate a subtraction",
    formal_description="-(a - b) → b - a",
    preconditions=(
        "The matched node is unary minus of a subtraction",
        "Production Z3 returned EQUIVALENT_WITHIN_MODEL for (-(x - y)) versus (y - x) in Mode A and in Mode B width 4",
    ),
    supported_modes=_BOTH_MODES,
    verification_policy=VerificationPolicy.REQUIRE_EQUIVALENT_WITHIN_MODEL,
)

RULE_CONST_REASSOC = OptimizationRule(
    rule_id="algebra.const_reassoc",
    name="Reassociate added literals",
    formal_description="(e + c1) + c2 → e + (c1 + c2)",
    preconditions=(
        "The matched node is addition of a literal onto (e + literal)",
        "The summed literal must be legal in the active mode; width 2 with sum 5 is not an admission case",
        "Production Z3 returned EQUIVALENT_WITHIN_MODEL for ((x + 2) + 3) versus (x + 5) in Mode A and in Mode B width 8",
    ),
    supported_modes=_BOTH_MODES,
    verification_policy=VerificationPolicy.REQUIRE_EQUIVALENT_WITHIN_MODEL,
)

_DEFAULT_RULE_IMPLS: tuple[_RuleImpl, ...] = (
    _RuleImpl(RULE_ADD_ZERO, _try_add_zero),
    _RuleImpl(RULE_SUB_ZERO, _try_sub_zero),
    _RuleImpl(RULE_MUL_ONE, _try_mul_one),
    _RuleImpl(RULE_MUL_ZERO, _try_mul_zero),
    _RuleImpl(RULE_CONST_FOLD, _try_const_fold),
    _RuleImpl(RULE_SUB_SELF, _try_sub_self),
    _RuleImpl(RULE_ADD_SELF, _try_add_self),
    _RuleImpl(RULE_DOUBLE_NEG, _try_double_neg),
    _RuleImpl(RULE_NEG_SUB, _try_neg_sub),
    _RuleImpl(RULE_CONST_REASSOC, _try_const_reassoc),
    _RuleImpl(RULE_FACTORING, _try_factoring),
    _RuleImpl(RULE_DISTRIBUTIVITY, _try_distributivity),
)


def default_rules() -> tuple[OptimizationRule, ...]:
    """Return production rules admitted by verification.

    The four identity rules shipped in 1.0.0. The eight algebra rules were
    added only after production Z3 returned ``EQUIVALENT_WITHIN_MODEL`` for
    each template in Mode A and in the Mode B width named on the rule.
    """

    return tuple(impl.metadata for impl in _DEFAULT_RULE_IMPLS)


def rule_by_id(rule_id: str) -> OptimizationRule:
    """Look up a production rule by its unique identifier."""

    for impl in _DEFAULT_RULE_IMPLS:
        if impl.metadata.rule_id == rule_id:
            return impl.metadata
    raise OptimizerError(f"unknown optimization rule id: {rule_id!r}")


@dataclass(frozen=True, slots=True)
class ApplicableMatch:
    """A concrete match of one rule at one path in an expression tree."""

    rule: OptimizationRule
    path: Path
    before: Expr
    after: Expr
    matched_preconditions: tuple[str, ...]


def optimize(
    expression: Expression | str,
    config: SemanticConfiguration,
    *,
    policy: CorrectnessPolicy = CorrectnessPolicy.VERIFICATION_GUIDED,
    rules: Sequence[OptimizationRule] | None = None,
    max_accepted_steps: int = DEFAULT_MAX_ACCEPTED_STEPS,
) -> OptimizationResult:
    """Run the conservative optimization pipeline on ``expression``.

    Under ``VERIFICATION_GUIDED`` (the default), each candidate is checked
    against the *original* expression with the Phase 2 verifier and is
    accepted only on ``EQUIVALENT_WITHIN_MODEL``.
    """

    if policy is CorrectnessPolicy.EVALUATION_ONLY:
        raise OptimizerError(
            "EVALUATION_ONLY is reserved for veriforge.fuzzer_suite "
            "(analyze_mutation / mutate_and_analyze) and is not a "
            "production acceptance path; use VERIFICATION_GUIDED "
            "(the default)"
        )
    if policy is not CorrectnessPolicy.VERIFICATION_GUIDED:
        raise OptimizerError(f"unsupported correctness policy: {policy!r}")

    if max_accepted_steps < 0:
        raise OptimizerError("max_accepted_steps must be non-negative")

    original = _coerce_expression(expression, config)
    rule_impls = _resolve_rule_impls(rules)
    current = original
    trace: list[TransformationStep] = []
    blocked: set[tuple[Path, str]] = set()
    seen_canonical = {render_expr(original.root)}
    accepted_count = 0
    step_index = 0

    while accepted_count < max_accepted_steps:
        match = find_first_applicable(
            current.root,
            config.mode,
            rule_impls,
            blocked=blocked,
        )
        if match is None:
            break

        candidate_root = replace_at_path(current.root, match.path, match.after)
        candidate = expression_from_root(candidate_root)
        canonical = render_expr(candidate.root)
        if canonical in seen_canonical:
            verification = None
            decision = CandidateDecision.REJECTED
            rejection_reason = "candidate repeats an earlier expression"
        else:
            verification = verify_equivalence(original, candidate, config)
            decision, rejection_reason = _decide_acceptance(verification, match.rule)

        step = TransformationStep(
            step_index=step_index,
            rule_id=match.rule.rule_id,
            rule_name=match.rule.name,
            formal_description=match.rule.formal_description,
            preconditions=match.rule.preconditions,
            matched_preconditions=match.matched_preconditions,
            supported_modes=match.rule.supported_modes,
            verification_policy=match.rule.verification_policy,
            before_source=current.source,
            after_source=candidate.source,
            decision=decision,
            verification_result=verification,
            rejection_reason=rejection_reason,
        )
        trace.append(step)
        step_index += 1

        if decision is CandidateDecision.ACCEPTED:
            current = candidate
            accepted_count += 1
            seen_canonical.add(canonical)
            # Paths refer to the previous tree; clear blocks after a rewrite.
            blocked.clear()
        else:
            blocked.add((match.path, match.rule.rule_id))

    return OptimizationResult(
        original=original,
        accepted=current,
        config=config,
        policy=policy,
        trace=tuple(trace),
    )


def find_applicable_matches(
    expression: Expression | str,
    config: SemanticConfiguration,
    *,
    rules: Sequence[OptimizationRule] | None = None,
) -> tuple[ApplicableMatch, ...]:
    """Return all applicable production-rule matches under ``config.mode``.

    Does not verify or accept candidates. Useful for rule selection tests.
    """

    expr = _coerce_expression(expression, config)
    rule_impls = _resolve_rule_impls(rules)
    matches: list[ApplicableMatch] = []
    _collect_matches(expr.root, (), config.mode, rule_impls, matches)
    return tuple(matches)


def find_first_applicable(
    root: Expr,
    mode: SemanticMode,
    rule_impls: Sequence[_RuleImpl],
    *,
    blocked: Iterable[tuple[Path, str]] = (),
) -> ApplicableMatch | None:
    """Leftmost-innermost first match that is not in ``blocked``."""

    blocked_set = set(blocked)
    matches: list[ApplicableMatch] = []
    _collect_matches(root, (), mode, rule_impls, matches)
    for match in matches:
        if (match.path, match.rule.rule_id) not in blocked_set:
            return match
    return None


def try_apply_rule(node: Expr, rule: OptimizationRule) -> Expr | None:
    """Attempt a local rewrite of ``node`` with ``rule``; ``None`` if inapplicable."""

    impl = _impl_for_rule(rule)
    return impl.try_rewrite(node)


def expression_from_root(root: Expr, source: str | None = None) -> Expression:
    """Build an ``Expression`` from an IR root, rendering source when omitted."""

    rendered = source if source is not None else render_expr(root)
    return Expression(
        source=rendered,
        root=root,
        variables=_collect_variables(root),
    )


def render_expr(node: Expr) -> str:
    """Render an IR node to a parenthesized source string (safe to re-parse)."""

    return _render(node, parent_prec=0)


def replace_at_path(root: Expr, path: Path, replacement: Expr) -> Expr:
    """Return a copy of ``root`` with the node at ``path`` replaced."""

    if not path:
        return replacement

    head, *rest = path
    rest_path = tuple(rest)

    if isinstance(root, BinaryOp):
        if head == "left":
            return BinaryOp(
                op=root.op,
                left=replace_at_path(root.left, rest_path, replacement),
                right=root.right,
            )
        if head == "right":
            return BinaryOp(
                op=root.op,
                left=root.left,
                right=replace_at_path(root.right, rest_path, replacement),
            )
        raise OptimizerError(f"invalid binary path segment: {head!r}")

    if isinstance(root, UnaryOp):
        if head == "operand":
            return UnaryOp(
                op=root.op,
                operand=replace_at_path(root.operand, rest_path, replacement),
            )
        raise OptimizerError(f"invalid unary path segment: {head!r}")

    raise OptimizerError(
        f"cannot descend into {type(root).__name__} via path {path!r}"
    )


def node_at_path(root: Expr, path: Path) -> Expr:
    """Return the node at ``path`` within ``root``."""

    node: Expr = root
    for segment in path:
        if isinstance(node, BinaryOp):
            if segment == "left":
                node = node.left
            elif segment == "right":
                node = node.right
            else:
                raise OptimizerError(f"invalid binary path segment: {segment!r}")
        elif isinstance(node, UnaryOp):
            if segment == "operand":
                node = node.operand
            else:
                raise OptimizerError(f"invalid unary path segment: {segment!r}")
        else:
            raise OptimizerError(
                f"cannot descend into {type(node).__name__} via {segment!r}"
            )
    return node


def _decide_acceptance(
    verification: VerificationResult,
    rule: OptimizationRule,
) -> tuple[CandidateDecision, str | None]:
    if rule.verification_policy is not (
        VerificationPolicy.REQUIRE_EQUIVALENT_WITHIN_MODEL
    ):
        return (
            CandidateDecision.REJECTED,
            f"unsupported verification policy: {rule.verification_policy}",
        )

    if verification.status is VerificationStatus.EQUIVALENT_WITHIN_MODEL:
        return CandidateDecision.ACCEPTED, None

    return (
        CandidateDecision.REJECTED,
        (
            "candidate rejected under verification-guided policy: "
            f"verifier status {verification.status.value}"
            + (f" ({verification.reason})" if verification.reason else "")
        ),
    )


def _collect_matches(
    node: Expr,
    path: Path,
    mode: SemanticMode,
    rule_impls: Sequence[_RuleImpl],
    out: list[ApplicableMatch],
) -> None:
    # Innermost first: visit children before matching at this node.
    if isinstance(node, BinaryOp):
        _collect_matches(node.left, path + ("left",), mode, rule_impls, out)
        _collect_matches(node.right, path + ("right",), mode, rule_impls, out)
    elif isinstance(node, UnaryOp):
        _collect_matches(node.operand, path + ("operand",), mode, rule_impls, out)

    for impl in rule_impls:
        rule = impl.metadata
        if mode not in rule.supported_modes:
            continue
        after = impl.try_rewrite(node)
        if after is None:
            continue
        out.append(
            ApplicableMatch(
                rule=rule,
                path=path,
                before=node,
                after=after,
                matched_preconditions=rule.preconditions,
            )
        )


def _resolve_rule_impls(
    rules: Sequence[OptimizationRule] | None,
) -> tuple[_RuleImpl, ...]:
    if rules is None:
        return _DEFAULT_RULE_IMPLS
    return tuple(_impl_for_rule(rule) for rule in rules)


def _impl_for_rule(rule: OptimizationRule) -> _RuleImpl:
    for impl in _DEFAULT_RULE_IMPLS:
        if impl.metadata.rule_id == rule.rule_id:
            # Use the caller's metadata object so tests can supply variants,
            # but keep the production rewrite implementation.
            return _RuleImpl(rule, impl.try_rewrite)
    raise OptimizerError(
        f"no implementation registered for rule id {rule.rule_id!r}; "
        "no production rewrite is registered for this rule id"
    )


def _coerce_expression(
    value: Expression | str,
    config: SemanticConfiguration,
) -> Expression:
    if isinstance(value, Expression):
        return value
    if isinstance(value, str):
        return parse_expression(value, config)
    raise ParseError(
        f"expression must be Expression or str; got {type(value).__name__}"
    )


def _collect_variables(node: Expr) -> frozenset[str]:
    if isinstance(node, Variable):
        return frozenset({node.name})
    if isinstance(node, IntLiteral):
        return frozenset()
    if isinstance(node, UnaryOp):
        return _collect_variables(node.operand)
    if isinstance(node, BinaryOp):
        return _collect_variables(node.left) | _collect_variables(node.right)
    raise OptimizerError(f"unsupported expression node type: {type(node).__name__}")


# Precedence for parenthesized rendering (higher binds tighter).
_PREC_ADD_SUB = 10
_PREC_MUL = 20
_PREC_UNARY = 30
_PREC_ATOM = 40


def _render(node: Expr, parent_prec: int) -> str:
    if isinstance(node, IntLiteral):
        text = str(node.value)
        return text

    if isinstance(node, Variable):
        return node.name

    if isinstance(node, UnaryOp):
        operand = _render(node.operand, _PREC_UNARY)
        if node.op is UnaryOperator.PLUS:
            text = f"+{operand}"
        elif node.op is UnaryOperator.MINUS:
            text = f"-{operand}"
        else:
            raise OptimizerError(f"unsupported unary operator: {node.op}")
        if parent_prec > _PREC_UNARY:
            return f"({text})"
        return text

    if isinstance(node, BinaryOp):
        if node.op is BinaryOperator.ADD:
            prec = _PREC_ADD_SUB
            op_text = "+"
        elif node.op is BinaryOperator.SUB:
            prec = _PREC_ADD_SUB
            op_text = "-"
        elif node.op is BinaryOperator.MUL:
            prec = _PREC_MUL
            op_text = "*"
        else:
            raise OptimizerError(f"unsupported binary operator: {node.op}")

        # Left-associative: left child at same precedence, right child tighter.
        left = _render(node.left, prec)
        right = _render(node.right, prec + 1)
        text = f"{left} {op_text} {right}"
        if parent_prec > prec:
            return f"({text})"
        return text

    raise OptimizerError(f"unsupported expression node type: {type(node).__name__}")
