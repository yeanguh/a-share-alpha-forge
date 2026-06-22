#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from rank_news import Candidate, load_candidates, rank_candidates
from score_stocks import (
    MAX_MARKET_CAP_BILLION,
    MIN_MARKET_CAP_BILLION,
    MarketCapRange,
    StockObservation,
    load_observations,
)
from threshold_config import get_int, get_number, load_thresholds, threshold_version

VALID_FUND_DIRECTIONS = {"净流入扩散", "结构性流入", "缩量观望", "净流出扩散", "拥挤分化"}
VALID_DATA_QUALITY = {"full", "partial", "limited"}


def load_bundle(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Report bundle must be a JSON object")
    return payload


def write_temp_array(items: object, prefix: str) -> Path:
    if not isinstance(items, list):
        raise ValueError(f"`{prefix}` must be a JSON array")

    temp_root = Path(os.getenv("TMPDIR") or "tmp")
    temp_root.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix=f"{prefix}_",
        suffix=".json",
        dir=temp_root,
        delete=False,
    )
    with handle as temporary_file:
        path = Path(temporary_file.name)
        json.dump(items, temporary_file, ensure_ascii=False)
    return path


def load_from_bundle_array(items: object, prefix: str, loader: Any) -> Any:
    path = write_temp_array(items, prefix)
    try:
        return loader(path)
    finally:
        path.unlink(missing_ok=True)


def load_bundle_candidates(bundle: dict[str, Any]) -> list[Candidate]:
    return load_from_bundle_array(bundle.get("candidates"), "a_share_candidates_bundle", load_candidates)


def load_bundle_sector_candidates(bundle: dict[str, Any]) -> list[Candidate]:
    sector_candidates = bundle.get("sector_candidates", [])
    return load_from_bundle_array(sector_candidates, "a_share_sector_candidates_bundle", load_candidates)


def load_bundle_stocks(
    bundle: dict[str, Any],
    market_cap_range: MarketCapRange,
    threshold_config: dict[str, Any] | None = None,
) -> list[StockObservation]:
    return load_from_bundle_array(
        bundle.get("stocks", []),
        "a_share_stocks_bundle",
        lambda path: load_observations(path, market_cap_range, threshold_config),
    )


def validate_fund_flow(bundle: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    fund_flow = bundle.get("fund_flow")
    warnings: list[str] = []
    if not isinstance(fund_flow, dict):
        return {}, ["Missing `fund_flow`; final report must disclose fund-flow data gap."]

    direction = fund_flow.get("direction")
    if direction not in VALID_FUND_DIRECTIONS:
        warnings.append("Invalid or missing `fund_flow.direction`; use a defined fund-flow direction label.")

    quality = fund_flow.get("data_quality")
    if quality not in VALID_DATA_QUALITY:
        warnings.append("Invalid or missing `fund_flow.data_quality`; use full, partial, or limited.")
    elif quality != "full":
        warnings.append(f"Fund-flow data quality is `{quality}`; lower confidence in market-direction judgment.")
    if not isinstance(fund_flow.get("pbc_open_market_operation_summary"), str) or not fund_flow[
        "pbc_open_market_operation_summary"
    ].strip():
        warnings.append(
            "Missing `fund_flow.pbc_open_market_operation_summary`; disclose the PBOC open-market operation gap."
        )

    return fund_flow, warnings


def collect_warnings(
    bundle: dict[str, Any],
    candidates: list[Candidate],
    sector_candidates: list[Candidate],
    stocks: list[StockObservation],
    fund_warnings: list[str],
) -> list[str]:
    warnings = list(fund_warnings)
    positive_count = sum(1 for candidate in candidates if candidate.direction == "positive")
    negative_count = sum(1 for candidate in candidates if candidate.direction == "negative")
    if positive_count < 10:
        warnings.append(f"Only {positive_count} positive candidates available; positive Top 10 is incomplete.")
    if negative_count < 10:
        warnings.append(f"Only {negative_count} negative candidates available; negative Top 10 is incomplete.")
    if not stocks:
        warnings.append("No stock observations available; stock-level rating table is incomplete.")
    if not sector_candidates:
        warnings.append("No `sector_candidates` available; stock list cannot be audited as sector-first screening.")
    if sector_candidates and any(not stock.sector for stock in stocks):
        warnings.append(
            "Some stock observations have no `sector`; they cannot pass sector-first recommendation gating."
        )
    if evidence_gaps := bundle.get("evidence_gaps"):
        if isinstance(evidence_gaps, list):
            warnings.extend(str(gap) for gap in evidence_gaps)
        else:
            warnings.append("`evidence_gaps` must be an array when present.")
    return warnings


def selected_sector_names(
    sector_candidates: list[Candidate],
    direction: str,
    limit: int,
    min_impact_score: float = 0.0,
    min_price_volume: float = 0.0,
    min_liquidity: float = 0.0,
) -> set[str]:
    ranked = sorted(
        [
            candidate
            for candidate in sector_candidates
            if candidate.direction == direction
            and candidate.impact_score >= min_impact_score
            and candidate.price_volume >= min_price_volume
            and candidate.liquidity >= min_liquidity
        ],
        key=lambda candidate: candidate.impact_score,
        reverse=True,
    )
    return {candidate.title for candidate in ranked[:limit]}


def is_stock_from_selected_sector(stock: StockObservation, sector_names: set[str]) -> bool:
    if not sector_names:
        return False
    return stock.sector in sector_names


def stock_output(stock: StockObservation, sector_names: set[str]) -> dict[str, Any]:
    output = stock.to_dict()
    if not is_stock_from_selected_sector(stock, sector_names):
        reason = "未通过资讯板块筛选" if stock.sector else "未标注资讯板块"
        existing_reason = str(output["exclusion_reason"])
        output["eligible_for_recommendation"] = "no"
        output["exclusion_reason"] = f"{existing_reason}、{reason}" if existing_reason else reason
    return output


def is_recommendable_stock(stock: StockObservation, sector_names: set[str]) -> bool:
    return stock.eligible_for_recommendation and is_stock_from_selected_sector(stock, sector_names)


def ranked_mainline_sectors(
    sector_candidates: list[Candidate],
    limit: int,
) -> list[dict[str, float | int | str]]:
    positive_sectors = sorted(
        [candidate for candidate in sector_candidates if candidate.direction == "positive"],
        key=lambda candidate: candidate.impact_score,
        reverse=True,
    )
    remaining_sectors = sorted(
        [candidate for candidate in sector_candidates if candidate.direction != "positive"],
        key=lambda candidate: candidate.impact_score,
        reverse=True,
    )
    ranked = [*positive_sectors, *remaining_sectors][:limit]
    return [candidate.to_ranked_dict(rank) for rank, candidate in enumerate(ranked, start=1)]


def leading_stock_output(stock: StockObservation, mainline_sector_names: set[str]) -> dict[str, Any]:
    output = stock_output(stock, mainline_sector_names)
    output["leader_role"] = "eligible_leader" if output["eligible_for_recommendation"] == "yes" else "watch_leader"
    return output


def is_leader_quality_candidate(stock: StockObservation) -> bool:
    threshold = stock.threshold
    if stock.excluded_security:
        return False
    if stock.eligible_for_recommendation:
        return True
    return (
        stock.trend_score >= threshold("stock_gates", "leader_watch", "trend_min")
        and stock.volume_score >= threshold("stock_gates", "leader_watch", "volume_min")
        and stock.capital_recognition >= threshold("stock_gates", "leader_watch", "capital_recognition_min")
        and stock.event_alignment >= threshold("stock_gates", "leader_watch", "event_alignment_min")
        and stock.risk_score <= threshold("stock_gates", "leader_watch", "risk_max")
        and stock.research_rating != "风险回避"
    )


def beneficiary_sort_key(stock: StockObservation) -> tuple[float, float, float, float, float, float]:
    return (
        stock.beneficiary_quality_score,
        stock.institutional_trend_score,
        stock.capital_recognition,
        stock.trend_score,
        stock.volume_score,
        -stock.risk_score,
    )


def ranked_leading_stocks(
    stocks: list[StockObservation],
    mainline_sector_names: set[str],
    limit: int,
) -> list[dict[str, Any]]:
    mainline_stocks = [
        stock
        for stock in stocks
        if stock.directional_role == "beneficiary"
        and is_stock_from_selected_sector(stock, mainline_sector_names)
        and is_leader_quality_candidate(stock)
    ]
    ranked = sorted(
        mainline_stocks,
        key=lambda stock: (
            stock.eligible_for_recommendation,
            *beneficiary_sort_key(stock),
            stock.capital_recognition,
            stock.event_alignment,
        ),
        reverse=True,
    )
    return [leading_stock_output(stock, mainline_sector_names) for stock in ranked[:limit]]


def assemble_command(args: argparse.Namespace) -> None:
    threshold_config = load_thresholds(getattr(args, "threshold_config", None))
    min_market_cap = (
        args.min_market_cap_billion
        if args.min_market_cap_billion is not None
        else get_number(threshold_config, "market_cap_billion", "min")
    )
    max_market_cap = (
        args.max_market_cap_billion
        if args.max_market_cap_billion is not None
        else get_number(threshold_config, "market_cap_billion", "max")
    )
    market_cap_range = MarketCapRange(min_market_cap, max_market_cap)
    bundle = load_bundle(Path(args.input))
    candidates = load_bundle_candidates(bundle)
    sector_candidates = load_bundle_sector_candidates(bundle)
    stocks = load_bundle_stocks(bundle, market_cap_range, threshold_config)
    fund_flow, fund_warnings = validate_fund_flow(bundle)
    scored_stocks = sorted(stocks, key=lambda stock: stock.research_score, reverse=True)
    top_positive_sectors = (
        args.top_positive_sectors
        if args.top_positive_sectors is not None
        else get_int(threshold_config, "top_limits", "positive_sectors")
    )
    top_negative_sectors = (
        args.top_negative_sectors
        if args.top_negative_sectors is not None
        else get_int(threshold_config, "top_limits", "negative_sectors")
    )
    top_positive = (
        args.top_positive if args.top_positive is not None else get_int(threshold_config, "top_limits", "positive_candidates")
    )
    top_negative = (
        args.top_negative if args.top_negative is not None else get_int(threshold_config, "top_limits", "negative_candidates")
    )
    top_mainline_sectors = (
        args.top_mainline_sectors
        if args.top_mainline_sectors is not None
        else get_int(threshold_config, "top_limits", "mainline_sectors")
    )
    top_leading_stocks = (
        args.top_leading_stocks
        if args.top_leading_stocks is not None
        else get_int(threshold_config, "top_limits", "leading_stocks")
    )
    min_beneficiary_sector_impact = (
        args.min_beneficiary_sector_impact
        if args.min_beneficiary_sector_impact is not None
        else get_number(threshold_config, "sector_gates", "beneficiary", "impact_score_min")
    )
    min_beneficiary_sector_price_volume = (
        args.min_beneficiary_sector_price_volume
        if args.min_beneficiary_sector_price_volume is not None
        else get_number(threshold_config, "sector_gates", "beneficiary", "price_volume_min")
    )
    min_beneficiary_sector_liquidity = (
        args.min_beneficiary_sector_liquidity
        if args.min_beneficiary_sector_liquidity is not None
        else get_number(threshold_config, "sector_gates", "beneficiary", "liquidity_min")
    )
    positive_sectors = selected_sector_names(
        sector_candidates,
        "positive",
        top_positive_sectors,
        min_beneficiary_sector_impact,
        min_beneficiary_sector_price_volume,
        min_beneficiary_sector_liquidity,
    )
    negative_sectors = selected_sector_names(sector_candidates, "negative", top_negative_sectors)
    mainline_sectors = ranked_mainline_sectors(sector_candidates, top_mainline_sectors)
    mainline_sector_names = {str(sector["title"]) for sector in mainline_sectors}

    output = {
        "window": bundle.get("window", {}),
        "market_cap_filter": {
            "min_billion": market_cap_range.minimum_billion,
            "max_billion": market_cap_range.maximum_billion,
            "description": market_cap_range.description,
            "used_for_eligibility": False,
        },
        "market_cap_context": {
            "description": "display_only",
            "used_for_eligibility": False,
        },
        "threshold_config": {
            "version": threshold_version(threshold_config),
            "path": str(getattr(args, "threshold_config", None) or "default"),
            "beneficiary_sector_gate": {
                "impact_score_min": min_beneficiary_sector_impact,
                "price_volume_min": min_beneficiary_sector_price_volume,
                "liquidity_min": min_beneficiary_sector_liquidity,
            },
        },
        "fund_flow": fund_flow,
        "sector_rankings": {
            "positive": rank_candidates(sector_candidates, "positive", top_positive_sectors),
            "negative": rank_candidates(sector_candidates, "negative", top_negative_sectors),
        },
        "daily_mainlines": mainline_sectors,
        "leading_stocks": ranked_leading_stocks(scored_stocks, mainline_sector_names, top_leading_stocks),
        "rankings": {
            "positive": rank_candidates(candidates, "positive", top_positive),
            "negative": rank_candidates(candidates, "negative", top_negative),
        },
        "stocks": [
            stock_output(
                stock,
                positive_sectors if stock.directional_role == "beneficiary" else negative_sectors,
            )
            for stock in scored_stocks
        ],
        "eligible_beneficiaries": [
            stock.to_dict()
            for stock in sorted(scored_stocks, key=beneficiary_sort_key, reverse=True)
            if stock.directional_role == "beneficiary" and is_recommendable_stock(stock, positive_sectors)
        ],
        "eligible_pressure": [
            stock.to_dict()
            for stock in scored_stocks
            if stock.directional_role == "pressure" and is_recommendable_stock(stock, negative_sectors)
        ],
        "excluded_stocks": [
            stock_output(
                stock,
                positive_sectors if stock.directional_role == "beneficiary" else negative_sectors,
            )
            for stock in scored_stocks
            if not is_recommendable_stock(
                stock,
                positive_sectors if stock.directional_role == "beneficiary" else negative_sectors,
            )
        ],
        "warnings": collect_warnings(bundle, candidates, sector_candidates, stocks, fund_warnings),
    }
    if "supplemental_stock_analysis" in bundle:
        output["supplemental_stock_analysis"] = bundle.get("supplemental_stock_analysis")
    if "supplemental_conclusion" in bundle:
        output["supplemental_conclusion"] = bundle.get("supplemental_conclusion")
    write_json(output, Path(args.output) if args.output else None)


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
    parser = argparse.ArgumentParser(description="Assemble A-share brief scoring data.")
    parser.add_argument("--input", required=True, help="Path to a report bundle JSON object.")
    parser.add_argument("--output", help="Optional path to write assembled scoring JSON.")
    parser.add_argument("--threshold-config", help="Optional threshold config JSON. Defaults to skill config.")
    parser.add_argument("--top-positive-sectors", type=int, default=None, help="Number of positive sectors to emit.")
    parser.add_argument("--top-negative-sectors", type=int, default=None, help="Number of negative sectors to emit.")
    parser.add_argument("--top-positive", type=int, default=None, help="Number of positive candidates to emit.")
    parser.add_argument("--top-negative", type=int, default=None, help="Number of negative candidates to emit.")
    parser.add_argument(
        "--min-beneficiary-sector-impact",
        type=float,
        default=None,
        help="Minimum sector impact score required before beneficiary stocks can enter the opportunity list.",
    )
    parser.add_argument(
        "--min-beneficiary-sector-price-volume",
        type=float,
        default=None,
        help="Minimum sector price/volume confirmation required for beneficiary opportunity eligibility.",
    )
    parser.add_argument(
        "--min-beneficiary-sector-liquidity",
        type=float,
        default=None,
        help="Minimum sector liquidity confirmation required for beneficiary opportunity eligibility.",
    )
    parser.add_argument(
        "--top-mainline-sectors",
        type=int,
        default=None,
        help="Number of daily mainline sectors or concepts to emit.",
    )
    parser.add_argument(
        "--top-leading-stocks",
        type=int,
        default=None,
        help="Number of leading stocks from daily mainline sectors to emit.",
    )
    parser.add_argument(
        "--min-market-cap-billion",
        type=float,
        default=None,
        help="Deprecated; market cap is retained as display context, not recommendation eligibility.",
    )
    parser.add_argument(
        "--max-market-cap-billion",
        type=float,
        default=None,
        help="Deprecated; market cap is retained as display context, not recommendation eligibility.",
    )
    parser.set_defaults(func=assemble_command)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
