#!/usr/bin/env python3
"""Launch the VERIFORGE Streamlit interface on an uncommon port."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


DEFAULT_PORT = 8513


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"HTTP port (default {DEFAULT_PORT}; avoid 3000/5173/8080 when possible)",
    )
    parser.add_argument(
        "--address",
        default="127.0.0.1",
        help="Bind address (default 127.0.0.1)",
    )
    args = parser.parse_args(argv)
    app = Path(__file__).resolve().parent.parent / "veriforge" / "app.py"
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app),
        "--server.port",
        str(args.port),
        "--server.address",
        args.address,
        "--browser.gatherUsageStats",
        "false",
    ]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
