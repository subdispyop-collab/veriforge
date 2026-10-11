"""Deterministic assurance benchmark generator, dataset version 1.1.0.

Historical ``datasets/development`` and ``datasets/held_out`` are not read
for tuning and are not overwritten. Family membership decides the partition.
Cases from one family stay together.

Ground-truth labels are not stored by this generator. It stores construction
intent only. The experiment assigns labels from the independent oracles after
the protocol hash is recorded.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

DATASET_VERSION = "1.1.0"
GENERATOR_VERSION = "1.1.0"
GENERATOR_SEED = 20261011

HELD_OUT_FAMILIES = frozenset(
    {
        "distributivity",
        "sub_self",
        "const_off_by_one",
        "modular_collapse",
        "nested_identity",
        "wrong_factor",
        "unsupported_syntax",
    }
)

# Reported categories. A category with fewer than 30 pairs is insufficient.
CATEGORY_MINIMUM = 30


@dataclass(frozen=True, slots=True)
class GeneratedCase:
    case_id: str
    family: str
    partition: str
    category: str
    semantic_mode: str
    bit_width: int | None
    original_source: str
    candidate_source: str
    construction_intent: str
    inclusion_reason: str

    def fingerprint_row(self) -> dict[str, object]:
        return {
            "bit_width": self.bit_width,
            "candidate_source": self.candidate_source,
            "case_id": self.case_id,
            "category": self.category,
            "construction_intent": self.construction_intent,
            "family": self.family,
            "original_source": self.original_source,
            "partition": self.partition,
            "semantic_mode": self.semantic_mode,
        }


def partition_for(family: str) -> str:
    if family in HELD_OUT_FAMILIES:
        return "held_out"
    return "development"


def generate_cases() -> tuple[GeneratedCase, ...]:
    """Return the full versioned case list in stable order."""

    raw: list[tuple[str, str, str, str, int | None, str, str, str]] = []
    raw.extend(_algebraic())
    raw.extend(_inequivalent())
    raw.extend(_mode_traps())
    raw.extend(_robustness())
    raw.extend(_sample_size_fill())
    cases: list[GeneratedCase] = []
    seen: set[tuple[object, ...]] = set()
    for family, category, mode, width, original, candidate, intent, reason in raw:
        key = (mode, width, _norm(original), _norm(candidate), family)
        if key in seen:
            continue
        seen.add(key)
        partition = partition_for(family)
        index = len(cases) + 1
        cases.append(
            GeneratedCase(
                case_id=f"av1-{index:04d}",
                family=family,
                partition=partition,
                category=category,
                semantic_mode=mode,
                bit_width=width,
                original_source=original,
                candidate_source=candidate,
                construction_intent=intent,
                inclusion_reason=reason,
            )
        )
    return tuple(cases)


def dataset_canonical_bytes(cases: tuple[GeneratedCase, ...] | list[GeneratedCase]) -> bytes:
    rows = [case.fingerprint_row() for case in cases]
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    return payload.encode("utf-8")


def dataset_hash(cases: tuple[GeneratedCase, ...] | list[GeneratedCase]) -> str:
    return hashlib.sha256(dataset_canonical_bytes(cases)).hexdigest()


def _norm(source: str) -> str:
    return " ".join(source.split())


def _algebraic() -> list[tuple]:
    rows: list[tuple] = []
    variables = ("x", "y", "z", "a", "b")
    widths = (1, 2, 4, 8)

    def add(family: str, mode: str, width: int | None, original: str, candidate: str, reason: str) -> None:
        rows.append(
            (
                family,
                "equivalent_algebraic",
                mode,
                width,
                original,
                candidate,
                "equivalent",
                reason,
            )
        )

    for var in variables:
        add("add_zero", "mode_a", None, f"({var} + 0)", var, "add zero")
        add("sub_zero", "mode_a", None, f"({var} - 0)", var, "subtract zero")
        add("mul_one", "mode_a", None, f"({var} * 1)", var, "multiply by one")
        add("mul_zero", "mode_a", None, f"({var} * 0)", "0", "multiply by zero")
        add("double_neg", "mode_a", None, f"(-(-{var}))", var, "double negation")
        for width in widths:
            if width >= 1:
                add("add_zero", "mode_b", width, f"({var} + 0)", var, "add zero")
                add("sub_zero", "mode_b", width, f"({var} - 0)", var, "subtract zero")
                add("mul_one", "mode_b", width, f"({var} * 1)", var, "multiply by one")
                add("mul_zero", "mode_b", width, f"({var} * 0)", "0", "multiply by zero")
                add("double_neg", "mode_b", width, f"(-(-{var}))", var, "double negation")

    for left, right in (("x", "y"), ("y", "z"), ("a", "b"), ("x", "a")):
        add("comm_add", "mode_a", None, f"({left} + {right})", f"({right} + {left})", "add commutes")
        add("comm_mul", "mode_a", None, f"({left} * {right})", f"({right} * {left})", "mul commutes")
        add("sub_self", "mode_a", None, f"({left} - {left})", "0", "subtract self")
        add("neg_sub", "mode_a", None, f"(-({left} - {right}))", f"({right} - {left})", "negated difference")
        for width in widths:
            add("comm_add", "mode_b", width, f"({left} + {right})", f"({right} + {left})", "add commutes")
            add("comm_mul", "mode_b", width, f"({left} * {right})", f"({right} * {left})", "mul commutes")
            add("sub_self", "mode_b", width, f"({left} - {left})", "0", "subtract self")
            add("neg_sub", "mode_b", width, f"(-({left} - {right}))", f"({right} - {left})", "negated difference")
            if width >= 2:
                add(
                    "add_self",
                    "mode_b",
                    width,
                    f"({left} + {left})",
                    f"({left} * 2)",
                    "x+x to 2*x where literal 2 is in range",
                )
        add("add_self", "mode_a", None, f"({left} + {left})", f"({left} * 2)", "x+x to 2*x")

    for var in ("x", "y", "z"):
        add(
            "assoc_add",
            "mode_a",
            None,
            f"(({var} + 1) + 2)",
            f"({var} + (1 + 2))",
            "addition associates",
        )
        add(
            "const_reassoc",
            "mode_a",
            None,
            f"(({var} + 2) + 3)",
            f"({var} + 5)",
            "constant reassociation",
        )
        add("const_fold", "mode_a", None, f"(({var} * 1) + (2 + 3))", f"({var} + 5)", "fold constants")
        for width in (4, 8):
            add(
                "assoc_add",
                "mode_b",
                width,
                f"(({var} + 1) + 2)",
                f"({var} + (1 + 2))",
                "addition associates",
            )
            add(
                "const_reassoc",
                "mode_b",
                width,
                f"(({var} + 2) + 3)",
                f"({var} + 5)",
                "constant reassociation inside range",
            )
            add(
                "const_fold",
                "mode_b",
                width,
                f"(({var} * 1) + (2 + 3))",
                f"({var} + 5)",
                "fold constants inside range",
            )

    for width in (1, 2, 4):
        for var in ("x", "y", "a"):
            add(
                "distributivity",
                "mode_b",
                width,
                f"({var} * (y + z))" if var == "x" else f"({var} * (a + 1))",
                f"(({var} * y) + ({var} * z))" if var == "x" else f"(({var} * a) + ({var} * 1))",
                "multiplication distributes over addition",
            )
    add("distributivity", "mode_a", None, "(x * (y + z))", "((x * y) + (x * z))", "distributivity")
    add("distributivity", "mode_a", None, "(a * (b + 1))", "((a * b) + (a * 1))", "distributivity")
    add("distributivity", "mode_a", None, "(y * (x + z))", "((y * x) + (y * z))", "distributivity")
    for width in (2, 4, 8):
        add(
            "distributivity",
            "mode_b",
            width,
            "(x * (y + z))",
            "((x * y) + (x * z))",
            "distributivity",
        )
    add("factoring", "mode_a", None, "((x * y) + (x * z))", "(x * (y + z))", "factor common x")
    add("factoring", "mode_a", None, "((a * b) + (a * 1))", "(a * (b + 1))", "factor common a")
    for width in (1, 2, 4, 8):
        add(
            "factoring",
            "mode_b",
            width,
            "((x * y) + (x * z))",
            "(x * (y + z))",
            "factor common x",
        )

    # Nested identities, varied but still one family.
    nests = (
        "(((x + 0) * 1) - 0)",
        "((y * 1) + 0)",
        "(((a - 0) * 1) * 1)",
        "((z + 0) + 0)",
        "(((b * 0) + x) * 1)",
    )
    simplified = ("x", "y", "a", "z", "x")
    for original, candidate in zip(nests, simplified):
        add("nested_identity", "mode_a", None, original, candidate, "nested identity rules")
        for width in widths:
            add(
                "nested_identity",
                "mode_b",
                width,
                original,
                candidate,
                "nested identity rules",
            )
    return rows


def _inequivalent() -> list[tuple]:
    rows: list[tuple] = []
    specs = (
        ("const_off_by_one", "(x + 1)", "(x + 2)", "constant differs by one"),
        ("const_off_by_one", "(y + 0)", "(y + 1)", "added one"),
        ("const_off_by_one", "(a * 1)", "(a * 2)", "factor differs"),
        ("op_swap", "(x + y)", "(x - y)", "addition replaced by subtraction"),
        ("op_swap", "(a * b)", "(a + b)", "multiplication replaced by addition"),
        ("drop_term", "(x + y)", "x", "dropped addend"),
        ("drop_term", "(a + 1)", "a", "dropped constant"),
        ("mul_to_add", "(x * y)", "(x + y)", "mul rewritten as add"),
        ("swap_sub", "(x - y)", "(y - x)", "subtraction operands swapped"),
        ("swap_sub", "(a - 1)", "(1 - a)", "subtraction operands swapped"),
        ("wrong_factor", "(x * 2)", "(x * 3)", "wrong constant factor"),
        ("wrong_factor", "(y * y)", "(y + y)", "square replaced by sum"),
    )
    for family, original, candidate, reason in specs:
        rows.append(
            (
                family,
                "non_equivalent",
                "mode_a",
                None,
                original,
                candidate,
                "non_equivalent",
                reason,
            )
        )
        for width in (1, 2, 4, 8):
            # Skip candidates whose literals fall outside the width.
            if width == 1 and any(token in original + candidate for token in ("2", "3")):
                continue
            if width == 1 and "1" in candidate and family == "const_off_by_one" and "2" in candidate:
                continue
            # In width 1, subtraction coincides with addition, so add/sub swaps
            # and operand swaps of subtraction are equivalences. That was found
            # by a development-only oracle check before the protocol was hashed.
            # Held-out families are not rewritten here.
            mode_b_intent = "non_equivalent"
            mode_b_category = "non_equivalent"
            if width == 1 and family == "swap_sub":
                mode_b_intent = "mode_dependent"
                mode_b_category = "mode_dependent"
            if width == 1 and family == "op_swap" and "+" in original and "-" in candidate:
                mode_b_intent = "mode_dependent"
                mode_b_category = "mode_dependent"
            rows.append(
                (
                    family,
                    mode_b_category,
                    "mode_b",
                    width,
                    original,
                    candidate,
                    mode_b_intent,
                    reason
                    + (
                        "; width-1 ring identity"
                        if mode_b_intent == "mode_dependent"
                        else ""
                    ),
                )
            )
    # Boundary non-equivalence at the top of the unsigned range.
    for width, literal in ((4, 15), (8, 255)):
        rows.append(
            (
                "const_off_by_one",
                "boundary",
                "mode_b",
                width,
                f"(x + {literal})",
                "(x + 0)",
                "non_equivalent",
                "top-of-range constant replaced by zero",
            )
        )
        rows.append(
            (
                "const_off_by_one",
                "boundary",
                "mode_a",
                None,
                f"(x + {literal})",
                "(x + 0)",
                "non_equivalent",
                "large constant replaced by zero",
            )
        )
    return rows


def _mode_traps() -> list[tuple]:
    """Pairs whose equivalence depends on the semantic mode."""

    rows: list[tuple] = []
    traps = (
        (8, "(x + 255)", "(x - 1)", "255 wraps to -1 only in width 8"),
        (8, "(-1)", "255", "unary minus one is all-ones only in width 8"),
        (8, "((x + 128) + 128)", "x", "128+128 wraps to 0 only in width 8"),
        (4, "((x + 8) + 8)", "x", "8+8 wraps to 0 only in width 4"),
        (4, "(y + 15)", "(y - 1)", "15 wraps to -1 only in width 4"),
        (2, "((a + 2) + 2)", "a", "2+2 wraps to 0 only in width 2"),
    )
    for width, original, candidate, reason in traps:
        for mode in ("mode_a", "mode_b"):
            rows.append(
                (
                    "modular_collapse",
                    "mode_dependent",
                    mode,
                    width if mode == "mode_b" else None,
                    original,
                    candidate,
                    "mode_dependent",
                    reason,
                )
            )
    # Equivalent over integers, illegal as a Mode B width-1 candidate.
    range_traps = (
        (1, "(x + x)", "(x * 2)", "literal 2 is outside width 1"),
        (1, "((y + 1) + 1)", "(y + 2)", "literal 2 is outside width 1"),
        (2, "((a + 1) + 3)", "(a + 4)", "literal 4 is outside width 2"),
        (3, "((z + 4) + 4)", "(z + 8)", "literal 8 is outside width 3"),
    )
    for width, original, candidate, reason in range_traps:
        rows.append(
            (
                "literal_range",
                "mode_dependent",
                "mode_a",
                None,
                original,
                candidate,
                "equivalent_in_mode_a",
                reason,
            )
        )
        rows.append(
            (
                "literal_range",
                "mode_dependent",
                "mode_b",
                width,
                original,
                candidate,
                "invalid_in_mode_b",
                reason,
            )
        )
    return rows


def _sample_size_fill() -> list[tuple]:
    """Raise category counts to the preregistered minimum of 30.

    These templates were fixed before any held-out oracle result was read.
    """

    rows: list[tuple] = []
    # Additional held-out non-equivalent pairs (existing held-out families).
    extra_wrong = (
        ("(x * 4)", "(x * 5)", 8),
        ("(y * 3)", "(y + 3)", 8),
        ("(a * a)", "(a * 1)", 4),
        ("(z * 2)", "(z + 0)", 4),
        ("(b * 3)", "(b * 1)", 8),
        ("(x * y)", "(x * x)", 4),
        ("(y + 3)", "(y + 4)", 8),
        ("(a - 2)", "(a - 1)", 4),
    )
    for original, candidate, width in extra_wrong:
        rows.append(
            (
                "wrong_factor",
                "non_equivalent",
                "mode_a",
                None,
                original,
                candidate,
                "non_equivalent",
                "additional held-out non-equivalent pair",
            )
        )
        rows.append(
            (
                "wrong_factor",
                "non_equivalent",
                "mode_b",
                width,
                original,
                candidate,
                "non_equivalent",
                "additional held-out non-equivalent pair",
            )
        )
    # Boundary category, development family, both equivalence directions.
    boundary_eq = (
        (4, "(x + 15)", "(x - 1)"),  # this is mode-dependent, do not use as generic eq
    )
    del boundary_eq
    for var, width, top in (
        ("x", 4, 15),
        ("y", 4, 15),
        ("z", 8, 255),
        ("a", 8, 255),
        ("b", 8, 255),
        ("x", 8, 255),
    ):
        rows.append(
            (
                "boundary_values",
                "boundary",
                "mode_b",
                width,
                f"({var} + 0)",
                var,
                "equivalent",
                "boundary variable plus zero",
            )
        )
        rows.append(
            (
                "boundary_values",
                "boundary",
                "mode_b",
                width,
                f"({var} + {top})",
                f"({var} + 1)",
                "non_equivalent",
                "top-of-range constant is not one",
            )
        )
        rows.append(
            (
                "boundary_values",
                "boundary",
                "mode_a",
                None,
                f"({var} + {top})",
                f"({var} + {top})",
                "equivalent",
                "identical boundary expression",
            )
        )
    for var, width, top in (("x", 2, 3), ("y", 2, 3), ("z", 1, 1), ("a", 1, 1)):
        rows.append(
            (
                "boundary_values",
                "boundary",
                "mode_b",
                width,
                f"({var} - 0)",
                var,
                "equivalent",
                "boundary subtract-zero at a small width",
            )
        )
        rows.append(
            (
                "boundary_values",
                "boundary",
                "mode_b",
                width,
                f"({var} + {top})",
                f"({var} + 0)",
                "non_equivalent",
                "top-of-range constant is not zero",
            )
        )
        rows.append(
            (
                "boundary_values",
                "boundary",
                "mode_b",
                width,
                f"({var} - 0)",
                var,
                "equivalent",
                "boundary subtract zero",
            )
        )
    # More modular collapses so mode_dependent reaches 30.
    more_traps = (
        (8, "(y + 255)", "(y - 1)"),
        (8, "((y + 128) + 128)", "y"),
        (4, "(a + 15)", "(a - 1)"),
        (4, "((z + 8) + 8)", "z"),
        (8, "((a + 128) + 128)", "a"),
        (2, "(x + 3)", "(x - 1)"),
    )
    for width, original, candidate in more_traps:
        for mode in ("mode_a", "mode_b"):
            rows.append(
                (
                    "modular_collapse",
                    "mode_dependent",
                    mode,
                    width if mode == "mode_b" else None,
                    original,
                    candidate,
                    "mode_dependent",
                    "additional modular-collapse pair fixed before evaluation",
                )
            )
    return rows


def _robustness() -> list[tuple]:
    rows: list[tuple] = []
    unsupported = (
        "x / y",
        "x % 2",
        "x // 2",
        "x << 1",
        "x >> 1",
        "x ** 2",
        "x & 1",
        "x | 1",
        "x ^ 1",
        "~x",
        "x == 1",
        "x < 1",
        "not x",
        "f(x)",
        "1.5",
        "(x,)",
        "x.y",
    )
    for source in unsupported:
        rows.append(
            (
                "unsupported_syntax",
                "robustness",
                "mode_a",
                None,
                source,
                "x",
                "unsupported",
                "syntax outside the arithmetic grammar",
            )
        )
        rows.append(
            (
                "unsupported_syntax",
                "robustness",
                "mode_b",
                8,
                source,
                "x",
                "unsupported",
                "syntax outside the arithmetic grammar",
            )
        )
    malformed = (
        "",
        "x +",
        "((x)",
        "01",
        "True",
        "False",
        "0b2",
        "0x",
        "x + +",
    )
    for source in malformed:
        rows.append(
            (
                "malformed_input",
                "robustness",
                "mode_a",
                None,
                source,
                "0",
                "invalid_input",
                "malformed or rejected literal",
            )
        )
    # Out-of-range Mode B literals are invalid, not wrapped.
    rows.append(
        (
            "malformed_input",
            "robustness",
            "mode_b",
            8,
            "(x + 256)",
            "x",
            "invalid_input",
            "literal 256 is outside width 8 and must not wrap",
        )
    )
    rows.append(
        (
            "malformed_input",
            "robustness",
            "mode_b",
            4,
            "16",
            "0",
            "invalid_input",
            "literal 16 is outside width 4",
        )
    )
    return rows
