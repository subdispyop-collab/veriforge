#!/usr/bin/env python3
"""Report the method-discovery gate. Does not score pairs."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research" / "PREREGISTRATION.md"
META = ROOT / "research" / "method_discovery_preregistration.json"


def main() -> int:
    digest = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    meta = json.loads(META.read_text(encoding="utf-8"))
    if meta.get("protocol_sha256") != digest:
        print(f"hash mismatch file={digest} recorded={meta.get('protocol_sha256')}")
        return 2
    if meta.get("gate") != "NO-GO":
        print("this script only reports the NO-GO record")
        return 2
    if meta.get("new_pairs_authorized") is not False:
        print("refusing to analyze because new pairs were authorized")
        return 2
    report = {
        "gate": "NO-GO",
        "protocol_sha256": digest,
        "primary_hypothesis": "not_tested",
        "pair_count": 0,
        "false_equivalence": None,
        "reason": "no candidate survived the gate; no confirmatory rows exist",
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
