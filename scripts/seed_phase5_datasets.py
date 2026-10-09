"""Generate Phase 5 seed datasets under datasets/development and datasets/held_out.

Idempotent. Does not run evaluation. Enforces near-duplicate separation.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from veriforge.config import SemanticConfiguration  # noqa: E402
from veriforge.dataset_engine import (  # noqa: E402
    assert_no_cross_partition_leakage,
    build_case,
    write_bundle,
)
from veriforge.models import (  # noqa: E402
    ARTIFICIAL_90_10_MIX,
    DatasetBundle,
    DatasetMetadata,
    DatasetPartition,
    ExpectedOutcome,
    SemanticMode,
    TransformationCategory,
)


CREATED_AT = "2026-10-09T00:00:00Z"
SEED = 20261009
VERSION = "0.5.0"


def mode_a() -> SemanticConfiguration:
    return SemanticConfiguration(mode=SemanticMode.MODE_A)


def mode_b(width: int = 32) -> SemanticConfiguration:
    return SemanticConfiguration(mode=SemanticMode.MODE_B, bit_width=width)


def development_cases() -> list:
    a = mode_a()
    b = mode_b(32)
    b8 = mode_b(8)
    cases = [
        build_case(
            case_id="dev-hand-001",
            original_source="x + 0",
            candidate_source="x",
            config=a,
            transformation_category=TransformationCategory.IDENTITY_PRESERVING,
            expected_outcome=ExpectedOutcome.EQUIVALENT,
            inclusion_reason="hand-checked Mode A identity add-zero",
        ),
        build_case(
            case_id="dev-hand-002",
            original_source="x * 1",
            candidate_source="x",
            config=a,
            transformation_category=TransformationCategory.IDENTITY_PRESERVING,
            expected_outcome=ExpectedOutcome.EQUIVALENT,
            inclusion_reason="hand-checked Mode A identity mul-one",
        ),
        build_case(
            case_id="dev-hand-003",
            original_source="(y - 0) * 1",
            candidate_source="y",
            config=a,
            transformation_category=TransformationCategory.VALID_REWRITE,
            expected_outcome=ExpectedOutcome.EQUIVALENT,
            inclusion_reason="nested identity rewrite under Mode A",
        ),
        build_case(
            case_id="dev-incorrect-001",
            original_source="x + 1",
            candidate_source="x + 2",
            config=a,
            transformation_category=TransformationCategory.INCORRECT_REWRITE,
            expected_outcome=ExpectedOutcome.NON_EQUIVALENT,
            inclusion_reason="deliberately incorrect constant shift",
            labels={"role": "incorrect"},
        ),
        build_case(
            case_id="dev-incorrect-002",
            original_source="a * b",
            candidate_source="a + b",
            config=a,
            transformation_category=TransformationCategory.ARTIFICIAL_MUTATION,
            expected_outcome=ExpectedOutcome.NON_EQUIVALENT,
            inclusion_reason="mul-to-add style artificial mutation seed",
            labels={"role": "incorrect"},
        ),
        build_case(
            case_id="dev-boundary-001",
            original_source="255 + 1",
            candidate_source="0",
            config=b8,
            transformation_category=TransformationCategory.BOUNDARY_VALUE,
            expected_outcome=ExpectedOutcome.EQUIVALENT,
            inclusion_reason="Mode B width-8 wraparound boundary",
        ),
        build_case(
            case_id="dev-nested-001",
            original_source="((x + y) + 0) * 1",
            candidate_source="x + y",
            config=a,
            transformation_category=TransformationCategory.NESTED_EXPRESSION,
            expected_outcome=ExpectedOutcome.EQUIVALENT,
            inclusion_reason="nested expression with identity removals",
        ),
        build_case(
            case_id="dev-modeb-001",
            original_source="x * 0",
            candidate_source="0",
            config=b,
            transformation_category=TransformationCategory.IDENTITY_PRESERVING,
            expected_outcome=ExpectedOutcome.EQUIVALENT,
            inclusion_reason="Mode B mul-zero identity",
        ),
        build_case(
            case_id="dev-malformed-001",
            original_source="x(",
            candidate_source=None,
            config=a,
            transformation_category=TransformationCategory.UNSUPPORTED_OR_MALFORMED,
            expected_outcome=ExpectedOutcome.PARSE_REJECT,
            inclusion_reason="malformed source for parser rejection",
            parse_for_complexity=False,
        ),
        build_case(
            case_id="dev-unsupported-001",
            original_source="x / y",
            candidate_source=None,
            config=a,
            transformation_category=TransformationCategory.UNSUPPORTED_OR_MALFORMED,
            expected_outcome=ExpectedOutcome.UNSUPPORTED,
            inclusion_reason="division unsupported in initial grammar",
            parse_for_complexity=False,
        ),
        # Controlled 90/10 mix members are labeled; mix is not prevalence.
        build_case(
            case_id="dev-mix-correct-001",
            original_source="z - 0",
            candidate_source="z",
            config=a,
            transformation_category=TransformationCategory.VALID_REWRITE,
            expected_outcome=ExpectedOutcome.EQUIVALENT,
            inclusion_reason="controlled-mix correct member (artificial config)",
            labels={
                "controlled_mix": "90_10",
                "mix_role": "correct",
            },
            notes=ARTIFICIAL_90_10_MIX.label,
        ),
        build_case(
            case_id="dev-mix-incorrect-001",
            original_source="z + w",
            candidate_source="z - w",
            config=a,
            transformation_category=TransformationCategory.INCORRECT_REWRITE,
            expected_outcome=ExpectedOutcome.NON_EQUIVALENT,
            inclusion_reason="controlled-mix incorrect member (artificial config)",
            labels={
                "controlled_mix": "90_10",
                "mix_role": "incorrect",
            },
            notes=ARTIFICIAL_90_10_MIX.label,
        ),
    ]
    return cases


def held_out_cases() -> list:
    """Held-out seed cases. Distinct near-duplicate keys from development."""

    a = mode_a()
    b = mode_b(32)
    b16 = mode_b(16)
    return [
        build_case(
            case_id="hold-hand-001",
            original_source="p + 0",
            candidate_source="p",
            config=a,
            transformation_category=TransformationCategory.IDENTITY_PRESERVING,
            expected_outcome=ExpectedOutcome.EQUIVALENT,
            inclusion_reason="held-out Mode A identity add-zero (distinct vars)",
        ),
        build_case(
            case_id="hold-hand-002",
            original_source="q * 1",
            candidate_source="q",
            config=a,
            transformation_category=TransformationCategory.IDENTITY_PRESERVING,
            expected_outcome=ExpectedOutcome.EQUIVALENT,
            inclusion_reason="held-out Mode A identity mul-one",
        ),
        build_case(
            case_id="hold-incorrect-001",
            original_source="m + 3",
            candidate_source="m + 5",
            config=a,
            transformation_category=TransformationCategory.INCORRECT_REWRITE,
            expected_outcome=ExpectedOutcome.NON_EQUIVALENT,
            inclusion_reason="held-out incorrect constant shift",
            labels={"role": "incorrect"},
        ),
        build_case(
            case_id="hold-incorrect-002",
            original_source="u - v",
            candidate_source="v - u",
            config=a,
            transformation_category=TransformationCategory.ARTIFICIAL_MUTATION,
            expected_outcome=ExpectedOutcome.NON_EQUIVALENT,
            inclusion_reason="held-out swap-sub style artificial mutation seed",
            labels={"role": "incorrect"},
        ),
        build_case(
            case_id="hold-boundary-001",
            original_source="65535 + 1",
            candidate_source="0",
            config=b16,
            transformation_category=TransformationCategory.BOUNDARY_VALUE,
            expected_outcome=ExpectedOutcome.EQUIVALENT,
            inclusion_reason="Mode B width-16 wraparound boundary",
        ),
        build_case(
            case_id="hold-nested-001",
            original_source="((r * 1) - 0) + s",
            candidate_source="r + s",
            config=a,
            transformation_category=TransformationCategory.NESTED_EXPRESSION,
            expected_outcome=ExpectedOutcome.EQUIVALENT,
            inclusion_reason="held-out nested identity cleanup",
        ),
        build_case(
            case_id="hold-modeb-001",
            original_source="t - 0",
            candidate_source="t",
            config=b,
            transformation_category=TransformationCategory.IDENTITY_PRESERVING,
            expected_outcome=ExpectedOutcome.EQUIVALENT,
            inclusion_reason="held-out Mode B sub-zero",
        ),
        build_case(
            case_id="hold-malformed-001",
            original_source="import os",
            candidate_source=None,
            config=a,
            transformation_category=TransformationCategory.UNSUPPORTED_OR_MALFORMED,
            expected_outcome=ExpectedOutcome.PARSE_REJECT,
            inclusion_reason="held-out import rejection",
            parse_for_complexity=False,
        ),
    ]


def main() -> None:
    root = ROOT / "datasets"
    dev_cases = development_cases()
    hold_cases = held_out_cases()
    assert_no_cross_partition_leakage(dev_cases, hold_cases)

    mix_label = ARTIFICIAL_90_10_MIX.label
    dev_meta = DatasetMetadata(
        dataset_version=VERSION,
        generation_procedure=(
            "Hand-authored Phase 5 seed cases via scripts/seed_phase5_datasets.py; "
            "near-duplicate keys from normalized original/candidate + category + mode."
        ),
        semantic_model="mode_a_and_mode_b_unsigned_as_per_docs/SEMANTICS.md",
        random_seed=SEED,
        partition=DatasetPartition.DEVELOPMENT,
        case_count=len(dev_cases),
        created_at_utc=CREATED_AT,
        description=(
            "Development partition for protocol/method work. Includes labeled "
            "members of an artificial 90/10 controlled mix configuration."
        ),
        controlled_mix=True,
        controlled_mix_label=mix_label,
    )
    hold_meta = DatasetMetadata(
        dataset_version=VERSION,
        generation_procedure=(
            "Hand-authored Phase 5 held-out seed cases via "
            "scripts/seed_phase5_datasets.py; keys checked against development "
            "to prevent near-duplicate leakage. Not evaluated in Phase 5."
        ),
        semantic_model="mode_a_and_mode_b_unsigned_as_per_docs/SEMANTICS.md",
        random_seed=SEED,
        partition=DatasetPartition.HELD_OUT,
        case_count=len(hold_cases),
        created_at_utc=CREATED_AT,
        description=(
            "Held-out partition reserved for final evaluation (Phase 10). "
            "Phase 5 must not run evaluation against this partition."
        ),
        controlled_mix=False,
        controlled_mix_label=None,
    )
    write_bundle(DatasetBundle(metadata=dev_meta, cases=tuple(dev_cases)), root=root)
    write_bundle(DatasetBundle(metadata=hold_meta, cases=tuple(hold_cases)), root=root)
    print(f"wrote {len(dev_cases)} development cases and {len(hold_cases)} held_out cases")


if __name__ == "__main__":
    main()
