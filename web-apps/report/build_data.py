#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / "local"
INDUSTRY = ROOT / "industry-analysis"
REPORT_APP = ROOT / "web-apps" / "report"
OUT = REPORT_APP / "data.js"
INDUSTRY_ASSETS = REPORT_APP / "industry-assets"


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


def first_heading(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if match:
            return match.group(1)
    return fallback


def extract_report_date(markdown: str, fallback: str) -> str:
    match = re.search(r"分析日期[：:]\s*(\d{4}-\d{2}-\d{2})", markdown)
    if match:
        return match.group(1)
    match = re.search(r"(\d{4}-\d{2}-\d{2})$", fallback)
    return match.group(1) if match else ""


def rewrite_industry_image_refs(markdown: str, report_dir: Path, asset_slug: str) -> tuple[str, list[dict[str, str]]]:
    images: list[dict[str, str]] = []

    def repl(match: re.Match[str]) -> str:
        alt = match.group(1)
        src = match.group(2)
        if src.startswith(("http://", "https://", "data:")):
            images.append({"alt": alt, "src": src})
            return match.group(0)
        source = report_dir / src
        target_src = f"../industry-assets/{asset_slug}/{src}"
        if source.exists():
            images.append({"alt": alt, "src": target_src})
            return f"![{alt}]({target_src})"
        images.append({"alt": alt, "src": src})
        return match.group(0)

    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", repl, markdown), images


def collect_industry_reports() -> list[dict[str, Any]]:
    if INDUSTRY_ASSETS.exists():
        shutil.rmtree(INDUSTRY_ASSETS)
    INDUSTRY_ASSETS.mkdir(parents=True, exist_ok=True)

    if not INDUSTRY.exists():
        return []
    items: list[dict[str, Any]] = []
    for report_dir in sorted(INDUSTRY.iterdir()):
        if not report_dir.is_dir():
            continue
        report_path = report_dir / "report.md"
        if not report_path.exists():
            continue
        asset_dir = report_dir / "assets"
        if asset_dir.exists():
            shutil.copytree(asset_dir, INDUSTRY_ASSETS / report_dir.name / "assets", dirs_exist_ok=True)

        markdown, images = rewrite_industry_image_refs(read_text(report_path), report_dir, report_dir.name)
        source_data = read_json(report_dir / "source_data.json")
        quality = read_json(report_dir / "quality_report.json")
        items.append(
            {
                "id": report_dir.name,
                "title": first_heading(markdown, report_dir.name),
                "date": extract_report_date(markdown, report_dir.name),
                "markdown": markdown,
                "sourceData": source_data,
                "quality": quality,
                "images": images,
                "path": str(report_path.relative_to(ROOT)),
            }
        )
    return sorted(items, key=lambda item: (item.get("date") or "", item.get("id") or ""), reverse=True)


def main() -> None:
    payload = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "days": collect_days(),
        "weeklies": collect_weeklies(),
        "industryReports": collect_industry_reports(),
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    OUT.write_text(f"window.REPORT_DATA = {encoded};\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(OUT),
                "days": len(payload["days"]),
                "weeklies": len(payload["weeklies"]),
                "industryReports": len(payload["industryReports"]),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
