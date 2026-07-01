#!/usr/bin/env python3
"""Batch day-update runner for the local A-share history archive.

Iterates the stock universe in ``a-data/stock_list.csv`` and tops up each code's
archive to the latest trade date by delegating to
:func:`scripts.local_hist.get_hist`, which is local-first and only fetches the
missing tail (口径-safe, unadjusted). This module supplies the *runner* layer
that ``local_hist`` intentionally omits: universe iteration, rate limiting,
per-code degradation, progress, and a run summary.

Usage
-----
Update the whole universe to today::

    uv run python scripts/update_hist.py

Update only a few codes (debug / smoke)::

    uv run python scripts/update_hist.py --codes 000001,600519,300750

Common flags::

    --end-date 2026-06-30   # top up to a specific trade date (default: today)
    --limit 50              # only process the first N codes (smoke)
    --sleep 0.15            # seconds between codes (rate limit; default 0.1)
    --offline               # no network; report staleness only
    --summary-out PATH      # write a JSON run summary (default: tmp/update_hist/summary.json)

All conclusions are for research/review only, not trading instructions.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

# Make ``scripts`` importable whether run as a module or a file.
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import local_hist  # noqa: E402  (path shim above)

CODE_COL = "代码"
NAME_COL = "名称"
DEFAULT_SLEEP_SECONDS = 0.1


def _repo_root() -> Path:
    # scripts/ -> stock-analysis/
    return _SCRIPTS_DIR.parent


def load_universe(limit: int | None = None) -> list[str]:
    """Read 6-digit codes from ``a-data/stock_list.csv`` (utf-8-sig / BOM)."""
    list_path = local_hist.data_root() / "stock_list.csv"
    if not list_path.exists():
        raise FileNotFoundError(f"stock_list.csv not found at {list_path}")
    df = pd.read_csv(list_path, dtype=str, encoding="utf-8-sig")
    if CODE_COL not in df.columns:
        raise KeyError(
            f"expected column {CODE_COL!r} in stock_list.csv, got {list(df.columns)}"
        )
    codes = [local_hist.normalize_code(str(c)) for c in df[CODE_COL] if str(c).strip()]
    # De-dupe while preserving order.
    seen: set[str] = set()
    ordered = [c for c in codes if not (c in seen or seen.add(c))]
    if limit is not None:
        ordered = ordered[:limit]
    return ordered


def update_one(
    code: str,
    *,
    end_date: str | None,
    allow_network: bool,
) -> dict[str, object]:
    """Top up one code. Never raises: failures are captured in the result dict."""
    before = local_hist.local_last_date(code)
    try:
        df = local_hist.get_hist(code, end_date=end_date, allow_network=allow_network)
    except Exception as exc:  # defensive: local_hist already swallows fetch errors
        return {
            "code": code,
            "status": "error",
            "before": before,
            "after": before,
            "rows": None,
            "error": f"{type(exc).__name__}: {exc}",
        }
    after = str(df[local_hist.DATE_COL].iloc[-1]) if not df.empty else None
    if before is None and after is None:
        status = "no_data"
    elif before == after:
        status = "unchanged"
    else:
        status = "updated"
    return {
        "code": code,
        "status": status,
        "before": before,
        "after": after,
        "rows": int(len(df)),
    }


def run(
    codes: list[str],
    *,
    end_date: str | None,
    allow_network: bool,
    sleep_seconds: float,
) -> dict[str, object]:
    total = len(codes)
    results: list[dict[str, object]] = []
    counts = {"updated": 0, "unchanged": 0, "no_data": 0, "error": 0}
    started = datetime.now()

    for idx, code in enumerate(codes, start=1):
        res = update_one(code, end_date=end_date, allow_network=allow_network)
        results.append(res)
        counts[str(res["status"])] = counts.get(str(res["status"]), 0) + 1

        if idx % 100 == 0 or idx == total:
            elapsed = (datetime.now() - started).total_seconds()
            rate = idx / elapsed if elapsed else 0.0
            print(
                f"[{idx}/{total}] "
                f"updated={counts['updated']} unchanged={counts['unchanged']} "
                f"no_data={counts['no_data']} error={counts['error']} "
                f"({rate:.1f}/s)",
                flush=True,
            )
        if allow_network and sleep_seconds > 0 and idx < total:
            time.sleep(sleep_seconds)

    return {
        "generated_at": started.isoformat(timespec="seconds"),
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "end_date": end_date or datetime.now().strftime("%Y-%m-%d"),
        "universe_size": total,
        "allow_network": allow_network,
        "counts": counts,
        "results": results,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch day-update the local A-share history archive."
    )
    parser.add_argument(
        "--codes",
        help="Comma-separated 6-digit codes; default is the whole stock_list.csv universe.",
    )
    parser.add_argument(
        "--end-date",
        help="Top up to this trade date (YYYY-MM-DD); default is today.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Only process the first N codes (smoke/debug).",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=DEFAULT_SLEEP_SECONDS,
        help=f"Seconds between codes to rate-limit public endpoints (default {DEFAULT_SLEEP_SECONDS}).",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="No network; only report current staleness per code.",
    )
    parser.add_argument(
        "--summary-out",
        help="Path to write the JSON run summary (default: tmp/update_hist/summary.json).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.codes:
        codes = [local_hist.normalize_code(c) for c in args.codes.split(",") if c.strip()]
    else:
        codes = load_universe(limit=args.limit)

    if not codes:
        print("No codes to process.", file=sys.stderr)
        return 1

    print(
        f"Updating {len(codes)} codes to "
        f"{args.end_date or datetime.now().strftime('%Y-%m-%d')} "
        f"(network={'off' if args.offline else 'on'}, sleep={args.sleep}s)",
        flush=True,
    )

    summary = run(
        codes,
        end_date=args.end_date,
        allow_network=not args.offline,
        sleep_seconds=args.sleep,
    )

    out_path = Path(args.summary_out) if args.summary_out else (
        _repo_root() / "tmp" / "update_hist" / "summary.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    counts = summary["counts"]
    print(
        "Done. "
        f"updated={counts['updated']} unchanged={counts['unchanged']} "
        f"no_data={counts['no_data']} error={counts['error']}. "
        f"Summary -> {out_path}",
        flush=True,
    )
    # Non-zero exit only if literally everything failed (lets cron detect a dead source).
    if counts["error"] == summary["universe_size"] and summary["universe_size"] > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
