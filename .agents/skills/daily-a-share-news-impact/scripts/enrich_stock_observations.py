#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib import error

from tencent_quote import fetch_quote


def load_bundle(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Input bundle must be a JSON object")
    stocks = payload.get("stocks", [])
    if not isinstance(stocks, list):
        raise ValueError("Input bundle field `stocks` must be a JSON array")
    return payload


def enrich_stock(stock: dict[str, Any], refresh: bool) -> tuple[dict[str, Any], str | None]:
    ticker = stock.get("ticker")
    if not isinstance(ticker, str) or not ticker.strip():
        return stock, "Skipped stock without valid `ticker`."
    if stock.get("market_cap_billion") not in {None, ""} and not refresh:
        return stock, None

    try:
        quote = fetch_quote(ticker)
    except (OSError, error.URLError, ValueError) as exc:
        return stock, f"{ticker}: Tencent quote fetch failed: {exc}"

    enriched = dict(stock)
    snapshot = quote.to_snapshot()
    enriched["market_cap_billion"] = snapshot["total_market_cap_billion"]
    external_data = enriched.get("external_data")
    if not isinstance(external_data, dict):
        external_data = {}
    external_data["quote_snapshot"] = snapshot
    enriched["external_data"] = external_data
    return enriched, None


def enrich_command(args: argparse.Namespace) -> None:
    bundle = load_bundle(Path(args.input))
    enriched_stocks: list[dict[str, Any]] = []
    warnings: list[str] = []
    for item in bundle.get("stocks", []):
        if not isinstance(item, dict):
            warnings.append("Skipped non-object item in `stocks`.")
            continue
        enriched, warning = enrich_stock(item, args.refresh)
        enriched_stocks.append(enriched)
        if warning:
            warnings.append(warning)

    output = dict(bundle)
    output["stocks"] = enriched_stocks
    evidence_gaps = output.get("evidence_gaps", [])
    if not isinstance(evidence_gaps, list):
        evidence_gaps = [str(evidence_gaps)]
    if warnings:
        evidence_gaps.extend(warnings)
    output["evidence_gaps"] = evidence_gaps

    output_path = Path(args.output)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    write_json(
        {
            "output": str(output_path),
            "stock_count": len(enriched_stocks),
            "warning_count": len(warnings),
            "warnings": warnings,
        }
    )


def write_json(payload: object) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Enrich A-share stock observations with free quote snapshots.")
    parser.add_argument("--input", required=True, help="Path to a report bundle JSON object.")
    parser.add_argument("--output", required=True, help="Path to write the enriched report bundle JSON object.")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh quote snapshots and market cap even when `market_cap_billion` is already present.",
    )
    parser.set_defaults(func=enrich_command)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
