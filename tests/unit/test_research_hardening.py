"""Unit tests for the research-hardening semantic path. No pytest required."""

from __future__ import annotations

import unittest

from veriforge.assurance import GateResult, audit_equivalence, combine_gates
from veriforge.benchmark_generator import (
    GENERATOR_SEED,
    generate_cases,
    partition_for,
)
from veriforge.cex_localize import localize_difference
from veriforge.config import SemanticConfiguration
from veriforge.exceptions import InvalidLiteralError, UnsupportedSyntaxError
from veriforge.exhaustive_oracle import domain_size, exhaustive_compare
from veriforge.independent_evaluator import evaluate_source, unsigned_wrap
from veriforge.independent_parser import parse_independent, render_independent
from veriforge.models import SemanticMode, VerificationStatus
from veriforge.polynomial_oracle import polynomial_compare
from veriforge.semantic_mutants import (
    MUTANTS,
    evaluate_mutant,
    mutant_always_confirms,
    mutant_combine_timeout_as_equivalent,
    parse_mutant,
    reference_confirms_difference,
)
from veriforge.signed_experiment import evaluate_signed, signed_wrap
from veriforge.stats_util import spearman, wilson_interval
from veriforge.testing_baseline import testing_compare


def mode_a() -> SemanticConfiguration:
    return SemanticConfiguration(mode=SemanticMode.MODE_A)


def mode_b(width: int) -> SemanticConfiguration:
    return SemanticConfiguration(mode=SemanticMode.MODE_B, bit_width=width)


class ParserTests(unittest.TestCase):
    def test_precedence_and_unary(self) -> None:
        parsed = parse_independent("1+2*3", mode_a())
        self.assertEqual(evaluate_source("1+2*3", {}, mode_a()), 7)
        self.assertEqual(render_independent(parsed.root), "(1+(2*3))")
        self.assertEqual(evaluate_source("--x", {"x": 4}, mode_a()), 4)
        self.assertEqual(evaluate_source("x+-1", {"x": 3}, mode_a()), 2)

    def test_literals_and_rejections(self) -> None:
        self.assertEqual(parse_independent("0x10", mode_a()).root.value, 16)
        self.assertEqual(parse_independent("0b1010", mode_a()).root.value, 10)
        self.assertEqual(parse_independent("1_000", mode_a()).root.value, 1000)
        self.assertEqual(parse_independent("00", mode_a()).root.value, 0)
        with self.assertRaises(UnsupportedSyntaxError):
            parse_independent("01", mode_a())
        with self.assertRaises(InvalidLiteralError):
            parse_independent("True", mode_a())
        with self.assertRaises(UnsupportedSyntaxError):
            parse_independent("x / y", mode_a())
        with self.assertRaises(InvalidLiteralError):
            parse_independent("256", mode_b(8))

    def test_unsigned_not_signed(self) -> None:
        self.assertEqual(unsigned_wrap(-1, 8), 255)
        self.assertEqual(evaluate_source("-1", {}, mode_b(8)), 255)
        self.assertEqual(evaluate_source("(x + 255)", {"x": 1}, mode_b(8)), 0)
        self.assertEqual(evaluate_source("(16 * 16)", {}, mode_b(8)), 0)
        self.assertNotEqual(evaluate_source("-1", {}, mode_a()), 255)


class OracleTests(unittest.TestCase):
    def test_polynomial_identity_and_witness(self) -> None:
        left = parse_independent("(x + 0)", mode_a())
        right = parse_independent("x", mode_a())
        same = polynomial_compare(left.root, right.root)
        self.assertEqual(same.verdict, "equivalent")
        bad_l = parse_independent("(x + 1)", mode_a())
        bad_r = parse_independent("(x + 2)", mode_a())
        diff = polynomial_compare(bad_l.root, bad_r.root)
        self.assertEqual(diff.verdict, "counterexample")
        self.assertIsNotNone(diff.witness)
        assert diff.witness is not None
        self.assertNotEqual(
            evaluate_source("(x + 1)", diff.witness, mode_a()),
            evaluate_source("(x + 2)", diff.witness, mode_a()),
        )

    def test_exhaustive_budget(self) -> None:
        self.assertEqual(domain_size(4, 2), 256)
        left = parse_independent("(x + x)", mode_b(2))
        right = parse_independent("(x * 2)", mode_b(2))
        result = exhaustive_compare(left.root, right.root, mode_b(2), assignment_budget=16)
        self.assertEqual(result.verdict, "equivalent")
        self.assertEqual(result.assignments_evaluated, 4)
        too_big = exhaustive_compare(left.root, right.root, mode_b(8), assignment_budget=16)
        self.assertEqual(too_big.verdict, "not_computed")
        self.assertEqual(too_big.assignments_evaluated, 0)
        trap_l = parse_independent("(x + 255)", mode_b(8))
        trap_r = parse_independent("(x - 1)", mode_b(8))
        trap = exhaustive_compare(trap_l.root, trap_r.root, mode_b(8), assignment_budget=256)
        self.assertEqual(trap.verdict, "equivalent")
        mode_a_skip = exhaustive_compare(trap_l.root, trap_r.root, mode_a(), assignment_budget=256)
        self.assertEqual(mode_a_skip.verdict, "not_applicable")


class ContractTests(unittest.TestCase):
    def test_timeout_is_not_equivalence(self) -> None:
        status, method, _reason = combine_gates(
            [GateResult(name="production_smt", verdict="timeout", detail="timed out")]
        )
        self.assertIs(status, VerificationStatus.TIMEOUT)
        self.assertNotEqual(method, "production_smt")
        self.assertIsNot(status, VerificationStatus.EQUIVALENT_WITHIN_MODEL)

    def test_disagreement_blocks_equivalence(self) -> None:
        status, _method, _reason = combine_gates(
            [
                GateResult(name="production_smt", verdict="equivalent", detail="unsat"),
                GateResult(
                    name="exhaustive",
                    verdict="counterexample",
                    detail="differ",
                    witness={"x": 1},
                ),
            ]
        )
        self.assertIs(status, VerificationStatus.SEMANTIC_DISAGREEMENT)

    def test_unavailable_does_not_prove_equivalence(self) -> None:
        status, _method, _reason = combine_gates(
            [GateResult(name="production_smt", verdict="unavailable", detail="no z3")]
        )
        self.assertIs(status, VerificationStatus.UNKNOWN)

    def test_missing_solver_does_not_veto_polynomial_proof(self) -> None:
        report = audit_equivalence("(x + 0)", "x", mode_a(), run_smt=True)
        self.assertIs(report.status, VerificationStatus.EQUIVALENT_WITHIN_MODEL)
        self.assertIn("polynomial", report.establishing_method)
        self.assertFalse(report.smt_available)

    def test_exhaustive_can_establish_mode_b(self) -> None:
        status, method, _reason = combine_gates(
            [
                GateResult(name="production_smt", verdict="unavailable", detail="no z3"),
                GateResult(name="exhaustive", verdict="equivalent", detail="full domain"),
            ]
        )
        self.assertIs(status, VerificationStatus.EQUIVALENT_WITHIN_MODEL)
        self.assertEqual(method, "exhaustive")


class MutantTests(unittest.TestCase):
    def test_each_mutant_is_detected_on_its_fixture(self) -> None:
        cfg_a = mode_a()
        cfg_b = mode_b(8)
        node_add = parse_independent("(x + y)", cfg_a).root
        self.assertNotEqual(
            evaluate_mutant("m01_add_as_sub", node_add, {"x": 3, "y": 4}, cfg_a),
            evaluate_source("(x + y)", {"x": 3, "y": 4}, cfg_a),
        )
        node_mul = parse_independent("(x * y)", cfg_b).root
        self.assertNotEqual(
            evaluate_mutant("m02_mul_without_wrap", node_mul, {"x": 16, "y": 16}, cfg_b),
            evaluate_source("(x * y)", {"x": 16, "y": 16}, cfg_b),
        )
        self.assertLess(
            evaluate_mutant("m03_unsigned_as_signed", parse_independent("255", cfg_b).root, {}, cfg_b),
            0,
        )
        self.assertNotEqual(
            evaluate_mutant("m04_unary_minus_dropped", parse_independent("(-x)", cfg_a).root, {"x": 5}, cfg_a),
            evaluate_source("(-x)", {"x": 5}, cfg_a),
        )
        self.assertLess(
            evaluate_mutant("m05_unary_minus_no_wrap", parse_independent("(-x)", cfg_b).root, {"x": 1}, cfg_b),
            0,
        )
        parsed = parse_mutant("m06_div_accepted_as_mul", "(x / y)", cfg_a)
        self.assertEqual(evaluate_source(render_independent(parsed.root), {"x": 3, "y": 4}, cfg_a), 12)
        with self.assertRaises(UnsupportedSyntaxError):
            parse_independent("(x / y)", cfg_a)
        self.assertIs(
            mutant_combine_timeout_as_equivalent(),
            VerificationStatus.EQUIVALENT_WITHIN_MODEL,
        )
        self.assertIs(
            combine_gates(
                [GateResult(name="production_smt", verdict="timeout", detail="t")]
            )[0],
            VerificationStatus.TIMEOUT,
        )
        self.assertTrue(mutant_always_confirms(1, 1))
        self.assertFalse(reference_confirms_difference(1, 1))
        parsed_add = parse_mutant("m09_div_accepted_as_add", "(x / y)", cfg_a)
        self.assertEqual(
            evaluate_source(render_independent(parsed_add.root), {"x": 3, "y": 4}, cfg_a),
            7,
        )
        self.assertEqual(
            evaluate_mutant("m10_mul_zero_to_one", parse_independent("(x * 0)", cfg_a).root, {"x": 9}, cfg_a),
            1,
        )
        self.assertEqual(len(MUTANTS), 10)


class BenchmarkAndStatsTests(unittest.TestCase):
    def test_partition_and_determinism(self) -> None:
        self.assertEqual(partition_for("distributivity"), "held_out")
        self.assertEqual(partition_for("add_zero"), "development")
        first = generate_cases()
        second = generate_cases()
        self.assertEqual([case.case_id for case in first], [case.case_id for case in second])
        self.assertGreaterEqual(len(first), 300)
        self.assertGreaterEqual(len({case.family for case in first}), 20)
        self.assertEqual(GENERATOR_SEED, 20261011)

    def test_wilson_and_spearman(self) -> None:
        interval = wilson_interval(0, 10)
        self.assertIsNotNone(interval)
        assert interval is not None
        self.assertEqual(interval[0], 0.0)
        self.assertGreater(interval[1], 0.0)
        self.assertLess(interval[1], 1.0)
        self.assertIsNone(wilson_interval(0, 0))
        self.assertAlmostEqual(spearman([1, 2, 3], [2, 4, 6]) or 0.0, 1.0)

    def test_testing_finds_off_by_one(self) -> None:
        left = parse_independent("(x + 1)", mode_b(4))
        right = parse_independent("(x + 2)", mode_b(4))
        found = testing_compare(left.root, right.root, mode_b(4), budget=10, seed=1)
        self.assertTrue(found.distinguished)

    def test_signed_is_separate(self) -> None:
        self.assertEqual(signed_wrap(128, 8), -128)
        node = parse_independent("(127 + 1)", mode_a()).root
        self.assertEqual(evaluate_signed(node, {}, 8), -128)
        self.assertEqual(evaluate_source("(127 + 1)", {}, mode_b(8)), 128)

    def test_localize_constant(self) -> None:
        original = parse_independent("(x + 1)", mode_a())
        candidate = parse_independent("(x + 2)", mode_a())
        found = localize_difference(original.root, candidate.root, {"x": 0}, mode_a())
        self.assertIsNotNone(found)


if __name__ == "__main__":
    unittest.main()
