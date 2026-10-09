"""Versioned research datasets with development / held-out separation (§9.4).

Phase 5 responsibility: load, validate, and fingerprint dataset partitions;
prevent near-duplicate leakage across partitions; support controlled-mix
metadata. Does not run held-out evaluation.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from veriforge.config import SemanticConfiguration
from veriforge.exceptions import VeriforgeError
from veriforge.models import (
    ARTIFICIAL_90_10_MIX,
    ComplexityCharacteristics,
    ControlledMixConfiguration,
    DatasetBundle,
    DatasetCase,
    DatasetMetadata,
    DatasetPartition,
    ExpectedOutcome,
    Expression,
    SemanticMode,
    TransformationCategory,
)
from veriforge.parser_engine import parse_expression

# Package-relative default roots (repo layout).
DEFAULT_DATASETS_ROOT = Path(__file__).resolve().parent.parent / "datasets"
DEVELOPMENT_DIRNAME = DatasetPartition.DEVELOPMENT.value
HELD_OUT_DIRNAME = DatasetPartition.HELD_OUT.value

METADATA_FILENAME = "metadata.json"
CASES_FILENAME = "cases.jsonl"

# Whitespace / trivial formatting normalization for near-duplicate keys.
_WS_RE = re.compile(r"\s+")


class DatasetError(VeriforgeError):
    """Dataset construction, validation, or leakage-control failure."""


def datasets_root(root: Path | None = None) -> Path:
    """Return the datasets root directory."""

    return Path(root) if root is not None else DEFAULT_DATASETS_ROOT


def partition_dir(
    partition: DatasetPartition, *, root: Path | None = None
) -> Path:
    """Return the directory for one partition."""

    return datasets_root(root) / partition.value


def normalize_expression_text(source: str) -> str:
    """Normalize source text for near-duplicate comparison.

    Collapses whitespace and strips. Does not rewrite operators or
    parentheses; that would change meaning under this grammar.
    """

    return _WS_RE.sub(" ", source.strip())


def near_duplicate_key(
    original_source: str,
    candidate_source: str | None,
    transformation_category: TransformationCategory,
    semantic_mode: SemanticMode,
    bit_width: int | None,
) -> str:
    """Stable key used to detect cross-partition near-duplicates (§9.4).

    Cases that share the same normalized original/candidate pair under the
    same category and semantic model are treated as near-duplicates (or
    variants of the same underlying transformation).
    """

    orig = normalize_expression_text(original_source)
    cand = (
        normalize_expression_text(candidate_source)
        if candidate_source is not None
        else ""
    )
    width = "" if bit_width is None else str(bit_width)
    return "|".join(
        (
            semantic_mode.value,
            width,
            transformation_category.value,
            orig,
            cand,
        )
    )


def compute_complexity(
    expression: Expression | None,
    *,
    source: str,
    failed_parse: bool = False,
) -> ComplexityCharacteristics:
    """Record complexity characteristics for a case.

    When parsing fails (malformed / unsupported cases), counts are derived
    from the source string alone and AST fields are zeroed.
    """

    if failed_parse or expression is None:
        return ComplexityCharacteristics(
            source_length=len(source),
            ast_node_count=0,
            nesting_depth=0,
            variable_count=0,
            operator_count=0,
            literal_count=0,
        )

    from veriforge.models import BinaryOp, IntLiteral, UnaryOp, Variable

    nodes = 0
    nesting = 0
    operators = 0
    literals = 0

    def walk(node: object, depth: int) -> None:
        nonlocal nodes, nesting, operators, literals
        nodes += 1
        nesting = max(nesting, depth)
        if isinstance(node, IntLiteral):
            literals += 1
        elif isinstance(node, Variable):
            return
        elif isinstance(node, UnaryOp):
            operators += 1
            walk(node.operand, depth + 1)
        elif isinstance(node, BinaryOp):
            operators += 1
            walk(node.left, depth + 1)
            walk(node.right, depth + 1)

    walk(expression.root, 1)
    return ComplexityCharacteristics(
        source_length=len(source),
        ast_node_count=nodes,
        nesting_depth=nesting,
        variable_count=len(expression.variables),
        operator_count=operators,
        literal_count=literals,
    )


def _complexity_to_dict(c: ComplexityCharacteristics) -> dict[str, int]:
    return {
        "source_length": c.source_length,
        "ast_node_count": c.ast_node_count,
        "nesting_depth": c.nesting_depth,
        "variable_count": c.variable_count,
        "operator_count": c.operator_count,
        "literal_count": c.literal_count,
    }


def _complexity_from_dict(data: Mapping[str, Any]) -> ComplexityCharacteristics:
    return ComplexityCharacteristics(
        source_length=int(data["source_length"]),
        ast_node_count=int(data["ast_node_count"]),
        nesting_depth=int(data["nesting_depth"]),
        variable_count=int(data["variable_count"]),
        operator_count=int(data["operator_count"]),
        literal_count=int(data["literal_count"]),
    )


def case_to_dict(case: DatasetCase) -> dict[str, Any]:
    """Serialize one case to a JSON-compatible mapping."""

    return {
        "case_id": case.case_id,
        "original_source": case.original_source,
        "candidate_source": case.candidate_source,
        "semantic_mode": case.semantic_mode.value,
        "bit_width": case.bit_width,
        "transformation_category": case.transformation_category.value,
        "expected_outcome": case.expected_outcome.value,
        "complexity": _complexity_to_dict(case.complexity),
        "inclusion_reason": case.inclusion_reason,
        "exclusion_reason": case.exclusion_reason,
        "near_duplicate_key": case.near_duplicate_key,
        "notes": case.notes,
        "labels": dict(case.labels),
    }


def case_from_dict(data: Mapping[str, Any]) -> DatasetCase:
    """Deserialize one case from a mapping."""

    bit_width = data.get("bit_width")
    return DatasetCase(
        case_id=str(data["case_id"]),
        original_source=str(data["original_source"]),
        candidate_source=(
            None
            if data.get("candidate_source") is None
            else str(data["candidate_source"])
        ),
        semantic_mode=SemanticMode(str(data["semantic_mode"])),
        bit_width=None if bit_width is None else int(bit_width),
        transformation_category=TransformationCategory(
            str(data["transformation_category"])
        ),
        expected_outcome=ExpectedOutcome(str(data["expected_outcome"])),
        complexity=_complexity_from_dict(data["complexity"]),
        inclusion_reason=str(data["inclusion_reason"]),
        exclusion_reason=(
            None
            if data.get("exclusion_reason") is None
            else str(data["exclusion_reason"])
        ),
        near_duplicate_key=(
            None
            if data.get("near_duplicate_key") is None
            else str(data["near_duplicate_key"])
        ),
        notes=None if data.get("notes") is None else str(data["notes"]),
        labels={str(k): str(v) for k, v in dict(data.get("labels") or {}).items()},
    )


def metadata_to_dict(meta: DatasetMetadata) -> dict[str, Any]:
    return {
        "dataset_version": meta.dataset_version,
        "generation_procedure": meta.generation_procedure,
        "semantic_model": meta.semantic_model,
        "random_seed": meta.random_seed,
        "partition": meta.partition.value,
        "case_count": meta.case_count,
        "created_at_utc": meta.created_at_utc,
        "description": meta.description,
        "controlled_mix": meta.controlled_mix,
        "controlled_mix_label": meta.controlled_mix_label,
    }


def metadata_from_dict(data: Mapping[str, Any]) -> DatasetMetadata:
    return DatasetMetadata(
        dataset_version=str(data["dataset_version"]),
        generation_procedure=str(data["generation_procedure"]),
        semantic_model=str(data["semantic_model"]),
        random_seed=(
            None if data.get("random_seed") is None else int(data["random_seed"])
        ),
        partition=DatasetPartition(str(data["partition"])),
        case_count=int(data["case_count"]),
        created_at_utc=str(data["created_at_utc"]),
        description=str(data["description"]),
        controlled_mix=bool(data.get("controlled_mix", False)),
        controlled_mix_label=(
            None
            if data.get("controlled_mix_label") is None
            else str(data["controlled_mix_label"])
        ),
    )


def ensure_near_duplicate_keys(
    cases: Iterable[DatasetCase],
) -> tuple[DatasetCase, ...]:
    """Fill missing near_duplicate_key fields from case contents."""

    filled: list[DatasetCase] = []
    for case in cases:
        key = case.near_duplicate_key or near_duplicate_key(
            case.original_source,
            case.candidate_source,
            case.transformation_category,
            case.semantic_mode,
            case.bit_width,
        )
        if case.near_duplicate_key == key:
            filled.append(case)
        else:
            filled.append(
                DatasetCase(
                    case_id=case.case_id,
                    original_source=case.original_source,
                    candidate_source=case.candidate_source,
                    semantic_mode=case.semantic_mode,
                    bit_width=case.bit_width,
                    transformation_category=case.transformation_category,
                    expected_outcome=case.expected_outcome,
                    complexity=case.complexity,
                    inclusion_reason=case.inclusion_reason,
                    exclusion_reason=case.exclusion_reason,
                    near_duplicate_key=key,
                    notes=case.notes,
                    labels=case.labels,
                )
            )
    return tuple(filled)


def find_duplicate_keys_within(
    cases: Iterable[DatasetCase],
) -> dict[str, list[str]]:
    """Return near-duplicate keys that appear more than once inside a partition."""

    buckets: dict[str, list[str]] = {}
    for case in ensure_near_duplicate_keys(cases):
        assert case.near_duplicate_key is not None
        buckets.setdefault(case.near_duplicate_key, []).append(case.case_id)
    return {k: ids for k, ids in buckets.items() if len(ids) > 1}


def find_cross_partition_leaks(
    development: Iterable[DatasetCase],
    held_out: Iterable[DatasetCase],
) -> list[tuple[str, str, str]]:
    """Return (key, development_case_id, held_out_case_id) leak triples.

    A leak is a shared near-duplicate key across development and held_out.
    """

    dev = ensure_near_duplicate_keys(development)
    held = ensure_near_duplicate_keys(held_out)
    dev_map: dict[str, list[str]] = {}
    for case in dev:
        assert case.near_duplicate_key is not None
        dev_map.setdefault(case.near_duplicate_key, []).append(case.case_id)
    leaks: list[tuple[str, str, str]] = []
    for case in held:
        assert case.near_duplicate_key is not None
        for dev_id in dev_map.get(case.near_duplicate_key, ()):
            leaks.append((case.near_duplicate_key, dev_id, case.case_id))
    return leaks


def assert_no_cross_partition_leakage(
    development: Iterable[DatasetCase],
    held_out: Iterable[DatasetCase],
) -> None:
    """Raise DatasetError if near-duplicates cross partitions."""

    leaks = find_cross_partition_leaks(development, held_out)
    if leaks:
        sample = "; ".join(
            f"{key} (dev={d}, held={h})" for key, d, h in leaks[:5]
        )
        raise DatasetError(
            f"near-duplicate leakage across development and held_out: {sample}"
        )


def validate_bundle(bundle: DatasetBundle) -> None:
    """Validate metadata/case consistency for one partition."""

    meta = bundle.metadata
    cases = ensure_near_duplicate_keys(bundle.cases)
    if meta.case_count != len(cases):
        raise DatasetError(
            f"metadata.case_count={meta.case_count} != len(cases)={len(cases)}"
        )
    ids = [c.case_id for c in cases]
    if len(ids) != len(set(ids)):
        raise DatasetError("duplicate case_id values within partition")
    if meta.controlled_mix and not meta.controlled_mix_label:
        raise DatasetError("controlled_mix requires controlled_mix_label")
    if meta.controlled_mix and "prevalence" in (meta.controlled_mix_label or "").lower():
        # Label may mention prevalence only to deny it; require the denial phrase.
        label = meta.controlled_mix_label or ""
        if "not" not in label.lower() or "real-world" not in label.lower():
            raise DatasetError(
                "controlled-mix label must state it is not real-world prevalence"
            )
    within = find_duplicate_keys_within(cases)
    if within:
        raise DatasetError(
            "near-duplicate keys repeated inside partition: "
            + ", ".join(sorted(within)[:5])
        )


def write_bundle(bundle: DatasetBundle, *, root: Path | None = None) -> Path:
    """Persist one partition under datasets/<partition>/."""

    validate_bundle(bundle)
    cases = ensure_near_duplicate_keys(bundle.cases)
    meta = DatasetMetadata(
        dataset_version=bundle.metadata.dataset_version,
        generation_procedure=bundle.metadata.generation_procedure,
        semantic_model=bundle.metadata.semantic_model,
        random_seed=bundle.metadata.random_seed,
        partition=bundle.metadata.partition,
        case_count=len(cases),
        created_at_utc=bundle.metadata.created_at_utc,
        description=bundle.metadata.description,
        controlled_mix=bundle.metadata.controlled_mix,
        controlled_mix_label=bundle.metadata.controlled_mix_label,
    )
    out_dir = partition_dir(meta.partition, root=root)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / METADATA_FILENAME).write_text(
        json.dumps(metadata_to_dict(meta), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [json.dumps(case_to_dict(c), sort_keys=True) for c in cases]
    (out_dir / CASES_FILENAME).write_text(
        ("\n".join(lines) + ("\n" if lines else "")),
        encoding="utf-8",
    )
    return out_dir


def load_bundle(
    partition: DatasetPartition, *, root: Path | None = None
) -> DatasetBundle:
    """Load and validate one partition from disk."""

    part_dir = partition_dir(partition, root=root)
    meta_path = part_dir / METADATA_FILENAME
    cases_path = part_dir / CASES_FILENAME
    if not meta_path.is_file():
        raise DatasetError(f"missing metadata: {meta_path}")
    if not cases_path.is_file():
        raise DatasetError(f"missing cases: {cases_path}")
    meta = metadata_from_dict(json.loads(meta_path.read_text(encoding="utf-8")))
    if meta.partition is not partition:
        raise DatasetError(
            f"metadata.partition={meta.partition.value} does not match "
            f"requested {partition.value}"
        )
    cases: list[DatasetCase] = []
    for line_no, line in enumerate(
        cases_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            cases.append(case_from_dict(json.loads(line)))
        except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise DatasetError(
                f"invalid case on line {line_no} of {cases_path}: {exc}"
            ) from exc
    bundle = DatasetBundle(metadata=meta, cases=tuple(cases))
    validate_bundle(bundle)
    return bundle


def load_all_partitions(*, root: Path | None = None) -> dict[DatasetPartition, DatasetBundle]:
    """Load development and held_out and assert no cross-partition leakage."""

    development = load_bundle(DatasetPartition.DEVELOPMENT, root=root)
    held_out = load_bundle(DatasetPartition.HELD_OUT, root=root)
    assert_no_cross_partition_leakage(development.cases, held_out.cases)
    return {
        DatasetPartition.DEVELOPMENT: development,
        DatasetPartition.HELD_OUT: held_out,
    }


def build_case(
    *,
    case_id: str,
    original_source: str,
    candidate_source: str | None,
    config: SemanticConfiguration,
    transformation_category: TransformationCategory,
    expected_outcome: ExpectedOutcome,
    inclusion_reason: str,
    exclusion_reason: str | None = None,
    notes: str | None = None,
    labels: Mapping[str, str] | None = None,
    parse_for_complexity: bool = True,
) -> DatasetCase:
    """Construct a DatasetCase, optionally deriving complexity via the parser."""

    expression: Expression | None = None
    failed = False
    if parse_for_complexity and expected_outcome not in (
        ExpectedOutcome.PARSE_REJECT,
        ExpectedOutcome.UNSUPPORTED,
    ):
        try:
            expression = parse_expression(original_source, config)
        except Exception:
            failed = True
    else:
        failed = True
    complexity = compute_complexity(
        expression, source=original_source, failed_parse=failed
    )
    bit_width = (
        None if config.mode is SemanticMode.MODE_A else config.bit_width
    )
    key = near_duplicate_key(
        original_source,
        candidate_source,
        transformation_category,
        config.mode,
        bit_width,
    )
    return DatasetCase(
        case_id=case_id,
        original_source=original_source,
        candidate_source=candidate_source,
        semantic_mode=config.mode,
        bit_width=bit_width,
        transformation_category=transformation_category,
        expected_outcome=expected_outcome,
        complexity=complexity,
        inclusion_reason=inclusion_reason,
        exclusion_reason=exclusion_reason,
        near_duplicate_key=key,
        notes=notes,
        labels=dict(labels or {}),
    )


def artificial_90_10_mix() -> ControlledMixConfiguration:
    """Return the §9.4 controlled 90/10 mix (not real-world prevalence)."""

    return ARTIFICIAL_90_10_MIX


def controlled_mix_metadata_fields(
    mix: ControlledMixConfiguration | None = None,
) -> dict[str, Any]:
    """Metadata fields that label a controlled artificial mix correctly."""

    mix = mix or ARTIFICIAL_90_10_MIX
    return {
        "controlled_mix": True,
        "controlled_mix_label": mix.label,
        "correct_fraction": mix.correct_fraction,
        "incorrect_fraction": mix.incorrect_fraction,
    }
