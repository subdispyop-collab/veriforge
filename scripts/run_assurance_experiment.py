#!/usr/bin/env python3
"""Run the preregistered assurance experiment.

Refuses to score held-out cases if the protocol hash does not match
research/protocol_preregistration.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from veriforge.assurance_experiment import execute


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--protocol",
        type=Path,
        default=Path("research/EXPERIMENT_PROTOCOL.md"),
    )
    parser.add_argument(
        "--preregistration",
        type=Path,
        default=Path("research/protocol_preregistration.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("experiments/reports/assurance-v1"),
    )
    args = parser.parse_args()
    summary = execute(args.protocol, args.preregistration, args.output)
    print(
        json.dumps(
            {
                "case_count": summary["case_count"],
                "dataset_sha256": summary["environment"]["dataset_sha256"],
                "h_audit": summary["h_audit"]["decision"],
                "h_test": summary["h_test"]["h_test_decision"],
                "mutants_detected": summary["mutants"]["detected"],
                "mutants_denominator": summary["mutants"]["denominator"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
