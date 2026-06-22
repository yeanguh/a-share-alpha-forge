#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / "local"
OUT = ROOT / "web-report" / "data.js"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def compact_stock(stock: dict[str, Any]) -> dict[str, Any]:
    return {
        "ticker": stock.get("ticker", ""),
        "name": stock.get("name", ""),
        "sector": stock.get("sector", ""),
        "role": stock.get("directional_role") or stock.get("role", ""),
        "rating": stock.get("research_rating", ""),
        "tendency": stock.get("operation_tendency", ""),
        "quality": stock.get("beneficiary_quality_score"),
        "score": stock.get("research_score"),
        "trend": stock.get("trend_score"),
        "volume": stock.get("volume_score"),
        "capital": stock.get("capital_recognition"),
        "risk": stock.get("risk_score"),
        "exclusion": stock.get("exclusion_reason") or stock.get("excluded_reason") or "",
    }


def compact_hit(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": item.get("name") or item.get("sector") or item.get("ticker") or "",
        "ticker": item.get("ticker", ""),
        "sector": item.get("sector", ""),
        "hit": item.get("hit"),
        "level": item.get("hit_level") or item.get("hit_grade") or item.get("direction_hit_level") or "",
        "reason": item.get("reason") or item.get("explanation") or item.get("actual_move") or "",
        "move": item.get("actual_move") or "",
        "returnPct": item.get("actual_return_pct")
        or item.get("open_to_close_pct")
        or item.get("return_since_report_open_pct"),
    }


def compact_day(day_dir: Path) -> dict[str, Any]:
    date = day_dir.name
    assembled = read_json(day_dir / "assembled.json")
    close = read_json(day_dir / "close_review.json")
    report_md = read_text(day_dir / "report.md")
    close_md = read_text(day_dir / "close_review.md")

    mainlines = assembled.get("daily_mainlines") or []
    leaders = assembled.get("leading_stocks") or []
    beneficiaries = assembled.get("eligible_beneficiaries") or []
    pressure = assembled.get("eligible_pressure") or []
    fund_flow = assembled.get("fund_flow") or {}

    return {
        "date": date,
        "hasDaily": bool(report_md),
        "hasCloseReview": bool(close),
        "hasCloseMarkdown": bool(close_md),
        "dailyMarkdown": report_md,
        "closeMarkdown": close_md,
        "window": assembled.get("window") or {},
        "fundFlow": {
            "direction": fund_flow.get("direction", ""),
            "turnover": fund_flow.get("turnover_summary", ""),
            "mainFlow": fund_flow.get("main_flow_summary", ""),
            "sectorFlow": fund_flow.get("sector_flow_summary", ""),
            "breadth": fund_flow.get("breadth_summary", ""),
            "pbc": fund_flow.get("pbc_open_market_operation_summary", ""),
            "quality": fund_flow.get("data_quality", ""),
        },
        "mainlines": [
            {
                "title": item.get("title", ""),
                "score": item.get("impact_score"),
                "direction": item.get("direction", ""),
                "reason": item.get("reason") or item.get("summary") or "",
            }
            for item in mainlines
            if isinstance(item, dict)
        ],
        "leaders": [compact_stock(item) for item in leaders if isinstance(item, dict)],
        "beneficiaries": [compact_stock(item) for item in beneficiaries if isinstance(item, dict)],
        "pressure": [compact_stock(item) for item in pressure if isinstance(item, dict)],
        "warnings": assembled.get("warnings") or [],
        "closeReview": {
            "reviewTime": close.get("review_time", ""),
            "directionHit": close.get("direction_hit"),
            "directionLevel": close.get("direction_hit_level") or close.get("direction_hit_grade") or "",
            "directionReason": close.get("direction_hit_reason")
            or close.get("direction_review")
            or close.get("direction_review", ""),
            "averageStockError": close.get("average_stock_error"),
            "lesson": close.get("lesson", ""),
            "sectorHits": [compact_hit(item) for item in (close.get("sector_hits") or []) if isinstance(item, dict)],
            "stockHits": [compact_hit(item) for item in (close.get("stock_hits") or []) if isinstance(item, dict)],
        },
    }


def collect_days() -> list[dict[str, Any]]:
    days: list[dict[str, Any]] = []
    if not LOCAL.exists():
        return days
    for child in sorted(LOCAL.iterdir()):
        if not child.is_dir():
            continue
        try:
            datetime.strptime(child.name, "%Y-%m-%d")
        except ValueError:
            continue
        if (child / "assembled.json").exists() or (child / "report.md").exists():
            days.append(compact_day(child))
    return days


def collect_weeklies() -> list[dict[str, Any]]:
    weekly_dir = LOCAL / "reviews" / "weekly"
    if not weekly_dir.exists():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(weekly_dir.glob("weekly_review_*.md")):
        stem = path.stem.removeprefix("weekly_review_")
        json_path = path.with_suffix(".json")
        payload = read_json(json_path)
        items.append(
            {
                "id": stem,
                "title": stem.replace("_", " 至 "),
                "markdown": read_text(path),
                "summary": payload,
                "hasJson": json_path.exists(),
            }
        )
    return items


def main() -> None:
    payload = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "days": collect_days(),
        "weeklies": collect_weeklies(),
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    OUT.write_text(f"window.REPORT_DATA = {encoded};\n", encoding="utf-8")
    print(json.dumps({"output": str(OUT), "days": len(payload["days"]), "weeklies": len(payload["weeklies"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
