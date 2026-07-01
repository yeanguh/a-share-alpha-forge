#!/usr/bin/env python3
"""Data-freshness gate for the selection flow: check, then backfill if stale.

Design intent (per user request A+B): the pipeline should NOT rely on a separate
scheduled day-update job. Instead, at *execution time* it checks whether the
codes it is about to use are fresh enough; if any are missing or stale, it tops
them up first (delegating to :mod:`update_hist` / :func:`local_hist.get_hist`),
then lets the caller continue with the rest of the steps.

Typical use at the top of ``run_integrated_selection`` (or any entrypoint that
consumes local history)::

    from scripts.ensure_fresh import ensure_fresh
    ...
    ensure_fresh(candidate_codes, end_date=args.date)  # backfills stale/missing

If ``candidate_codes`` is not yet known when you want the gate (e.g. you plan to
select from the whole universe), pass ``codes=None`` to check/backfill the whole
``stock_list.csv`` universe.

All conclusions are for research/review only, not trading instructions.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import local_hist  # noqa: E402
import update_hist  # noqa: E402


def _target_date(end_date: str | None) -> str:
    return end_date or datetime.now().strftime("%Y-%m-%d")


def stale_codes(
    codes: list[str],
    *,
    end_date: str | None = None,
) -> list[str]:
    """Return the subset of ``codes`` whose local archive is missing or older
    than ``end_date`` (default: today). Purely local, no network."""
    target = _target_date(end_date)
    out: list[str] = []
    for code in codes:
        norm = local_hist.normalize_code(code)
        last = local_hist.local_last_date(norm)
        if last is None or last < target:
            out.append(norm)
    return out


def ensure_fresh(
    codes: list[str] | None,
    *,
    end_date: str | None = None,
    allow_network: bool = True,
    sleep_seconds: float = update_hist.DEFAULT_SLEEP_SECONDS,
    verbose: bool = True,
) -> dict[str, object]:
    """Check freshness and backfill stale/missing codes before continuing.

    Parameters
    ----------
    codes:
        Explicit 6-digit codes to guard. If ``None``, the whole
        ``stock_list.csv`` universe is checked (heavier; use when the selection
        will scan the full market).
    end_date:
        Freshness target (YYYY-MM-DD). Default is today.
    allow_network:
        If ``False``, report staleness but do not fetch (offline gate).

    Returns a summary dict; the caller can log it and then proceed. Never raises
    on per-code fetch failure — those are captured by ``update_hist``.
    """
    target = _target_date(end_date)
    universe = (
        [local_hist.normalize_code(c) for c in codes]
        if codes is not None
        else update_hist.load_universe()
    )

    stale = stale_codes(universe, end_date=end_date)
    if not stale:
        if verbose:
            print(f"[ensure_fresh] all {len(universe)} codes fresh to {target}; skip backfill.", flush=True)
        return {
            "target_date": target,
            "checked": len(universe),
            "stale": 0,
            "backfilled": False,
            "counts": {"updated": 0, "unchanged": len(universe), "no_data": 0, "error": 0},
        }

    if verbose:
        print(
            f"[ensure_fresh] {len(stale)}/{len(universe)} codes stale/missing "
            f"(target {target}); backfilling (network={'off' if not allow_network else 'on'})...",
            flush=True,
        )

    summary = update_hist.run(
        stale,
        end_date=end_date,
        allow_network=allow_network,
        sleep_seconds=sleep_seconds,
    )

    if verbose:
        c = summary["counts"]
        print(
            f"[ensure_fresh] backfill done: updated={c['updated']} "
            f"unchanged={c['unchanged']} no_data={c['no_data']} error={c['error']}. "
            f"Continuing pipeline.",
            flush=True,
        )
    return {
        "target_date": target,
        "checked": len(universe),
        "stale": len(stale),
        "backfilled": True,
        "counts": summary["counts"],
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Check local A-share history freshness and backfill if stale."
    )
    parser.add_argument("--codes", help="Comma-separated 6-digit codes; default = whole universe.")
    parser.add_argument("--end-date", help="Freshness target YYYY-MM-DD (default: today).")
    parser.add_argument("--offline", action="store_true", help="Report staleness only; no network.")
    args = parser.parse_args()

    code_list = (
        [c for c in args.codes.split(",") if c.strip()] if args.codes else None
    )
    ensure_fresh(code_list, end_date=args.end_date, allow_network=not args.offline)
