"""Confirmatory assurance experiment.

The caller must preregister ``research/EXPERIMENT_PROTOCOL.md`` before the
held-out run. This module refuses to score held-out cases unless the
protocol hash matches the preregistration file.
"""

from __future__ import annotations

import csv
import dataclasses
import hashlib
import json
import platform
import sys
from collections import Counter, defaultdict
from pathlib import Path
from time import perf_counter

from veriforge.assurance import GateResult, combine_gates, concrete_values_agree
from veriforge.benchmark_generator import (
    DATASET_VERSION,
    GENERATOR_SEED,
    GENERATOR_VERSION,
    HELD_OUT_FAMILIES,
    generate_cases,
    dataset_hash,
)
from veriforge.candidate_rules import check_proposed_rules
from veriforge.cex_localize import localize_difference, propose_constant_repair
from veriforge.config import SemanticConfiguration
from veriforge.exceptions import ParseError
from veriforge.exhaustive_oracle import exhaustive_compare
from veriforge.independent_encoder import z3_available
from veriforge.independent_evaluator import evaluate_independent, evaluate_source
from veriforge.independent_parser import (
    operator_count,
    parse_independent,
)
from veriforge.models import SemanticMode
from veriforge.polynomial_oracle import polynomial_compare
from veriforge.rule_baseline import reduce_identities, rule_only_predict
from veriforge.semantic_mutants import (
    MUTANTS,
    evaluate_mutant,
    mutant_always_confirms,
    mutant_combine_timeout_as_equivalent,
    parse_mutant,
    reference_confirms_difference,
)
from veriforge.signed_experiment import evaluate_signed
from veriforge.stats_util import bootstrap_median_interval, percentile, spearman, wilson_interval
from veriforge.testing_baseline import testing_compare
from veriforge.ui.presentation import is_labeled_equivalent
from veriforge.models import VerificationStatus
from veriforge.version import __version__

EXHAUSTIVE_BUDGET = 65536
POLY_BUDGET = 4096
TESTING_BUDGETS = (10, 100, 1000, 10000)
CATEGORY_MINIMUM = 30
BOOTSTRAP_SEED = 20261011
BOOTSTRAP_RESAMPLES = 2000


def protocol_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_preregistration(protocol_path: Path, prereg_path: Path) -> dict:
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    digest = protocol_sha256(protocol_path)
    if prereg.get("protocol_sha256") != digest:
        raise RuntimeError(
            "protocol hash does not match preregistration; refusing held-out scoring"
        )
    return prereg


def _config(case) -> SemanticConfiguration:
    mode = SemanticMode.MODE_A if case.semantic_mode == "mode_a" else SemanticMode.MODE_B
    return SemanticConfiguration(mode=mode, bit_width=case.bit_width or 32)


def label_case(case) -> dict:
    """Assign an oracle label. Construction intent is not the label."""

    config = _config(case)
    record = {
        "case_id": case.case_id,
        "family": case.family,
        "partition": case.partition,
        "category": case.category,
        "semantic_mode": case.semantic_mode,
        "bit_width": case.bit_width,
        "original_source": case.original_source,
        "candidate_source": case.candidate_source,
        "construction_intent": case.construction_intent,
        "oracle_label": None,
        "label_source": None,
        "witness": None,
        "domain_size": None,
        "assignments_evaluated": None,
        "intent_matches_oracle": None,
        "evaluator_agreement": None,
    }
    try:
        original = parse_independent(case.original_source, config)
        candidate = parse_independent(case.candidate_source, config)
    except ParseError as exc:
        kind = "unsupported" if exc.__class__.__name__ == "UnsupportedSyntaxError" else "invalid_input"
        record["oracle_label"] = kind
        record["label_source"] = "independent_parser"
        record["detail"] = str(exc)
        record["intent_matches_oracle"] = case.construction_intent in {
            "unsupported",
            "invalid_input",
            "invalid_in_mode_b",
        }
        return record

    agreement, _prod, _indy, detail = concrete_values_agree(
        case.original_source,
        {name: 0 for name in original.variables},
        config,
    )
    record["evaluator_agreement"] = agreement
    record["evaluator_detail"] = detail

    if config.mode is SemanticMode.MODE_A:
        compared = polynomial_compare(
            original.root, candidate.root, term_budget=POLY_BUDGET
        )
        record["label_source"] = "polynomial_identity"
        record["oracle_label"] = {
            "equivalent": "equivalent",
            "counterexample": "non_equivalent",
            "not_computed": "not_computed",
        }[compared.verdict]
        record["witness"] = compared.witness
        record["detail"] = compared.detail
    else:
        exhaustive = exhaustive_compare(
            original.root,
            candidate.root,
            config,
            assignment_budget=EXHAUSTIVE_BUDGET,
        )
        record["label_source"] = "exhaustive" if exhaustive.verdict != "not_computed" else "not_computed"
        record["domain_size"] = exhaustive.domain_size
        record["assignments_evaluated"] = exhaustive.assignments_evaluated
        record["oracle_label"] = {
            "equivalent": "equivalent",
            "counterexample": "non_equivalent",
            "not_computed": "not_computed",
            "not_applicable": "not_computed",
        }[exhaustive.verdict]
        record["witness"] = exhaustive.witness
        record["detail"] = exhaustive.detail
        if exhaustive.verdict == "counterexample":
            record["original_value"] = exhaustive.original_value
            record["candidate_value"] = exhaustive.candidate_value

    intent = case.construction_intent
    label = record["oracle_label"]
    if intent in {"equivalent", "equivalent_in_mode_a"}:
        record["intent_matches_oracle"] = label == "equivalent"
    elif intent == "non_equivalent":
        record["intent_matches_oracle"] = label == "non_equivalent"
    elif intent == "mode_dependent":
        record["intent_matches_oracle"] = label in {"equivalent", "non_equivalent"}
    elif intent == "invalid_in_mode_b":
        record["intent_matches_oracle"] = label == "invalid_input"
    else:
        record["intent_matches_oracle"] = label == intent
    if label == "not_computed":
        record["intent_matches_oracle"] = False
    return record


def _pipeline_status(record: dict) -> str:
    """Status of the audited pipeline from the oracle gates, without SMT."""

    gates = [
        GateResult(name="production_smt", verdict="unavailable", detail="z3 not installed"),
        GateResult(
            name="independent_encoder",
            verdict="unavailable",
            detail="z3 not installed",
        ),
    ]
    if record["oracle_label"] in {"unsupported", "invalid_input"}:
        gates.append(
            GateResult(
                name="independent_parser",
                verdict="unsupported" if record["oracle_label"] == "unsupported" else "invalid_input",
                detail=record.get("detail", ""),
            )
        )
    elif record["label_source"] == "polynomial_identity":
        verdict = "equivalent" if record["oracle_label"] == "equivalent" else (
            "counterexample" if record["oracle_label"] == "non_equivalent" else "not_computed"
        )
        gates.append(
            GateResult(
                name="polynomial",
                verdict=verdict,
                detail=record.get("detail", ""),
                witness=record.get("witness"),
            )
        )
        gates.append(GateResult(name="exhaustive", verdict="not_applicable", detail="mode A"))
    elif record["label_source"] == "exhaustive":
        verdict = "equivalent" if record["oracle_label"] == "equivalent" else "counterexample"
        gates.append(GateResult(name="polynomial", verdict="not_applicable", detail="mode B"))
        gates.append(
            GateResult(
                name="exhaustive",
                verdict=verdict,
                detail=record.get("detail", ""),
                witness=record.get("witness"),
                domain_size=record.get("domain_size"),
                assignments_evaluated=record.get("assignments_evaluated"),
            )
        )
    else:
        gates.append(GateResult(name="exhaustive", verdict="not_computed", detail=record.get("detail", "")))
    status, method, reason = combine_gates(gates)
    if is_labeled_equivalent(status) and status is not VerificationStatus.EQUIVALENT_WITHIN_MODEL:
        raise RuntimeError("equivalence label contract failed")
    return status.value, method, reason


def run_testing(record: dict, budget: int) -> dict:
    config = SemanticConfiguration(
        mode=SemanticMode.MODE_A if record["semantic_mode"] == "mode_a" else SemanticMode.MODE_B,
        bit_width=record["bit_width"] or 32,
    )
    try:
        original = parse_independent(record["original_source"], config)
        candidate = parse_independent(record["candidate_source"], config)
    except ParseError:
        return {
            "budget": budget,
            "distinguished": None,
            "evaluated": 0,
            "elapsed_seconds": 0.0,
            "detail": "parse failure",
        }
    index = int(record["case_id"].rsplit("-", 1)[1])
    seed = GENERATOR_SEED + index * 10 + budget
    result = testing_compare(
        original.root,
        candidate.root,
        config,
        budget=budget,
        seed=seed,
    )
    return {
        "budget": budget,
        "distinguished": result.distinguished,
        "evaluated": result.evaluated,
        "elapsed_seconds": result.elapsed_seconds,
        "witness": result.witness,
        "detail": result.detail,
    }


def run_mutants() -> list[dict]:
    """Score the preregistered mutants on fixed fixtures."""

    cfg_a = SemanticConfiguration(mode=SemanticMode.MODE_A)
    cfg_b = SemanticConfiguration(mode=SemanticMode.MODE_B, bit_width=8)
    outcomes = []
    checks = {
        "m01_add_as_sub": lambda: evaluate_mutant(
            "m01_add_as_sub", parse_independent("(x + y)", cfg_a).root, {"x": 3, "y": 4}, cfg_a
        )
        != evaluate_source("(x + y)", {"x": 3, "y": 4}, cfg_a),
        "m02_mul_without_wrap": lambda: evaluate_mutant(
            "m02_mul_without_wrap",
            parse_independent("(x * y)", cfg_b).root,
            {"x": 16, "y": 16},
            cfg_b,
        )
        != evaluate_source("(x * y)", {"x": 16, "y": 16}, cfg_b),
        "m03_unsigned_as_signed": lambda: evaluate_mutant(
            "m03_unsigned_as_signed", parse_independent("255", cfg_b).root, {}, cfg_b
        )
        < 0,
        "m04_unary_minus_dropped": lambda: evaluate_mutant(
            "m04_unary_minus_dropped", parse_independent("(-x)", cfg_a).root, {"x": 5}, cfg_a
        )
        != evaluate_source("(-x)", {"x": 5}, cfg_a),
        "m05_unary_minus_no_wrap": lambda: evaluate_mutant(
            "m05_unary_minus_no_wrap", parse_independent("(-x)", cfg_b).root, {"x": 1}, cfg_b
        )
        < 0,
        "m06_div_accepted_as_mul": lambda: (
            parse_mutant("m06_div_accepted_as_mul", "(x / y)", cfg_a) is not None
            and _parse_rejected("(x / y)", cfg_a)
        ),
        "m07_timeout_as_equivalent": lambda: (
            mutant_combine_timeout_as_equivalent() is VerificationStatus.EQUIVALENT_WITHIN_MODEL
            and combine_gates(
                [GateResult(name="production_smt", verdict="timeout", detail="t")]
            )[0]
            is VerificationStatus.TIMEOUT
        ),
        "m08_validator_always_confirms": lambda: (
            mutant_always_confirms(1, 1) and not reference_confirms_difference(1, 1)
        ),
        "m09_div_accepted_as_add": lambda: (
            parse_mutant("m09_div_accepted_as_add", "(x / y)", cfg_a) is not None
            and _parse_rejected("(x / y)", cfg_a)
        ),
        "m10_mul_zero_to_one": lambda: evaluate_mutant(
            "m10_mul_zero_to_one", parse_independent("(x * 0)", cfg_a).root, {"x": 9}, cfg_a
        )
        == 1
        and evaluate_source("(x * 0)", {"x": 9}, cfg_a) == 0,
    }
    for spec in MUTANTS:
        detected = bool(checks[spec.mutant_id]())
        outcomes.append(
            {
                "mutant_id": spec.mutant_id,
                "defect": spec.defect,
                "why_realistic": spec.why_realistic,
                "expected_detector": spec.expected_detector,
                "semantic_effect": "confirmed_difference" if detected else "not_observed",
                "detected": detected,
                "survived": not detected,
            }
        )
    return outcomes


def _parse_rejected(source: str, config: SemanticConfiguration) -> bool:
    try:
        parse_independent(source, config)
    except ParseError:
        return True
    return False


def run_scaling() -> dict:
    """Execution-time scaling. Solver time is not measured."""

    widths = (8, 16, 32, 64)
    depths = (1, 2, 4, 8)
    var_counts = (1, 2, 3)
    rows = []
    for width in widths:
        config = SemanticConfiguration(mode=SemanticMode.MODE_B, bit_width=width)
        for nvars in var_counts:
            names = [chr(ord("a") + index) for index in range(nvars)]
            for depth in depths:
                source = names[0]
                for level in range(depth):
                    source = f"({source} + {names[level % nvars]})"
                parsed = parse_independent(source, config)
                assignment = {name: 1 for name in names}
                for _ in range(3):
                    evaluate_independent(parsed, assignment, config)
                samples = []
                for _ in range(30):
                    started = perf_counter()
                    evaluate_independent(parsed, assignment, config)
                    samples.append(perf_counter() - started)
                median = percentile(samples, 0.5)
                rows.append(
                    {
                        "width": width,
                        "depth": depth,
                        "variable_count": nvars,
                        "operator_count": operator_count(parsed.root),
                        "trials": 30,
                        "warmup": 3,
                        "median_seconds": median,
                        "p95_seconds": percentile(samples, 0.95),
                        "samples": samples,
                    }
                )
    rho = spearman(
        [row["operator_count"] for row in rows],
        [row["median_seconds"] for row in rows],
    )
    interval = bootstrap_median_interval(
        [row["median_seconds"] for row in rows],
        seed=BOOTSTRAP_SEED,
        resamples=BOOTSTRAP_RESAMPLES,
    )
    return {
        "solver_time": "unavailable",
        "solver_reason": "z3-solver is not installed",
        "execution_rows": [{key: value for key, value in row.items() if key != "samples"} for row in rows],
        "spearman_operator_count_vs_median_execution": rho,
        "bootstrap_of_configuration_medians": interval,
        "h3_historical": "unresolved_solver_time_unavailable",
        "h3_exec_rule": "supported if Spearman rho > 0, else not supported; undefined rho is inconclusive",
    }


def run_size_reduction() -> dict:
    """Operator-count change under the four identity rules. Not execution speed."""

    config = SemanticConfiguration(mode=SemanticMode.MODE_A)
    sources = ["(x + 0)", "(y - 0)", "(z * 1)", "(a * 0)", "(((x + 0) * 1) - 0)"]
    rows = []
    for source in sources:
        before = parse_independent(source, config)
        reduced = reduce_identities(source, config)
        after = parse_independent(reduced, config)
        rows.append(
            {
                "source": source,
                "reduced": reduced,
                "operators_before": operator_count(before.root),
                "operators_after": operator_count(after.root),
                "source_length_before": len(source),
                "source_length_after": len(reduced),
            }
        )
    return {"rows": rows, "execution_speed_claim": False}


def localization_summary(records: list[dict]) -> dict:
    proposed = 0
    verified = 0
    localized = 0
    applicable = 0
    for record in records:
        if record["partition"] != "held_out" or record["oracle_label"] != "non_equivalent":
            continue
        if not record.get("witness"):
            continue
        applicable += 1
        config = SemanticConfiguration(
            mode=SemanticMode.MODE_A if record["semantic_mode"] == "mode_a" else SemanticMode.MODE_B,
            bit_width=record["bit_width"] or 32,
        )
        original = parse_independent(record["original_source"], config)
        candidate = parse_independent(record["candidate_source"], config)
        found = localize_difference(original.root, candidate.root, record["witness"], config)
        if found is None:
            continue
        left_value = evaluate_independent(found[0], record["witness"], config)
        right_value = evaluate_independent(found[1], record["witness"], config)
        if left_value != right_value:
            localized += 1
        repair = propose_constant_repair(original.root, candidate.root, record["witness"], config)
        if repair is None:
            continue
        proposed += 1
        repaired_label = _label_nodes(original.root, repair, config)
        if repaired_label == "equivalent":
            verified += 1
    return {
        "held_out_non_equivalent_with_witness": applicable,
        "localized_difference": localized,
        "constant_repairs_proposed": proposed,
        "constant_repairs_verified": verified,
        "localization_wilson": _wilson_pair(localized, applicable),
        "repair_wilson": _wilson_pair(verified, proposed),
        "claim_level": "engineering",
    }


def _label_nodes(original, candidate, config: SemanticConfiguration) -> str:
    if config.mode is SemanticMode.MODE_A:
        return polynomial_compare(original, candidate).verdict
    result = exhaustive_compare(original, candidate, config, assignment_budget=EXHAUSTIVE_BUDGET)
    return result.verdict


def _wilson_pair(successes: int, trials: int) -> dict:
    interval = wilson_interval(successes, trials)
    return {
        "successes": successes,
        "trials": trials,
        "rate": None if trials == 0 else successes / trials,
        "wilson95": None if interval is None else {"low": interval[0], "high": interval[1]},
    }


def confusion(records: list[dict], predictions: dict[str, str]) -> dict:
    """predictions map case_id to equivalent / non_equivalent / not_handled / unavailable."""

    labeled = [
        record
        for record in records
        if record["oracle_label"] in {"equivalent", "non_equivalent"}
    ]
    tp = fp = tn = fn = abstain = 0
    for record in labeled:
        predicted = predictions.get(record["case_id"], "unavailable")
        actual_eq = record["oracle_label"] == "equivalent"
        if predicted == "equivalent" and actual_eq:
            tp += 1
        elif predicted == "equivalent" and not actual_eq:
            fp += 1
        elif predicted == "non_equivalent" and not actual_eq:
            tn += 1
        elif predicted == "non_equivalent" and actual_eq:
            fn += 1
        else:
            abstain += 1
    decided = tp + fp + tn + fn
    return {
        "labeled_cases": len(labeled),
        "true_accept_equivalent": tp,
        "false_accept_non_equivalent": fp,
        "true_reject_non_equivalent": tn,
        "false_reject_equivalent": fn,
        "abstain_or_unavailable": abstain,
        "false_accept_rate": _wilson_pair(fp, fp + tn),
        "false_reject_rate": _wilson_pair(fn, fn + tp),
        "decided": decided,
    }


def testing_summary(records: list[dict], testing_rows: list[dict]) -> dict:
    by_budget = defaultdict(list)
    for row in testing_rows:
        by_budget[row["budget"]].append(row)
    summaries = {}
    held_out_non_eq = {
        record["case_id"]
        for record in records
        if record["partition"] == "held_out" and record["oracle_label"] == "non_equivalent"
    }
    held_out_eq = {
        record["case_id"]
        for record in records
        if record["partition"] == "held_out" and record["oracle_label"] == "equivalent"
    }
    for budget, rows in by_budget.items():
        misses = 0
        tested_bugs = 0
        false_diff = 0
        tested_eq = 0
        elapsed = 0.0
        missed_ids = []
        for row in rows:
            if row["distinguished"] is None:
                continue
            elapsed += row["elapsed_seconds"]
            if row["case_id"] in held_out_non_eq:
                tested_bugs += 1
                if not row["distinguished"]:
                    misses += 1
                    missed_ids.append(row["case_id"])
            if row["case_id"] in held_out_eq:
                tested_eq += 1
                if row["distinguished"]:
                    false_diff += 1
        summaries[str(budget)] = {
            "false_equivalence_misses": misses,
            "non_equivalent_tested": tested_bugs,
            "false_equivalence_rate": _wilson_pair(misses, tested_bugs),
            "false_differences_on_equivalent": false_diff,
            "equivalent_tested": tested_eq,
            "false_difference_rate": _wilson_pair(false_diff, tested_eq),
            "wall_clock_seconds": elapsed,
            "missed_case_ids": missed_ids,
        }
    rate_10 = summaries.get("10", {}).get("false_equivalence_rate", {})
    rate_10000 = summaries.get("10000", {}).get("false_equivalence_rate", {})
    n_10 = rate_10.get("trials") or 0
    n_10000 = rate_10000.get("trials") or 0
    if n_10 < CATEGORY_MINIMUM or n_10000 < CATEGORY_MINIMUM:
        decision = "inconclusive"
    elif (rate_10000.get("rate") or 0) < (rate_10.get("rate") or 0):
        decision = "supported"
    else:
        decision = "not_supported"
    return {"by_budget": summaries, "h_test_decision": decision}


def mode_trap_summary(records: list[dict]) -> list[dict]:
    """Pair each modular-collapse or literal-range source across modes."""

    grouped: dict[tuple, dict] = {}
    for record in records:
        if record["family"] not in {"modular_collapse", "literal_range"}:
            continue
        key = (record["family"], record["original_source"], record["candidate_source"], record["bit_width"])
        # Mode A stores bit_width None. Pair on sources only plus the mode B width
        # by using the source pair.
        key = (record["family"], record["original_source"], record["candidate_source"])
        slot = grouped.setdefault(
            key,
            {"family": record["family"], "original_source": record["original_source"], "candidate_source": record["candidate_source"], "modes": {}},
        )
        slot["modes"][record["semantic_mode"]] = {
            "oracle_label": record["oracle_label"],
            "bit_width": record["bit_width"],
        }
    rows = []
    for slot in grouped.values():
        mode_a = slot["modes"].get("mode_a", {}).get("oracle_label")
        mode_b = slot["modes"].get("mode_b", {}).get("oracle_label")
        rows.append(
            {
                **slot,
                "differs_across_modes": mode_a != mode_b,
            }
        )
    return rows


def category_counts(records: list[dict]) -> dict:
    counts = Counter(record["category"] for record in records)
    return {
        category: {
            "pairs": count,
            "conclusion": "reported" if count >= CATEGORY_MINIMUM else "insufficient_sample",
        }
        for category, count in sorted(counts.items())
    }


def signed_spot_checks() -> list[dict]:
    node = parse_independent("(127 + 1)", SemanticConfiguration(mode=SemanticMode.MODE_A)).root
    return [
        {
            "expression": "(127 + 1)",
            "width": 8,
            "signed_result": evaluate_signed(node, {}, 8),
            "unsigned_mode_b_result": evaluate_source(
                "(127 + 1)",
                {},
                SemanticConfiguration(mode=SemanticMode.MODE_B, bit_width=8),
            ),
            "production_mode": "not_added",
        }
    ]


def write_svg(path: Path, title: str, labels: list[str], values: list[float]) -> None:
    width = 640
    height = 360
    left = 70
    top = 40
    chart_w = 540
    chart_h = 260
    maximum = max(values) if values else 1
    if maximum <= 0:
        maximum = 1
    bars = []
    slot = chart_w / max(1, len(values))
    for index, (label, value) in enumerate(zip(labels, values)):
        bar_h = chart_h * (value / maximum)
        x = left + index * slot + 8
        y = top + chart_h - bar_h
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{slot - 16:.1f}" height="{bar_h:.1f}" fill="#2457a6"/>'
        )
        bars.append(
            f'<text x="{x + (slot - 16) / 2:.1f}" y="{top + chart_h + 20}" text-anchor="middle" font-size="12">{label}</text>'
        )
        bars.append(
            f'<text x="{x + (slot - 16) / 2:.1f}" y="{y - 6:.1f}" text-anchor="middle" font-size="11">{value:.4g}</text>'
        )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        f'<rect width="100%" height="100%" fill="white"/>'
        f'<text x="20" y="24" font-size="16">{title}</text>'
        + "".join(bars)
        + "</svg>"
    )
    path.write_text(svg, encoding="utf-8")


def execute(protocol_path: Path, prereg_path: Path, output_dir: Path) -> dict:
    prereg = verify_preregistration(protocol_path, prereg_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    raw = output_dir / "raw"
    raw.mkdir(exist_ok=True)
    plots = output_dir / "plots"
    plots.mkdir(exist_ok=True)

    cases = generate_cases()
    digest = dataset_hash(cases)
    records = []
    for index, case in enumerate(cases, start=1):
        record = label_case(case)
        status, method, reason = _pipeline_status(record)
        record["pipeline_status"] = status
        record["pipeline_method"] = method
        record["pipeline_reason"] = reason
        try:
            record["rule_baseline"] = rule_only_predict(
                case.original_source, case.candidate_source, _config(case)
            )
        except Exception as exc:  # noqa: BLE001
            record["rule_baseline"] = "not_handled"
            record["rule_baseline_error"] = str(exc)
        records.append(record)
        if index % 50 == 0:
            print(f"labeled {index}/{len(cases)}", file=sys.stderr)

    testing_rows = []
    for record in records:
        if record["partition"] != "held_out":
            continue
        if record["oracle_label"] not in {"equivalent", "non_equivalent"}:
            continue
        for budget in TESTING_BUDGETS:
            row = run_testing(record, budget)
            row["case_id"] = record["case_id"]
            row["oracle_label"] = record["oracle_label"]
            testing_rows.append(row)
    print("testing baseline complete", file=sys.stderr)

    held = [record for record in records if record["partition"] == "held_out"]
    pipeline_pred = {}
    rule_pred = {}
    for record in held:
        if record["pipeline_status"] == "equivalent_within_model":
            pipeline_pred[record["case_id"]] = "equivalent"
        elif record["pipeline_status"] == "counterexample_found":
            pipeline_pred[record["case_id"]] = "non_equivalent"
        else:
            pipeline_pred[record["case_id"]] = "not_handled"
        if record["rule_baseline"] == "equivalent":
            rule_pred[record["case_id"]] = "equivalent"
        else:
            rule_pred[record["case_id"]] = "not_handled"

    mutants = run_mutants()
    scaling = run_scaling()
    reduction = run_size_reduction()
    localization = localization_summary(records)
    rules = [dataclasses.asdict(row) for row in check_proposed_rules()]
    test_stats = testing_summary(records, testing_rows)

    # Pipeline vs oracle is partly the same oracle. Report that explicitly.
    pipeline_confusion = confusion(held, pipeline_pred)
    pipeline_confusion["circularity"] = (
        "On tractable cases the audited pipeline's establishing method is the "
        "same exhaustive or polynomial oracle that supplies the label. Agreement "
        "there is a contract check, not an independent accuracy estimate."
    )
    rule_confusion = confusion(held, rule_pred)

    disagreements = [
        {
            "case_id": record["case_id"],
            "detail": record.get("evaluator_detail"),
        }
        for record in records
        if record.get("evaluator_agreement") is False
    ]
    intent_mismatches = [
        {
            "case_id": record["case_id"],
            "partition": record["partition"],
            "family": record["family"],
            "intent": record["construction_intent"],
            "oracle_label": record["oracle_label"],
            "original_source": record["original_source"],
            "candidate_source": record["candidate_source"],
            "bit_width": record["bit_width"],
            "semantic_mode": record["semantic_mode"],
        }
        for record in records
        if record.get("intent_matches_oracle") is False
    ]

    environment = {
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "veriforge": __version__,
        "z3_available": z3_available(),
        "cvc5_available": False,
        "bitwuzla_available": False,
        "cvc5_note": "not installed; egress blocked and no local binary was found",
        "bitwuzla_note": "not installed; egress blocked and no local binary was found",
        "generator_seed": GENERATOR_SEED,
        "dataset_version": DATASET_VERSION,
        "generator_version": GENERATOR_VERSION,
        "exhaustive_budget": EXHAUSTIVE_BUDGET,
        "protocol_sha256": prereg["protocol_sha256"],
        "protocol_created_at_utc": prereg["created_at_utc"],
        "dataset_sha256": digest,
        "held_out_families": sorted(HELD_OUT_FAMILIES),
    }

    summary = {
        "environment": environment,
        "case_count": len(records),
        "partitions": dict(Counter(record["partition"] for record in records)),
        "categories": category_counts(records),
        "family_count": len({record["family"] for record in records}),
        "oracle_labels": dict(Counter(record["oracle_label"] for record in records)),
        "held_out_oracle_labels": dict(Counter(record["oracle_label"] for record in held)),
        "h_audit": {
            "decision": "inconclusive",
            "reason": "production Z3 verifier and the second Z3 encoder were unavailable because z3-solver could not be installed",
        },
        "h_test": test_stats,
        "pipeline_vs_oracle_held_out": pipeline_confusion,
        "rule_baseline_held_out": rule_confusion,
        "production_smt": "unavailable",
        "independent_encoder": "unavailable",
        "external_solver": "unavailable",
        "mutants": {
            "detected": sum(1 for row in mutants if row["detected"]),
            "survived": sum(1 for row in mutants if row["survived"]),
            "denominator": len(mutants),
            "rows": mutants,
        },
        "scaling": scaling,
        "size_reduction": reduction,
        "localization": localization,
        "proposed_rules": rules,
        "signed_spot_checks": signed_spot_checks(),
        "evaluator_disagreements": disagreements,
        "intent_mismatches": intent_mismatches,
        "mode_traps": mode_trap_summary(records),
        "smt_versus_testing": "not_computed_solver_unavailable",
    }

    (raw / "cases.jsonl").write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    with (raw / "testing_baseline.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "oracle_label",
                "budget",
                "distinguished",
                "evaluated",
                "elapsed_seconds",
                "detail",
            ],
        )
        writer.writeheader()
        for row in testing_rows:
            writer.writerow({key: row.get(key) for key in writer.fieldnames})
    (raw / "environment.json").write_text(
        json.dumps(environment, indent=2, sort_keys=True), encoding="utf-8"
    )
    manifest = {
        "dataset_version": DATASET_VERSION,
        "generator_version": GENERATOR_VERSION,
        "generator_seed": GENERATOR_SEED,
        "dataset_sha256": digest,
        "case_count": len(cases),
        "held_out_families": sorted(HELD_OUT_FAMILIES),
        "exhaustive_budget": EXHAUSTIVE_BUDGET,
        "historical_held_out_preserved": "datasets/held_out",
    }
    manifest_path = Path("datasets/assurance_v1")
    manifest_path.mkdir(parents=True, exist_ok=True)
    (manifest_path / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    (manifest_path / "cases.jsonl").write_text(
        "".join(
            json.dumps(case.fingerprint_row(), sort_keys=True) + "\n" for case in cases
        ),
        encoding="utf-8",
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    budgets = [10, 100, 1000, 10000]
    rates = []
    for budget in budgets:
        rate = test_stats["by_budget"][str(budget)]["false_equivalence_rate"]["rate"]
        rates.append(0.0 if rate is None else rate)
    write_svg(
        plots / "testing-false-equivalence.svg",
        "Held-out false-equivalence rate by testing budget",
        [str(budget) for budget in budgets],
        rates,
    )
    medians = [row["median_seconds"] for row in scaling["execution_rows"]]
    write_svg(
        plots / "execution-time-medians.svg",
        "Median evaluator time by scaling configuration index",
        [str(index) for index in range(0, len(medians), max(1, len(medians) // 8))],
        [medians[index] for index in range(0, len(medians), max(1, len(medians) // 8))],
    )
    return summary
