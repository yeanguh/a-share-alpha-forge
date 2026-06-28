#!/usr/bin/env python3
"""Integrated A-share stock-selection orchestrator.

The script ranks research candidates from local archives first. It can optionally
call the existing quote/valuation helper for a narrowed list, but it does not
refresh network data by default.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
TMP = ROOT / "tmp" / "integrated-selection"


def raw_code(value: object) -> str:
    code = str(value or "").strip().upper()
    code = code.replace(".SH", "").replace(".SZ", "").replace(".BJ", "")
    code = re.sub(r"^(SH|SZ|BJ)", "", code)
    digits = re.sub(r"\D", "", code)
    return digits.zfill(6) if digits else ""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def latest_archive_date() -> str:
    dates = sorted(path.parent.name for path in (ROOT / "local").glob("*/assembled.json"))
    if not dates:
        raise FileNotFoundError("no local/YYYY-MM-DD/assembled.json archive found")
    return dates[-1]


def load_archive(date: str | None) -> tuple[str, dict[str, Any]]:
    selected = date or latest_archive_date()
    path = ROOT / "local" / selected / "assembled.json"
    if not path.exists():
        raise FileNotFoundError(f"archive not found: {path.relative_to(ROOT)}")
    return selected, read_json(path)


def as_float(value: object, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def score5(value: object, default: float = 2.5) -> float:
    return max(0.0, min(5.0, as_float(value, default)))


def contains_theme(text: str, theme: str | None) -> bool:
    if not theme:
        return True
    return theme.lower() in text.lower()


def mainline_matches(archive: dict[str, Any], theme: str | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in archive.get("daily_mainlines", []):
        title = str(item.get("title") or "")
        key = (title, str(item.get("direction") or ""))
        if contains_theme(title, theme) and key not in seen:
            seen.add(key)
            rows.append(item)
    for direction in ("positive", "negative"):
        for item in archive.get("sector_rankings", {}).get(direction, []):
            title = str(item.get("title") or item.get("sector") or "")
            key = (title, str(item.get("direction") or direction))
            if contains_theme(title, theme) and key not in seen:
                seen.add(key)
                rows.append(item)
    return rows


def industry_matches(theme: str | None) -> dict[str, list[dict[str, str]]]:
    matches: dict[str, list[dict[str, str]]] = {}
    for source_path in sorted((ROOT / "industry-analysis").glob("*/source_data.json")):
        try:
            data = read_json(source_path)
        except Exception:
            continue
        topic = str(data.get("topic") or source_path.parent.name)
        report_text = topic + " " + source_path.parent.name
        if not contains_theme(report_text, theme):
            if theme:
                continue
        for company in data.get("companies", []) or []:
            code = raw_code(company.get("code"))
            if not code:
                continue
            matches.setdefault(code, []).append(
                {
                    "topic": topic,
                    "report": str(source_path.parent.relative_to(ROOT)),
                    "role": str(company.get("role") or ""),
                    "name": str(company.get("name") or ""),
                }
            )
    return matches


@dataclass
class Candidate:
    code: str
    name: str = ""
    sector: str = ""
    source_tags: set[str] = field(default_factory=set)
    raw: dict[str, Any] = field(default_factory=dict)
    industry: list[dict[str, str]] = field(default_factory=list)
    manual: bool = False

    def merge(self, item: dict[str, Any], tag: str) -> None:
        self.source_tags.add(tag)
        if not self.raw or tag == "eligible_beneficiaries":
            self.raw.update(item)
        self.name = self.name or str(item.get("name") or "")
        self.sector = self.sector or str(item.get("sector") or item.get("theme") or "")


def add_candidate(candidates: dict[str, Candidate], item: dict[str, Any], tag: str) -> None:
    code = raw_code(item.get("ticker") or item.get("code"))
    if not code:
        return
    candidate = candidates.setdefault(code, Candidate(code=code))
    candidate.merge(item, tag)


def collect_candidates(archive: dict[str, Any], codes: list[str], theme: str | None) -> dict[str, Candidate]:
    candidates: dict[str, Candidate] = {}
    explicit_codes = {raw_code(code) for code in codes if raw_code(code)}
    for tag in ("eligible_beneficiaries", "leading_stocks", "stocks"):
        for item in archive.get(tag, []) or []:
            sector_text = " ".join(str(item.get(key) or "") for key in ("sector", "name", "ticker"))
            if theme and not contains_theme(sector_text, theme):
                continue
            add_candidate(candidates, item, tag)
    for code in codes:
        normalized = raw_code(code)
        if normalized:
            candidate = candidates.setdefault(normalized, Candidate(code=normalized, manual=True))
            candidate.manual = True
            candidate.source_tags.add("manual_codes")
    matched_industries = industry_matches(theme)
    for code, matches in matched_industries.items():
        if code in candidates or code in explicit_codes or theme:
            candidate = candidates.setdefault(code, Candidate(code=code))
            candidate.industry.extend(matches)
            candidate.source_tags.add("industry-analysis")
            if matches:
                candidate.name = candidate.name or matches[0].get("name", "")
                candidate.sector = candidate.sector or matches[0].get("topic", "")
    return candidates


def candidate_score(candidate: Candidate) -> tuple[float, dict[str, float], list[str], str]:
    raw = candidate.raw
    risk = score5(raw.get("risk_score"), 2.5)
    retail_quality = score5(raw.get("retail_voc_quality_score"), 3.0)
    dims = {
        "event": score5(raw.get("event_alignment"), 2.0),
        "beneficiary": score5(raw.get("beneficiary_quality_score"), 2.5),
        "capital": score5(raw.get("capital_recognition"), 2.5),
        "trend": score5(raw.get("trend_score"), 2.5),
        "volume": score5(raw.get("volume_score"), 2.5),
        "institutional": score5(raw.get("institutional_trend_score"), 2.2),
        "retail_quality": retail_quality,
        "risk_control": max(0.0, min(5.0, 5.0 - max(0.0, risk - 1.0))),
        "industry": 5.0 if candidate.industry else 0.0,
    }
    score = (
        dims["event"] * 3.6
        + dims["beneficiary"] * 2.8
        + dims["capital"] * 2.4
        + dims["trend"] * 2.0
        + dims["volume"] * 1.6
        + dims["institutional"] * 2.0
        + dims["retail_quality"] * 1.2
        + dims["risk_control"] * 2.0
        + dims["industry"] * 2.0
    )
    reasons: list[str] = []
    if "eligible_beneficiaries" in candidate.source_tags:
        score += 5
        reasons.append("已通过日报受益股门禁")
    if "leading_stocks" in candidate.source_tags:
        score += 3
        reasons.append("位于日报龙头/领先股列表")
    if candidate.industry:
        score += 4
        reasons.append("命中产业链报告公司映射")
    if candidate.manual:
        score += 2
        reasons.append("用户指定代码纳入复核")
    quote = (raw.get("external_data") or {}).get("quote") or {}
    pe = as_float(quote.get("pe_ttm") or quote.get("pe"), 0.0)
    if pe >= 120:
        score -= 5
        reasons.append("估值显著偏高，降级为重点复核项")
    if score5(raw.get("retail_sentiment"), 0.0) >= 4.5 and dims["capital"] < 4.0:
        score -= 4
        reasons.append("散户热度偏高但资金确认不足")
    exclusion = str(raw.get("exclusion_reason") or "")
    if exclusion:
        score -= 25
        reasons.append(exclusion)
    rating = str(raw.get("research_rating") or "")
    if rating == "风险回避":
        score -= 15
        reasons.append("综合评级为风险回避")
    score = round(max(0.0, min(100.0, score)), 2)
    if exclusion or rating == "风险回避":
        bucket = "reject"
    elif score >= 70 and "eligible_beneficiaries" in candidate.source_tags:
        bucket = "core"
    elif score >= 50:
        bucket = "watch"
    else:
        bucket = "reject"
    return score, {key: round(value, 2) for key, value in dims.items()}, reasons, bucket


def render_candidate(candidate: Candidate) -> dict[str, Any]:
    raw = candidate.raw
    score, dims, reasons, bucket = candidate_score(candidate)
    quote = (raw.get("external_data") or {}).get("quote") or {}
    return {
        "code": candidate.code,
        "name": candidate.name or raw.get("name") or "",
        "sector": candidate.sector or raw.get("sector") or "",
        "bucket": bucket,
        "score": score,
        "dimensions": dims,
        "research_rating": raw.get("research_rating") or "",
        "operation_tendency": raw.get("operation_tendency") or "",
        "source_tags": sorted(candidate.source_tags),
        "reasons": reasons or ["缺少强证据，仅保留为待验证样本"],
        "quote": {
            "latest": quote.get("latest"),
            "change_pct": quote.get("change_pct"),
            "market_cap": quote.get("market_cap") or quote.get("market_cap_billion"),
            "pe_ttm": quote.get("pe_ttm") or quote.get("pe"),
            "pb": quote.get("pb"),
        },
        "industry_matches": candidate.industry[:5],
        "missing_evidence": missing_evidence(candidate),
    }


def missing_evidence(candidate: Candidate) -> list[str]:
    raw = candidate.raw
    missing: list[str] = []
    if not raw:
        missing.append("缺少日报股票级评分")
    if not candidate.industry:
        missing.append("缺少产业链/卡口映射")
    if not (raw.get("external_data") or {}).get("quote"):
        missing.append("缺少本次归档行情/估值快照")
    if score5(raw.get("institutional_trend_score"), 0) < 3.5:
        missing.append("机构趋势确认不足")
    return missing


def refresh_quotes(rows: list[dict[str, Any]], limit: int) -> None:
    TMP.mkdir(parents=True, exist_ok=True)
    script = ROOT / ".agents/skills/china-stock-price-analysis/scripts/stock_analyze.py"
    for row in rows[:limit]:
        code = row["code"]
        dump = TMP / f"quote_{code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        cmd = [
            "uv",
            "run",
            "python",
            str(script.relative_to(ROOT)),
            code,
            "--industry",
            row.get("sector") or "传统制造业",
            "--dump-json",
            str(dump),
        ]
        result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=120)
        row["quote_refresh"] = {
            "command": " ".join(cmd),
            "returncode": result.returncode,
            "snapshot": str(dump.relative_to(ROOT)) if dump.exists() else "",
            "stderr": result.stderr[-1000:],
        }
        if result.returncode == 0 and dump.exists():
            apply_quote_refresh(row, dump)


def apply_quote_refresh(row: dict[str, Any], snapshot_path: Path) -> None:
    snapshot = read_json(snapshot_path)
    quote = snapshot.get("quote", snapshot)
    row["quote"].update(
        {
            "latest": quote.get("latest"),
            "change_pct": quote.get("change_pct"),
            "market_cap": quote.get("market_cap"),
            "pe_ttm": quote.get("pe_ttm"),
            "pb": quote.get("pb"),
        }
    )
    row["quote_refresh"]["source"] = quote.get("source", "")
    pe = as_float(quote.get("pe_ttm"), 0.0)
    if pe >= 120 and "刷新行情显示估值显著偏高" not in row["reasons"]:
        row["score"] = round(max(0.0, row["score"] - 5), 2)
        row["reasons"].append("刷新行情显示估值显著偏高")
    if pe >= 120 and "估值高位，需要盈利兑现复核" not in row["missing_evidence"]:
        row["missing_evidence"].append("估值高位，需要盈利兑现复核")
    if row["bucket"] == "core" and row["score"] < 70:
        row["bucket"] = "watch"


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# 综合选股池 {payload['date']}",
        "",
        f"- 主题: {payload.get('theme') or '全部'}",
        f"- 候选数: {payload['summary']['total']}，核心池: {payload['summary']['core']}，观察池: {payload['summary']['watch']}，排除: {payload['summary']['reject']}",
        "",
        "## 当日主线",
    ]
    for item in payload.get("mainlines", [])[:8]:
        lines.append(f"- {item.get('title') or item.get('sector')}: {item.get('impact_score', '')}")
    if not payload.get("mainlines"):
        lines.append("- 未匹配到主题主线，按股票/产业链证据补充筛选。")
    for bucket, title in (("core", "核心池"), ("watch", "观察池"), ("reject", "排除/待验证")):
        lines.extend(["", f"## {title}", "", "| 代码 | 名称 | 主题/行业 | 分数 | 证据 | 缺口 |", "| --- | --- | --- | ---: | --- | --- |"])
        rows = [row for row in payload["candidates"] if row["bucket"] == bucket]
        for row in rows:
            evidence = "；".join(row["reasons"][:3])
            missing = "；".join(row["missing_evidence"][:3]) or "无"
            lines.append(
                f"| {row['code']} | {row['name']} | {row['sector']} | {row['score']} | {evidence} | {missing} |"
            )
        if not rows:
            lines.append("| - | - | - | - | - | - |")
    lines.extend(["", "> 仅用于研究和复盘校准，不构成买卖建议。"])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an integrated A-share research stock pool.")
    parser.add_argument("--date", help="Archive date, e.g. 2026-06-26. Defaults to latest.")
    parser.add_argument("--theme", help="Filter by theme/sector/industry report topic.")
    parser.add_argument("--codes", help="Comma-separated stock codes to include for review.")
    parser.add_argument("--max-candidates", type=int, default=20)
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--output", help="Output path. Defaults to stdout.")
    parser.add_argument("--refresh-quotes", action="store_true", help="Call quick quote/valuation helper for top rows.")
    parser.add_argument("--quote-limit", type=int, default=5)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    date, archive = load_archive(args.date)
    codes = [part.strip() for part in (args.codes or "").split(",") if part.strip()]
    candidates = collect_candidates(archive, codes, args.theme)
    rendered = [render_candidate(candidate) for candidate in candidates.values()]
    rendered.sort(key=lambda row: ({"core": 2, "watch": 1, "reject": 0}[row["bucket"]], row["score"]), reverse=True)
    rendered = rendered[: max(1, args.max_candidates)]
    if args.refresh_quotes:
        refresh_quotes(rendered, args.quote_limit)
    payload = {
        "date": date,
        "theme": args.theme,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "total": len(rendered),
            "core": sum(1 for row in rendered if row["bucket"] == "core"),
            "watch": sum(1 for row in rendered if row["bucket"] == "watch"),
            "reject": sum(1 for row in rendered if row["bucket"] == "reject"),
        },
        "mainlines": mainline_matches(archive, args.theme),
        "candidates": rendered,
    }
    text = render_markdown(payload) if args.format == "markdown" else json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output)
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        print(str(output.relative_to(ROOT)))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
