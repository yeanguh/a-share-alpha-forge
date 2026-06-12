#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import assemble_report_data
import persist_report
import render_report


DEFAULT_WORK_DIR = Path("tmp") / "daily-a-share-news-impact"


def safe_run_id(value: str | None = None) -> str:
    return persist_report.safe_run_id(value or datetime.now().strftime("%H%M%S"))


def run_command(args: argparse.Namespace) -> None:
    run_id = safe_run_id(args.run_id)
    work_dir = Path(args.work_dir) / run_id
    work_dir.mkdir(parents=True, exist_ok=True)

    bundle_path = Path(args.bundle)
    assembled_path = Path(args.assembled_output) if args.assembled_output else work_dir / "assembled.json"
    report_path = Path(args.report_output) if args.report_output else work_dir / "report.md"

    assemble_report_data.assemble_command(
        argparse.Namespace(
            input=str(bundle_path),
            output=str(assembled_path),
            threshold_config=args.threshold_config,
            top_positive_sectors=args.top_positive_sectors,
            top_negative_sectors=args.top_negative_sectors,
            top_positive=args.top_positive,
            top_negative=args.top_negative,
            min_beneficiary_sector_impact=args.min_beneficiary_sector_impact,
            min_beneficiary_sector_price_volume=args.min_beneficiary_sector_price_volume,
            min_beneficiary_sector_liquidity=args.min_beneficiary_sector_liquidity,
            top_mainline_sectors=args.top_mainline_sectors,
            top_leading_stocks=args.top_leading_stocks,
            min_market_cap_billion=args.min_market_cap_billion,
            max_market_cap_billion=args.max_market_cap_billion,
        )
    )
    render_report.render_command(argparse.Namespace(assembled=str(assembled_path), output=str(report_path)))
    persist_report.persist_command(
        argparse.Namespace(
            bundle=str(bundle_path),
            assembled=str(assembled_path),
            report=str(report_path),
            close_review=None,
            date=args.date,
            output_root=args.output_root,
            run_id=run_id,
        )
    )

    summary = {
        "run_id": run_id,
        "bundle": str(bundle_path),
        "assembled": str(assembled_path),
        "report": str(report_path),
        "output_root": args.output_root,
    }
    sys.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the daily A-share brief pipeline from an existing input bundle."
    )
    parser.add_argument("--bundle", required=True, help="Path to input_bundle.json.")
    parser.add_argument("--work-dir", default=str(DEFAULT_WORK_DIR), help="Temporary working output root.")
    parser.add_argument("--assembled-output", help="Optional assembled JSON output path.")
    parser.add_argument("--report-output", help="Optional rendered Markdown report output path.")
    parser.add_argument("--output-root", default=str(persist_report.DEFAULT_ROOT), help="Archive root directory.")
    parser.add_argument("--run-id", help="Stable run id for work dir and archive.")
    parser.add_argument("--date", help="Override report date in YYYY-MM-DD format.")
    parser.add_argument("--threshold-config", help="Optional threshold config JSON. Defaults to skill config.")
    parser.add_argument("--top-positive-sectors", type=int, default=None)
    parser.add_argument("--top-negative-sectors", type=int, default=None)
    parser.add_argument("--top-positive", type=int, default=None)
    parser.add_argument("--top-negative", type=int, default=None)
    parser.add_argument("--min-beneficiary-sector-impact", type=float, default=None)
    parser.add_argument("--min-beneficiary-sector-price-volume", type=float, default=None)
    parser.add_argument("--min-beneficiary-sector-liquidity", type=float, default=None)
    parser.add_argument("--top-mainline-sectors", type=int, default=None)
    parser.add_argument("--top-leading-stocks", type=int, default=None)
    parser.add_argument("--min-market-cap-billion", type=float, default=None)
    parser.add_argument("--max-market-cap-billion", type=float, default=None)
    parser.set_defaults(func=run_command)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
