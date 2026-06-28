#!/usr/bin/env python3
"""Command-line entrypoint for the stock-analysis repository harness."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.runner import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
