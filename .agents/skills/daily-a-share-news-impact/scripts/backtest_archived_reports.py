#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from tencent_quote import DailyBar, Quote, fetch_kline, fetch_quote

DEFAULT_ROOT = Path("local")
DEFAULT_REVIEW_ROOT = DEFAULT_ROOT / "reviews"


@dataclass(frozen=True)
class StockPick:
    report_date: str
    ticker: str
    name: str
    role: str
    sector: str
    expected_positive: bool
    eligible_for_recommendation: str
    exclusion_reason: str


def parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")


def report_dirs(root: Path, start: str | None, end: str | None) -> list[Path]:
    start_date = parse_date(start) if start else None
    end_date = parse_date(end) if end else None
    directories: list[Path] = []
    for child in root.iterdir() if root.exists() else []:
        if not child.is_dir() or not (child / "assembled.json").exists():
            continue
        try:
            current = parse_date(child.name)
        except ValueError:
            continue
        if start_date and current < start_date:
            continue
        if end_date and current > end_date:
            continue
        directories.append(child)
    return sorted(directories)


def load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"`{path}` must contain a JSON object")
    return payload


def text_field(payload: dict[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    return value if isinstance(value, str) else ""


def stock_pick_from_payload(
    *,
    report_date: str,
    payload: dict[str, Any],
    role: str,
    expected_positive: bool,
) -> StockPick:
    return StockPick(
        report_date=report_date,
        ticker=text_field(payload, "ticker"),
        name=text_field(payload, "name"),
        role=role,
        sector=text_field(payload, "sector"),
        expected_positive=expected_positive,
        eligible_for_recommendation=text_field(payload, "eligible_for_recommendation"),
        exclusion_reason=text_field(payload, "exclusion_reason"),
    )


def load_recommendation_picks(day_dir: Path) -> list[StockPick]:
    assembled = load_json_object(day_dir / "assembled.json")
    picks: list[StockPick] = []
    for role, expected_positive, field_name in (
        ("beneficiary", True, "eligible_beneficiaries"),
        ("pressure", False, "eligible_pressure"),
    ):
        for item in assembled.get(field_name, []):
            if not isinstance(item, dict):
                continue
            picks.append(
                stock_pick_from_payload(
                    report_date=day_dir.name,
                    payload=item,
                    role=role,
                    expected_positive=expected_positive,
                )
            )
    return picks


def load_candidate_picks(day_dir: Path) -> list[StockPick]:
    bundle = load_json_object(day_dir / "input_bundle.json")
    stocks = bundle.get("stocks", [])
    if not isinstance(stocks, list):
        return []
    picks: list[StockPick] = []
    for item in stocks:
        if not isinstance(item, dict):
            continue
        role = text_field(item, "directional_role")
        if role not in {"beneficiary", "pressure"}:
            continue
        picks.append(
            stock_pick_from_payload(
                report_date=day_dir.name,
                payload=item,
                role=role,
                expected_positive=role == "beneficiary",
            )
        )
    return picks


def load_stock_picks(day_dir: Path, include_leaders: bool, include_candidates: bool) -> list[StockPick]:
    if include_candidates:
        return [pick for pick in load_candidate_picks(day_dir) if pick.ticker and pick.name]

    assembled = load_json_object(day_dir / "assembled.json")
    picks = load_recommendation_picks(day_dir)
    if include_leaders:
        recommendation_tickers = {pick.ticker for pick in picks}
        for item in assembled.get("leading_stocks", []):
            if not isinstance(item, dict):
                continue
            ticker = text_field(item, "ticker")
            if ticker in recommendation_tickers:
                continue
            picks.append(
                StockPick(
                    report_date=day_dir.name,
                    ticker=ticker,
                    name=text_field(item, "name"),
                    role="leader",
                    sector=text_field(item, "sector"),
                    expected_positive=True,
                    eligible_for_recommendation=text_field(item, "eligible_for_recommendation"),
                    exclusion_reason=text_field(item, "exclusion_reason"),
                )
            )
    return [pick for pick in picks if pick.ticker and pick.name]


def baseline_bar_index(bars: list[DailyBar], report_date: str) -> int | None:
    for index, bar in enumerate(bars):
        if bar.trade_date >= report_date:
            return index
    return None


def exit_price_and_date(
    *,
    quote: Quote,
    bars: list[DailyBar],
    baseline_index: int,
    horizon_trading_days: int | None,
) -> tuple[float, str, str]:
    if horizon_trading_days is None:
        return quote.last_price, quote.timestamp, "latest_quote"

    exit_index = baseline_index + horizon_trading_days - 1
    if exit_index >= len(bars):
        raise IndexError("Not enough K-line bars for requested horizon")
    exit_bar = bars[exit_index]
    return exit_bar.close_price, exit_bar.trade_date, "fixed_horizon_close"


def evaluate_pick(
    pick: StockPick,
    quote: Quote,
    bars: list[DailyBar],
    horizon_trading_days: int | None,
    minimum_hit_return_pct: float,
) -> dict[str, Any]:
    baseline_index = baseline_bar_index(bars, pick.report_date)
    if baseline_index is None:
        return {
            **pick.__dict__,
            "status": "missing_baseline",
            "hit": False,
        }
    baseline = bars[baseline_index]
    try:
        exit_price, exit_date, evaluation_mode = exit_price_and_date(
            quote=quote,
            bars=bars,
            baseline_index=baseline_index,
            horizon_trading_days=horizon_trading_days,
        )
    except IndexError:
        return {
            **pick.__dict__,
            "status": "insufficient_horizon",
            "hit": False,
            "baseline_date": baseline.trade_date,
            "baseline_open": baseline.open_price,
            "requested_horizon_trading_days": horizon_trading_days,
        }
    return_pct = round((exit_price / baseline.open_price - 1.0) * 100, 2)
    directional_return_pct = return_pct if pick.expected_positive else -return_pct
    hit = return_pct >= minimum_hit_return_pct if pick.expected_positive else return_pct <= -minimum_hit_return_pct
    return {
        **pick.__dict__,
        "status": "evaluated",
        "hit": hit,
        "minimum_hit_return_pct": minimum_hit_return_pct,
        "baseline_date": baseline.trade_date,
        "baseline_open": baseline.open_price,
        "current_price": quote.last_price,
        "exit_date": exit_date,
        "exit_price": exit_price,
        "evaluation_mode": evaluation_mode,
        "horizon_trading_days": "" if horizon_trading_days is None else horizon_trading_days,
        "return_since_report_open_pct": return_pct,
        "directional_return_pct": directional_return_pct,
        "today_pct": quote.pct_change,
        "turnover_rate": quote.turnover_rate,
        "market_cap_billion": quote.total_market_cap_billion,
        "quote_time": quote.timestamp,
    }


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    evaluated = [row for row in rows if row.get("status") == "evaluated"]
    if not evaluated:
        return {
            "count": 0,
            "hit_rate": None,
            "average_return_pct": None,
            "average_directional_return_pct": None,
            "median_return_pct": None,
            "median_directional_return_pct": None,
            "average_gain_pct": None,
            "average_loss_pct": None,
            "payoff_ratio": None,
            "worst_return_pct": None,
            "best_return_pct": None,
        }
    returns = sorted(float(row["return_since_report_open_pct"]) for row in evaluated)
    directional_returns = sorted(
        float(row.get("directional_return_pct", row["return_since_report_open_pct"])) for row in evaluated
    )
    gains = [value for value in directional_returns if value > 0]
    losses = [value for value in directional_returns if value < 0]
    return_midpoint = len(returns) // 2
    directional_midpoint = len(directional_returns) // 2
    median = (
        returns[return_midpoint] if len(returns) % 2 else (returns[return_midpoint - 1] + returns[return_midpoint]) / 2
    )
    directional_median = (
        directional_returns[directional_midpoint]
        if len(directional_returns) % 2
        else (directional_returns[directional_midpoint - 1] + directional_returns[directional_midpoint]) / 2
    )
    average_gain = sum(gains) / len(gains) if gains else None
    average_loss = sum(losses) / len(losses) if losses else None
    payoff_ratio = None
    if average_gain is not None and average_loss is not None and average_loss != 0:
        payoff_ratio = abs(average_gain / average_loss)
    return {
        "count": len(evaluated),
        "hit_rate": round(sum(1 for row in evaluated if row["hit"]) / len(evaluated), 3),
        "average_return_pct": round(sum(returns) / len(returns), 3),
        "average_directional_return_pct": round(sum(directional_returns) / len(directional_returns), 3),
        "median_return_pct": round(median, 3),
        "median_directional_return_pct": round(directional_median, 3),
        "average_gain_pct": None if average_gain is None else round(average_gain, 3),
        "average_loss_pct": None if average_loss is None else round(average_loss, 3),
        "payoff_ratio": None if payoff_ratio is None else round(payoff_ratio, 3),
        "worst_return_pct": round(returns[0], 3),
        "best_return_pct": round(returns[-1], 3),
        "worst_directional_return_pct": round(directional_returns[0], 3),
        "best_directional_return_pct": round(directional_returns[-1], 3),
    }


def summarize_by_role(rows: list[dict[str, Any]]) -> dict[str, Any]:
    roles = sorted({str(row.get("role")) for row in rows})
    return {role: summarize_rows([row for row in rows if row.get("role") == role]) for role in roles}


def summarize_by_report(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dates = sorted({str(row.get("report_date")) for row in rows})
    return [
        {
            "report_date": report_date,
            "overall": summarize_rows([row for row in rows if row.get("report_date") == report_date]),
            "by_role": summarize_by_role([row for row in rows if row.get("report_date") == report_date]),
        }
        for report_date in dates
    ]


def worst_misses(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    misses = [row for row in rows if row.get("status") == "evaluated" and not row.get("hit")]
    return sorted(
        misses,
        key=lambda row: abs(float(row.get("return_since_report_open_pct", 0))),
        reverse=True,
    )[:limit]


def best_hits(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    hits = [row for row in rows if row.get("status") == "evaluated" and row.get("hit")]
    return sorted(
        hits,
        key=lambda row: abs(float(row.get("return_since_report_open_pct", 0))),
        reverse=True,
    )[:limit]


def backtest_command(args: argparse.Namespace) -> None:
    if args.horizon_trading_days is not None and args.horizon_trading_days <= 0:
        raise ValueError("`horizon_trading_days` must be positive when provided")
    if args.min_hit_return_pct < 0:
        raise ValueError("`min_hit_return_pct` must be non-negative")

    picks: list[StockPick] = []
    for day_dir in report_dirs(Path(args.output_root), args.start, args.end):
        picks.extend(load_stock_picks(day_dir, args.include_leaders, args.include_candidates))

    tickers = sorted({pick.ticker for pick in picks})
    quotes = {ticker: fetch_quote(ticker) for ticker in tickers}
    klines = {ticker: fetch_kline(ticker, args.kline_days) for ticker in tickers}
    rows = [
        evaluate_pick(
            pick,
            quotes[pick.ticker],
            klines[pick.ticker],
            args.horizon_trading_days,
            args.min_hit_return_pct,
        )
        for pick in picks
    ]
    payload = {
        "review_time": datetime.now().astimezone().isoformat(),
        "review_type": "archived_report_realtime_backtest",
        "source": "tencent_public_quote_and_kline",
        "evaluation_mode": "fixed_horizon_close" if args.horizon_trading_days else "latest_quote",
        "horizon_trading_days": args.horizon_trading_days,
        "minimum_hit_return_pct": args.min_hit_return_pct,
        "pick_scope": "all_input_bundle_candidates" if args.include_candidates else "recommendation_rows",
        "report_count": len({pick.report_date for pick in picks}),
        "stock_pick_count": len(picks),
        "ticker_count": len(tickers),
        "overall": summarize_rows(rows),
        "by_role": summarize_by_role(rows),
        "by_report": summarize_by_report(rows),
        "best_hits": best_hits(rows, args.extreme_limit),
        "worst_misses": worst_misses(rows, args.extreme_limit),
        "rows": rows,
    }
    write_json(payload, Path(args.output) if args.output else None)


def write_json(payload: object, output_path: Path | None = None) -> None:
    encoded = json.dumps(payload, ensure_ascii=False, indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(f"{encoded}\n", encoding="utf-8")
        sys.stdout.write(json.dumps({"output": str(output_path)}, ensure_ascii=False, indent=2))
        sys.stdout.write("\n")
        return
    sys.stdout.write(encoded)
    sys.stdout.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backtest archived A-share reports against free realtime quotes.")
    parser.add_argument("--output-root", default=str(DEFAULT_ROOT), help="Archive root directory.")
    parser.add_argument(
        "--output",
        help=f"Optional path for backtest JSON. Recommended root: {DEFAULT_REVIEW_ROOT}/backtests/.",
    )
    parser.add_argument("--start", help="Start report date in YYYY-MM-DD format.")
    parser.add_argument("--end", help="End report date in YYYY-MM-DD format.")
    parser.add_argument("--kline-days", type=int, default=30, help="Number of daily bars to fetch per ticker.")
    parser.add_argument("--extreme-limit", type=int, default=10, help="Number of best hits and worst misses to emit.")
    parser.add_argument(
        "--horizon-trading-days",
        type=int,
        help=(
            "Evaluate from the report-date open to the close of the Nth trading day. "
            "For example, 1 means report-day close and 3 means the third trading-day close. "
            "When omitted, evaluate against the latest realtime quote."
        ),
    )
    parser.add_argument(
        "--min-hit-return-pct",
        type=float,
        default=0.0,
        help=(
            "Minimum absolute return required for a pick to count as a hit. "
            "Beneficiary rows need returns greater than or equal to this value, "
            "and pressure rows need returns less than or equal to the negative value."
        ),
    )
    parser.add_argument(
        "--include-leaders",
        action="store_true",
        help="Include mainline leader-table stocks that are not already recommendation rows.",
    )
    parser.add_argument(
        "--include-candidates",
        action="store_true",
        help=(
            "Evaluate every beneficiary or pressure stock observation from each archived input bundle. "
            "This is intended for threshold scans and ignores `--include-leaders`."
        ),
    )
    parser.set_defaults(func=backtest_command)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
