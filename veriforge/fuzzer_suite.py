"""Isolated mutation-testing / adversarial validation module (Phase 4).

Controlling specification §7.2 and §8:

* Artificial mutations are explicitly labeled and never mixed into production
  optimizer rules (``veriforge.optimizer_engine.default_rules``).
* Candidates never bypass the verification gate.
* Each record stores ``mutation_id`` and ``generation_method``.
* Generation is reproducible through fixed seeds.
* ``CorrectnessPolicy.EVALUATION_ONLY`` analysis may inspect deliberately
  incorrect candidates but must not accept them into the production path.

This module is not a production optimizer. Do not import mutation generators
into ``optimize()``.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

from veriforge.config import SemanticConfiguration
from veriforge.exceptions import OptimizerError, ParseError
from veriforge.models import (
    BinaryOp,
    BinaryOperator,
    CorrectnessPolicy,
    Expr,
    Expression,
    IntLiteral,
    MutationAnalysisResult,
    MutationCategory,
    MutationRecord,
    SemanticMode,
    UnaryOp,
    Variable,
    VerificationStatus,
)
from veriforge.optimizer_engine import (
    Path,
    default_rules,
    expression_from_root,
    node_at_path,
    replace_at_path,
)
from veriforge.parser_engine import parse_expression
from veriforge.verifier_engine import verify_equivalence

# Fixed default seed for reproducible mutation campaigns (Phase 4).
DEFAULT_MUTATION_SEED = 20261009

# Prefix required on every mutation_id so production rule ids cannot collide.
MUTATION_ID_PREFIX = "mutation."

GenerationMethod = str


@dataclass(frozen=True, slots=True)
class _MutationSite:
    """One applicable artificial rewrite at a concrete IR path."""

    category: MutationCategory
    path: Path
    after: Expr
    generation_method: str


def mutation_categories() -> tuple[MutationCategory, ...]:
    """Return all supported artificial mutation categories."""

    return tuple(MutationCategory)


def production_rule_ids() -> frozenset[str]:
    """Return production optimizer rule ids (must stay disjoint from mutations)."""

    return frozenset(rule.rule_id for rule in default_rules())


def assert_mutation_isolation() -> None:
    """Fail if any mutation category id collides with a production rule id."""

    prod = production_rule_ids()
    mut = frozenset(category.value for category in MutationCategory)
    overlap = prod & mut
    if overlap:
        raise OptimizerError(
            f"mutation categories collide with production rule ids: {sorted(overlap)}"
        )
    for category in MutationCategory:
        if not category.value.startswith(MUTATION_ID_PREFIX):
            raise OptimizerError(
                f"mutation category id {category.value!r} must start with "
                f"{MUTATION_ID_PREFIX!r}"
            )


def generate_mutations(
    expression: Expression | str,
    config: SemanticConfiguration,
    *,
    seed: int = DEFAULT_MUTATION_SEED,
    categories: Sequence[MutationCategory] | None = None,
    max_mutations: int | None = None,
) -> tuple[MutationRecord, ...]:
    """Generate labeled artificial mutations of ``expression``.

    Site enumeration is deterministic for a given IR shape and category set.
    When ``max_mutations`` is set, a ``random.Random(seed)`` shuffle selects
    which sites are kept (still reproducible).
    """

    assert_mutation_isolation()
    original = _coerce_expression(expression, config)
    selected = (
        tuple(categories) if categories is not None else mutation_categories()
    )
    sites = _enumerate_sites(original.root, selected, config)
    if max_mutations is not None:
        if max_mutations < 0:
            raise OptimizerError("max_mutations must be non-negative")
        rng = random.Random(seed)
        sites = list(sites)
        rng.shuffle(sites)
        sites = sites[:max_mutations]

    records: list[MutationRecord] = []
    for index, site in enumerate(sites):
        mutated_root = replace_at_path(original.root, site.path, site.after)
        mutated = expression_from_root(mutated_root)
        mutation_id = f"{site.category.value}#{seed}:{index}"
        records.append(
            MutationRecord(
                mutation_id=mutation_id,
                category=site.category,
                generation_method=site.generation_method,
                seed=seed,
                original_source=original.source,
                mutated_source=mutated.source,
                site_path=site.path,
                artificial=True,
            )
        )
    return tuple(records)


def analyze_mutation(
    mutation: MutationRecord,
    config: SemanticConfiguration,
) -> MutationAnalysisResult:
    """Analyze one artificial mutation under EVALUATION_ONLY.

    Runs the Phase 2 verifier. Never accepts the candidate into production
    optimization. ``accepted_into_production`` is always False.
    """

    if not mutation.artificial:
        raise OptimizerError(
            "refusing to analyze a record that is not marked artificial"
        )
    if mutation.category.value in production_rule_ids():
        raise OptimizerError(
            "refusing to analyze a mutation whose category collides with "
            "a production rule id"
        )

    verification = verify_equivalence(
        mutation.original_source,
        mutation.mutated_source,
        config,
    )
    detected = verification.status is not VerificationStatus.EQUIVALENT_WITHIN_MODEL
    return MutationAnalysisResult(
        mutation=mutation,
        config=config,
        policy=CorrectnessPolicy.EVALUATION_ONLY,
        verification_result=verification,
        detected_as_non_equivalent=detected,
        accepted_into_production=False,
    )


def analyze_mutations(
    mutations: Iterable[MutationRecord],
    config: SemanticConfiguration,
) -> tuple[MutationAnalysisResult, ...]:
    """Analyze many artificial mutations under EVALUATION_ONLY."""

    return tuple(analyze_mutation(record, config) for record in mutations)


def mutate_and_analyze(
    expression: Expression | str,
    config: SemanticConfiguration,
    *,
    seed: int = DEFAULT_MUTATION_SEED,
    categories: Sequence[MutationCategory] | None = None,
    max_mutations: int | None = None,
) -> tuple[MutationAnalysisResult, ...]:
    """Generate artificial mutations and analyze them under EVALUATION_ONLY."""

    records = generate_mutations(
        expression,
        config,
        seed=seed,
        categories=categories,
        max_mutations=max_mutations,
    )
    return analyze_mutations(records, config)


def _enumerate_sites(
    root: Expr,
    categories: Sequence[MutationCategory],
    config: SemanticConfiguration,
) -> list[_MutationSite]:
    category_set = set(categories)
    sites: list[_MutationSite] = []

    def visit(node: Expr, path: Path) -> None:
        if isinstance(node, BinaryOp):
            visit(node.left, path + ("left",))
            visit(node.right, path + ("right",))
        elif isinstance(node, UnaryOp):
            visit(node.operand, path + ("operand",))

        for category in MutationCategory:
            if category not in category_set:
                continue
            after = _try_mutate(node, category, config)
            if after is None:
                continue
            sites.append(
                _MutationSite(
                    category=category,
                    path=path,
                    after=after,
                    generation_method=_generation_method(category),
                )
            )

    visit(root, ())
    # Stable order: path tuple, then category value.
    sites.sort(key=lambda s: (s.path, s.category.value))
    return sites


def _generation_method(category: MutationCategory) -> GenerationMethod:
    return f"artificial_ast_rewrite:{category.value}"


def _try_mutate(
    node: Expr,
    category: MutationCategory,
    config: SemanticConfiguration,
) -> Expr | None:
    if category is MutationCategory.LITERAL_PLUS_ONE:
        if not isinstance(node, IntLiteral):
            return None
        new_value = node.value + 1
        if config.mode is SemanticMode.MODE_B and new_value > config.max_unsigned:
            return None
        if config.mode is SemanticMode.MODE_A:
            bit_limit = config.limits.max_mode_a_literal_bit_length
            if new_value.bit_length() > bit_limit:
                return None
        return IntLiteral(value=new_value)

    if category is MutationCategory.ZERO_TO_ONE:
        if isinstance(node, IntLiteral) and node.value == 0:
            return IntLiteral(value=1)
        return None

    if category is MutationCategory.ADD_TO_SUB:
        if isinstance(node, BinaryOp) and node.op is BinaryOperator.ADD:
            return BinaryOp(
                op=BinaryOperator.SUB,
                left=node.left,
                right=node.right,
            )
        return None

    if category is MutationCategory.MUL_TO_ADD:
        if isinstance(node, BinaryOp) and node.op is BinaryOperator.MUL:
            return BinaryOp(
                op=BinaryOperator.ADD,
                left=node.left,
                right=node.right,
            )
        return None

    if category is MutationCategory.SWAP_SUB_OPERANDS:
        if isinstance(node, BinaryOp) and node.op is BinaryOperator.SUB:
            return BinaryOp(
                op=BinaryOperator.SUB,
                left=node.right,
                right=node.left,
            )
        return None

    if category is MutationCategory.DROP_RIGHT_OF_ADD:
        if isinstance(node, BinaryOp) and node.op is BinaryOperator.ADD:
            # Dropping the right operand is incorrect unless the right is 0;
            # still emit the mutation so the verifier can detect it when wrong.
            return node.left
        return None

    raise OptimizerError(f"unsupported mutation category: {category!r}")


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


def rebuild_mutated(
    record: MutationRecord,
    config: SemanticConfiguration,
) -> Expression:
    """Parse the stored mutated source under ``config``."""

    return parse_expression(record.mutated_source, config)


def apply_mutation_at_site(
    original: Expression,
    category: MutationCategory,
    path: Path,
    config: SemanticConfiguration,
) -> Expression | None:
    """Apply one category at ``path``; return None if that site is inapplicable."""

    node = node_at_path(original.root, path)
    after = _try_mutate(node, category, config)
    if after is None:
        return None
    return expression_from_root(replace_at_path(original.root, path, after))


# Type alias kept for clarity in property-test helpers.
MutationGenerator = Callable[
    [Expression, SemanticConfiguration],
    tuple[MutationRecord, ...],
]
