#!/usr/bin/env python3
"""Integrated A-share stock-selection orchestrator.

The script ranks research candidates from local archives first. It can optionally
call the existing quote/valuation helper for a narrowed list, but it does not
refresh network data by default.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
TMP = ROOT / "tmp" / "integrated-selection"
IWENCAI_SCRIPT = ROOT / ".agents/skills/iwencai-trend-stock-pool/scripts/build_stock_pools.py"
IWENCAI_DEFAULT_STRATEGIES = "main_theme,broad_trend,fund_flow,quality_trend,breakout_theme"
IWENCAI_DEFAULT_SPOT_CSV = ROOT.parent / "a-data" / "stock_list.csv"
IWENCAI_DEFAULT_THEME_CACHE = (
    ROOT
    / "local/reviews/backtests/iwencai_trend_stock_pool_2026-06-01_2026-06-23/theme_codes.json"
)


def raw_code(value: object) -> str:
    code = str(value or "").strip().upper()
    code = code.replace(".SH", "").replace(".SZ", "").replace(".BJ", "")
    code = re.sub(r"^(SH|SZ|BJ)", "", code)
    digits = re.sub(r"\D", "", code)
    return digits.zfill(6) if digits else ""


def split_codes_arg(value: str | None) -> list[str]:
    parts = [part.strip() for part in re.split(r"[,，\s]+", value or "") if part.strip()]
    codes: list[str] = []
    for part in parts:
        digits = re.sub(r"\D", "", part)
        if len(digits) > 6 and len(digits) % 6 == 0:
            codes.extend(digits[idx : idx + 6] for idx in range(0, len(digits), 6))
        else:
            codes.append(part)
    return codes


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


def selection_today() -> str:
    return os.environ.get("A_STOCK_SELECTION_TODAY") or datetime.now().strftime("%Y-%m-%d")


def close_review_path(date: str) -> Path:
    return ROOT / "local" / date / "close_review.json"


def load_close_review(date: str) -> dict[str, Any] | None:
    path = close_review_path(date)
    if not path.exists():
        return None
    try:
        payload = read_json(path)
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def load_archive_for_selection(requested_date: str | None) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """Load the best archive plus market context for the requested/current date.

    If today's or requested day's full assembled mainline is absent, use the
    newest assembled archive but attach that day's close review when available.
    This keeps one-click selection from silently relying on stale market
    direction after the close review has already recorded what actually changed.
    """

    target_date = requested_date or selection_today()
    exact_path = ROOT / "local" / target_date / "assembled.json"
    if exact_path.exists():
        selected = target_date
        archive = read_json(exact_path)
        context_source = "requested_archive" if requested_date else "current_archive"
    else:
        selected = latest_archive_date()
        archive = read_json(ROOT / "local" / selected / "assembled.json")
        context_source = "latest_archive_fallback"

    close_review = load_close_review(target_date)
    archive_has_mainlines = bool(mainline_matches(archive, None))
    use_close_review = bool(close_review) and (selected != target_date or not archive_has_mainlines)
    if use_close_review and selected != target_date:
        warning = f"未找到 {target_date} 的 assembled 主线，已退回 {selected} 归档，并使用 {target_date} 收盘复盘校准。"
    elif selected != target_date:
        warning = f"未找到 {target_date} 的 assembled 主线或收盘复盘，已退回 {selected} 归档；当前市场状态可能滞后。"
    elif not archive_has_mainlines and not close_review:
        warning = f"{target_date} 归档缺少主线，且未找到收盘复盘；结果主要依赖趋势池和股票级证据。"
    else:
        warning = ""

    market_context = {
        "requested_date": target_date,
        "archive_date": selected,
        "source": "close_review_fallback" if use_close_review else context_source,
        "close_review_used": use_close_review,
        "close_review_date": target_date if close_review else "",
        "warning": warning,
    }
    if close_review:
        market_context["close_review"] = summarize_close_review(close_review)
    return selected, archive, market_context


def summarize_close_review(review: dict[str, Any]) -> dict[str, Any]:
    forecast = review.get("direction_forecast") or {}
    fund_flow = review.get("fund_flow_review") or {}
    if isinstance(forecast, str):
        forecast_summary = forecast
    else:
        forecast_summary = str(forecast.get("actual_direction") or forecast.get("early_direction") or "")
    return {
        "review_time": review.get("review_time") or "",
        "actual_market_summary": review.get("actual_market_summary") or "",
        "direction_hit": review.get("direction_hit"),
        "direction": forecast_summary,
        "fund_flow": fund_flow.get("actual") or fund_flow.get("post_close_judgment") or "",
        "sector_hits": [
            {
                "sector": item.get("sector") or "",
                "hit": item.get("hit"),
                "hit_level": item.get("hit_level") or "",
                "actual_move": item.get("actual_move") or item.get("reason") or "",
            }
            for item in (review.get("sector_hits") or [])[:10]
            if isinstance(item, dict)
        ],
    }


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


def close_review_mainlines(market_context: dict[str, Any], theme: str | None) -> list[dict[str, Any]]:
    if not market_context.get("close_review_used"):
        return []
    review = market_context.get("close_review") or {}
    rows: list[dict[str, Any]] = []
    summary = str(review.get("actual_market_summary") or "")
    if summary and contains_theme(summary, theme):
        rows.append(
            {
                "title": "收盘复盘市场状态",
                "impact_score": "close-review",
                "direction": review.get("direction") or "",
                "summary": summary,
            }
        )
    fund_flow = str(review.get("fund_flow") or "")
    if fund_flow and contains_theme(fund_flow, theme):
        rows.append(
            {
                "title": "收盘复盘资金流",
                "impact_score": "close-review",
                "direction": "fund_flow",
                "summary": fund_flow,
            }
        )
    for item in review.get("sector_hits") or []:
        sector = str(item.get("sector") or "")
        text = " ".join(str(item.get(key) or "") for key in ("sector", "hit_level", "actual_move"))
        if sector and contains_theme(text, theme):
            rows.append(
                {
                    "title": f"收盘复盘：{sector}",
                    "sector": sector,
                    "impact_score": item.get("hit_level") or ("命中" if item.get("hit") else "未命中"),
                    "direction": "positive" if item.get("hit") else "negative",
                    "summary": item.get("actual_move") or "",
                }
            )
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
    iwencai: list[dict[str, Any]] = field(default_factory=list)
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


def load_iwencai_data(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    if "pools" not in payload:
        raise ValueError(f"not an iwencai trend stock-pool JSON: {path}")
    return payload


def resolve_existing_path(value: str | None, default: Path | None = None) -> Path | None:
    path = Path(value) if value else default
    if path is None:
        return None
    if not path.is_absolute():
        path = ROOT / path
    return path if path.exists() else None


def run_iwencai_stock_pool(args: argparse.Namespace) -> dict[str, Any] | None:
    if args.skip_iwencai:
        return None
    if args.iwencai_json:
        path = Path(args.iwencai_json)
        if not path.is_absolute():
            path = ROOT / path
        return {
            "data": load_iwencai_data(path),
            "status": "loaded",
            "json": str(path.relative_to(ROOT)),
        }

    output_dir = Path(args.iwencai_output_dir) if args.iwencai_output_dir else (
        TMP / f"iwencai-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    command = [
        "uv",
        "run",
        "python",
        str(IWENCAI_SCRIPT.relative_to(ROOT)),
        "--strategies",
        args.iwencai_strategies,
        "--max-stocks",
        str(args.iwencai_max_stocks),
        "--top",
        str(args.iwencai_top),
        "--recommend-top",
        str(args.iwencai_recommend_top),
        "--high-confidence-top",
        str(args.iwencai_high_confidence_top),
        "--workers",
        str(args.iwencai_workers),
        "--output-dir",
        str(output_dir),
    ]
    if args.iwencai_no_cache:
        command.append("--no-cache")
    spot_csv = resolve_existing_path(args.iwencai_spot_csv, IWENCAI_DEFAULT_SPOT_CSV)
    if spot_csv:
        command.extend(["--spot-csv", str(spot_csv)])
    theme_cache = resolve_existing_path(args.iwencai_theme_cache_json, IWENCAI_DEFAULT_THEME_CACHE)
    if theme_cache:
        command.extend(["--theme-cache-json", str(theme_cache)])
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=args.iwencai_timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "timeout",
            "command": " ".join(command),
            "error": f"timed out after {exc.timeout}s",
            "data": None,
        }
    json_path = output_dir / "stock_pools.json"
    if result.returncode != 0 or not json_path.exists():
        return {
            "status": "failed",
            "command": " ".join(command),
            "returncode": result.returncode,
            "stdout": result.stdout[-2000:],
            "stderr": result.stderr[-2000:],
            "data": None,
        }
    return {
        "status": "generated",
        "command": " ".join(command),
        "output_dir": str(output_dir.relative_to(ROOT)),
        "json": str(json_path.relative_to(ROOT)),
        "data": load_iwencai_data(json_path),
    }


def iwencai_strength(entries: list[dict[str, Any]]) -> float:
    strength = 0.0
    for entry in entries:
        if entry.get("source") == "high_confidence":
            strength = max(strength, 5.0)
        if entry.get("source") == "recommendation":
            strength = max(strength, min(5.0, as_float(entry.get("recommendation_score"), 0.0) / 140.0))
        strength = max(strength, min(5.0, as_float(entry.get("score"), 0.0)))
    return round(strength, 2)


def add_iwencai_candidate(candidates: dict[str, Candidate], item: dict[str, Any], source: str) -> None:
    code = raw_code(item.get("code"))
    if not code:
        return
    candidate = candidates.setdefault(code, Candidate(code=code))
    candidate.source_tags.add("iwencai-trend-stock-pool")
    concepts = item.get("concepts") or []
    candidate.name = candidate.name or str(item.get("name") or "")
    candidate.sector = candidate.sector or "、".join(str(concept) for concept in concepts[:3])
    entry = {
        "source": source,
        "strategy": item.get("strategy") or "",
        "strategy_name": item.get("strategy_name") or "",
        "rank": item.get("rank"),
        "recommend_rank": item.get("recommend_rank"),
        "high_confidence_rank": item.get("high_confidence_rank"),
        "recommendation_score": item.get("recommendation_score"),
        "score": item.get("score"),
        "reason": item.get("reason") or "",
        "concepts": concepts,
        "theme_tier": item.get("theme_tier") or "",
        "metrics": {
            "day_ret": item.get("day_ret"),
            "momentum20": item.get("momentum20"),
            "momentum5": item.get("momentum5"),
            "vol_ratio": item.get("vol_ratio"),
            "turnover": item.get("turnover"),
            "ma20_dist": item.get("ma20_dist"),
            "upper_shadow": item.get("upper_shadow"),
            "close_position": item.get("close_position"),
        },
    }
    candidate.iwencai.append(entry)


def add_iwencai_candidates(candidates: dict[str, Candidate], iwencai_data: dict[str, Any] | None, theme: str | None) -> None:
    if not iwencai_data:
        return
    for item in iwencai_data.get("recommendations", []) or []:
        if theme and not contains_theme(" ".join([str(item.get("name") or ""), " ".join(item.get("concepts") or [])]), theme):
            continue
        add_iwencai_candidate(candidates, item, "recommendation")
    for item in iwencai_data.get("high_confidence_recommendations", []) or []:
        if theme and not contains_theme(" ".join([str(item.get("name") or ""), " ".join(item.get("concepts") or [])]), theme):
            continue
        add_iwencai_candidate(candidates, item, "high_confidence")
    for strategy, rows in (iwencai_data.get("pools") or {}).items():
        for item in rows or []:
            if theme and not contains_theme(" ".join([str(item.get("name") or ""), " ".join(item.get("concepts") or [])]), theme):
                continue
            enriched = dict(item)
            enriched.setdefault("strategy", strategy)
            add_iwencai_candidate(candidates, enriched, "strategy_pool")


def collect_candidates(
    archive: dict[str, Any],
    codes: list[str],
    theme: str | None,
    iwencai_data: dict[str, Any] | None = None,
) -> dict[str, Candidate]:
    candidates: dict[str, Candidate] = {}
    add_iwencai_candidates(candidates, iwencai_data, theme)
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
        "iwencai": iwencai_strength(candidate.iwencai),
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
        + dims["iwencai"] * 3.4
    )
    reasons: list[str] = []
    high_confidence_entries = [entry for entry in candidate.iwencai if entry.get("source") == "high_confidence"]
    recommendation_entries = [entry for entry in candidate.iwencai if entry.get("source") == "recommendation"]
    if high_confidence_entries:
        score += 8
        reasons.append("通过问财趋势承接高置信度过滤")
    if recommendation_entries:
        best_rank = min(int(entry.get("recommend_rank") or 999) for entry in recommendation_entries)
        score += max(1, 6 - min(best_rank, 5))
        reasons.append(f"问财趋势承接综合推荐第{best_rank}名")
    if candidate.iwencai:
        strategy_names = sorted(
            {
                str(entry.get("strategy_name") or entry.get("strategy") or "")
                for entry in candidate.iwencai
                if entry.get("strategy_name") or entry.get("strategy")
            }
        )
        if strategy_names:
            score += min(4, len(strategy_names))
            reasons.append("命中趋势策略：" + "、".join(strategy_names[:4]))
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
    elif score >= 70 and (
        "eligible_beneficiaries" in candidate.source_tags
        or high_confidence_entries
    ):
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
        "iwencai_matches": candidate.iwencai[:8],
        "missing_evidence": missing_evidence(candidate),
    }


def missing_evidence(candidate: Candidate) -> list[str]:
    raw = candidate.raw
    missing: list[str] = []
    if not raw:
        if candidate.iwencai:
            missing.append("缺少日报事件/基本面交叉验证")
        else:
            missing.append("缺少日报股票级评分")
    if not candidate.industry:
        missing.append("缺少产业链/卡口映射")
    if not (raw.get("external_data") or {}).get("quote"):
        missing.append("缺少本次归档行情/估值快照")
    if score5(raw.get("institutional_trend_score"), 0) < 3.5:
        missing.append("机构趋势确认不足")
    if not candidate.iwencai:
        missing.append("缺少问财趋势承接信号")
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
    row["missing_evidence"] = [
        item for item in row["missing_evidence"] if item != "缺少本次归档行情/估值快照"
    ]
    pe = as_float(quote.get("pe_ttm"), 0.0)
    if pe >= 120 and "刷新行情显示估值显著偏高" not in row["reasons"]:
        row["score"] = round(max(0.0, row["score"] - 5), 2)
        row["reasons"].append("刷新行情显示估值显著偏高")
    if pe >= 120 and "估值高位，需要盈利兑现复核" not in row["missing_evidence"]:
        row["missing_evidence"].append("估值高位，需要盈利兑现复核")
    if row["bucket"] == "core" and row["score"] < 70:
        row["bucket"] = "watch"
    if (
        row["bucket"] == "core"
        and pe >= 120
        and "eligible_beneficiaries" not in row.get("source_tags", [])
    ):
        row["bucket"] = "watch"


def _close_review_hit_bonus(hit: object, hit_level: str) -> float:
    text = str(hit_level or "")
    if hit is True:
        if "强" in text:
            return 3.0
        if "部分" in text or "边缘" in text:
            return 1.5
        return 2.0
    if hit is False:
        if "部分" in text or "个股" in text:
            return -1.5
        return -3.0
    return 0.0


def apply_market_context(rows: list[dict[str, Any]], market_context: dict[str, Any]) -> None:
    """Use post-close review signals to calibrate candidate ranking.

    The close review is intentionally a modest overlay: it should correct stale
    mainline assumptions when today's assembled report is missing, while not
    overruling hard stock-level trend/valuation gates.
    """

    if not market_context.get("close_review_used"):
        return
    review_date = str(market_context.get("close_review_date") or market_context.get("requested_date") or "")
    close_review = load_close_review(review_date) if review_date else None
    if not close_review:
        return

    stock_hits: dict[str, dict[str, Any]] = {
        raw_code(item.get("ticker") or item.get("code")): item
        for item in close_review.get("stock_hits", []) or []
        if isinstance(item, dict) and raw_code(item.get("ticker") or item.get("code"))
    }
    sector_hits = [
        item
        for item in close_review.get("sector_hits", []) or []
        if isinstance(item, dict) and item.get("sector")
    ]

    for row in rows:
        adjustments: list[str] = []
        delta = 0.0
        code = raw_code(row.get("code"))
        stock_hit = stock_hits.get(code)
        if stock_hit:
            hit_level = str(stock_hit.get("hit_level") or "")
            stock_delta = _close_review_hit_bonus(stock_hit.get("hit"), hit_level)
            delta += stock_delta
            actual = stock_hit.get("actual_move") or stock_hit.get("reason") or ""
            label = "个股命中" if stock_delta > 0 else "个股未命中" if stock_delta < 0 else "个股复盘"
            adjustments.append(f"{review_date}收盘复盘{label}：{hit_level or actual}")

        sector_text = " ".join(
            str(value or "")
            for value in [row.get("sector"), row.get("name"), " ".join(row.get("reasons") or [])]
        )
        for item in sector_hits:
            sector = str(item.get("sector") or "")
            if not sector or not contains_theme(sector_text, sector):
                continue
            sector_delta = _close_review_hit_bonus(item.get("hit"), str(item.get("hit_level") or "")) * 0.7
            delta += sector_delta
            label = "板块确认" if sector_delta > 0 else "板块转弱" if sector_delta < 0 else "板块复盘"
            adjustments.append(f"{review_date}收盘复盘{label}：{sector} {item.get('hit_level') or ''}".strip())
            break

        if not adjustments:
            continue
        row["market_context_evidence"] = adjustments[:4]
        row["score"] = round(max(0.0, min(100.0, as_float(row.get("score"), 0.0) + delta)), 2)
        row.setdefault("reasons", [])
        for adjustment in adjustments[:2]:
            if adjustment not in row["reasons"]:
                row["reasons"].append(adjustment)
        if row["bucket"] == "core" and row["score"] < 70:
            row["bucket"] = "watch"
        elif row["bucket"] == "reject" and row["score"] >= 50:
            row["bucket"] = "watch"
        elif row["bucket"] == "watch" and row["score"] >= 75 and (
            "eligible_beneficiaries" in row.get("source_tags", [])
            or any(entry.get("source") == "high_confidence" for entry in row.get("iwencai_matches", []))
        ):
            row["bucket"] = "core"


def _committee_member(name: str, score: float, stance: str, comment: str) -> dict[str, Any]:
    return {
        "name": name,
        "score": round(max(0.0, min(5.0, score)), 2),
        "stance": stance,
        "comment": comment,
    }


def investment_committee_review(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Deterministic local investment-committee review for selected candidates."""

    reviews: list[dict[str, Any]] = []
    for row in rows:
        dims = row.get("dimensions") or {}
        quote = row.get("quote") or {}
        pe = as_float(quote.get("pe_ttm"), 0.0)
        source_count = len(row.get("source_tags") or [])
        missing_count = len(row.get("missing_evidence") or [])
        archive_backed = any(tag in row.get("source_tags", []) for tag in ("eligible_beneficiaries", "leading_stocks", "stocks"))

        technical_score = (
            as_float(dims.get("trend"), 2.5) * 0.34
            + as_float(dims.get("volume"), 2.5) * 0.26
            + as_float(dims.get("iwencai"), 0.0) * 0.40
        )
        fundamental_score = (
            as_float(dims.get("event"), 2.0) * 0.28
            + as_float(dims.get("beneficiary"), 2.5) * 0.26
            + as_float(dims.get("institutional"), 2.2) * 0.20
            + as_float(dims.get("industry"), 0.0) * 0.26
        )
        valuation_penalty = 1.0 if pe >= 200 else 0.6 if pe >= 120 else 0.25 if pe >= 80 else 0.0
        risk_score = max(0.0, as_float(dims.get("risk_control"), 2.5) - valuation_penalty)
        portfolio_score = min(5.0, as_float(row.get("score"), 0.0) / 20.0 + min(source_count, 4) * 0.18 - missing_count * 0.12)

        members = [
            _committee_member(
                "趋势委员",
                technical_score,
                "支持" if technical_score >= 3.6 else "谨慎" if technical_score >= 2.8 else "反对",
                "趋势和量能共振较好" if technical_score >= 3.6 else "趋势承接仍需确认",
            ),
            _committee_member(
                "产业/基本面委员",
                fundamental_score,
                "支持" if fundamental_score >= 3.6 else "谨慎" if fundamental_score >= 2.6 else "反对",
                "具备事件、受益股或产业链交叉证据" if fundamental_score >= 3.6 else "基本面或产业链证据不足",
            ),
            _committee_member(
                "风险委员",
                risk_score,
                "支持" if risk_score >= 3.4 else "谨慎" if risk_score >= 2.4 else "反对",
                "风险和估值约束可接受" if risk_score >= 3.4 else "估值、热度或证据缺口需要压低优先级",
            ),
            _committee_member(
                "组合委员",
                portfolio_score,
                "支持" if portfolio_score >= 3.6 else "谨慎" if portfolio_score >= 2.8 else "反对",
                "可作为组合观察仓候选" if portfolio_score >= 3.6 else "需要补齐证据或等待更优排序",
            ),
        ]
        average = round(sum(member["score"] for member in members) / len(members), 2)
        vetoes = [member["name"] for member in members if member["stance"] == "反对"]
        if pe >= 200 and not archive_backed:
            vetoes.append("估值高位且缺少日报/产业链交叉验证")

        if vetoes:
            action = "暂不进入核心池"
            advice = "保留观察或剔除复核，先补估值、财务兑现和产业链证据。"
        elif row.get("bucket") == "core" and average >= 3.7:
            action = "核心观察"
            advice = "允许进入核心观察池，但仅在回撤、量能和风险条件同步满足后再评估。"
        elif average >= 3.0:
            action = "观察等待"
            advice = "保留在观察池，等待行情复核、产业链证据或机构趋势确认。"
        else:
            action = "剔除复核"
            advice = "当前证据不足，不建议进入本轮重点名单。"

        reviews.append(
            {
                "code": row.get("code") or "",
                "name": row.get("name") or "",
                "bucket": row.get("bucket") or "",
                "committee_score": average,
                "action": action,
                "advice": advice,
                "vetoes": vetoes,
                "members": members,
            }
        )
        row["committee_review"] = reviews[-1]

    return {
        "mode": "local_deterministic_committee",
        "description": "趋势、产业/基本面、风险、组合四类委员基于已采集证据做本地规则评审；不调用 LLM，不构成买卖建议。",
        "summary": {
            "core_observe": sum(1 for item in reviews if item["action"] == "核心观察"),
            "watch_wait": sum(1 for item in reviews if item["action"] == "观察等待"),
            "defer_or_reject": sum(1 for item in reviews if item["action"] in {"暂不进入核心池", "剔除复核"}),
        },
        "reviews": reviews,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    market_context = payload.get("market_context") or {}
    lines = [
        f"# 综合选股池 {payload['date']}",
        "",
        f"- 主题: {payload.get('theme') or '全部'}",
        f"- 候选数: {payload['summary']['total']}，核心池: {payload['summary']['core']}，观察池: {payload['summary']['watch']}，排除: {payload['summary']['reject']}",
        f"- 市场上下文: {market_context.get('source') or 'archive'}；请求日期 {market_context.get('requested_date') or payload['date']}；归档日期 {market_context.get('archive_date') or payload['date']}",
        "",
        "## 当日主线",
    ]
    if market_context.get("warning"):
        lines.append(f"- {market_context['warning']}")
    for item in payload.get("mainlines", [])[:8]:
        summary = item.get("summary")
        suffix = f"；{summary}" if summary else ""
        lines.append(f"- {item.get('title') or item.get('sector')}: {item.get('impact_score', '')}{suffix}")
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
    committee = payload.get("committee_review") or {}
    if committee:
        lines.extend(
            [
                "",
                "## 投资委员会评审",
                "",
                "| 代码 | 名称 | 投委会评分 | 决议 | 建议 | 否决/待补 |",
                "| --- | --- | ---: | --- | --- | --- |",
            ]
        )
        for item in committee.get("reviews", []):
            vetoes = "；".join(item.get("vetoes") or []) or "无"
            lines.append(
                f"| {item.get('code', '')} | {item.get('name', '')} | {item.get('committee_score', '')} | {item.get('action', '')} | {item.get('advice', '')} | {vetoes} |"
            )
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
    parser.add_argument("--skip-iwencai", action="store_true", help="Do not run iWenCai trend stock-pool first.")
    parser.add_argument("--iwencai-json", help="Reuse an existing iwencai stock_pools.json instead of running it.")
    parser.add_argument("--iwencai-output-dir", help="Output directory for the generated iWenCai trend pool.")
    parser.add_argument("--iwencai-strategies", default=IWENCAI_DEFAULT_STRATEGIES)
    parser.add_argument("--iwencai-max-stocks", type=int, default=300)
    parser.add_argument("--iwencai-top", type=int, default=20)
    parser.add_argument("--iwencai-recommend-top", type=int, default=8)
    parser.add_argument("--iwencai-high-confidence-top", type=int, default=8)
    parser.add_argument("--iwencai-workers", type=int, default=8)
    parser.add_argument("--iwencai-timeout", type=int, default=900)
    parser.add_argument("--iwencai-no-cache", action="store_true")
    parser.add_argument("--iwencai-spot-csv", help="Local spot snapshot CSV to pass to the iWenCai pool builder.")
    parser.add_argument("--iwencai-theme-cache-json", help="Cached theme constituents JSON for the iWenCai pool builder.")
    parser.add_argument(
        "--skip-fresh-check",
        action="store_true",
        help="跳过执行时的候选数据新鲜度检查/补齐闸门。",
    )
    parser.add_argument(
        "--no-fresh-backfill",
        action="store_true",
        help="闸门仍检查新鲜度，但缺失/过期时不联网补数（仅告警，降级到磁盘现有数据）。",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    date, archive, market_context = load_archive_for_selection(args.date)
    codes = split_codes_arg(args.codes)
    iwencai_result = run_iwencai_stock_pool(args)
    iwencai_data = iwencai_result.get("data") if iwencai_result else None
    candidates = collect_candidates(archive, codes, args.theme, iwencai_data)
    if not getattr(args, "skip_fresh_check", False):
        _ensure_candidate_data_fresh(list(candidates.keys()), args)
    rendered = [render_candidate(candidate) for candidate in candidates.values()]
    apply_market_context(rendered, market_context)
    rendered.sort(key=lambda row: ({"core": 2, "watch": 1, "reject": 0}[row["bucket"]], row["score"]), reverse=True)
    max_candidates = max(1, args.max_candidates)
    manual_rows = [row for row in rendered if "manual_codes" in row.get("source_tags", [])]
    selected: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    for row in manual_rows + rendered:
        code = row.get("code") or ""
        if code in seen_codes:
            continue
        if len(selected) >= max_candidates and "manual_codes" not in row.get("source_tags", []):
            continue
        selected.append(row)
        seen_codes.add(code)
        if len(selected) >= max_candidates and len(seen_codes) >= len({item.get("code") for item in manual_rows}):
            break
    rendered = selected
    if args.refresh_quotes:
        refresh_quotes(rendered, args.quote_limit)
    committee_review = investment_committee_review(rendered)
    payload = {
        "date": date,
        "theme": args.theme,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "market_context": market_context,
        "summary": {
            "total": len(rendered),
            "core": sum(1 for row in rendered if row["bucket"] == "core"),
            "watch": sum(1 for row in rendered if row["bucket"] == "watch"),
            "reject": sum(1 for row in rendered if row["bucket"] == "reject"),
        },
        "mainlines": close_review_mainlines(market_context, args.theme) + mainline_matches(archive, args.theme),
        "iwencai": {
            key: value
            for key, value in (iwencai_result or {"status": "skipped"}).items()
            if key != "data"
        },
        "candidates": rendered,
        "committee_review": committee_review,
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


def _ensure_candidate_data_fresh(candidate_codes: list[str], args: argparse.Namespace) -> None:
    """执行时新鲜度闸门：对候选码检查本地档案，缺失/过期先补数再继续。

    作用范围（重要）：本闸门在 collect_candidates 之后运行，只保证后续
    本地取价/估值环节（如 --refresh-quotes 调用的 refresh_quotes）用到的
    数据新鲜。它【不覆盖】上游 iWenCai 子进程——iWenCai 由 build_stock_pools.py
    自身的 local-first 增量补齐负责，本轮其评分/候选不会因这里补数而重算。
    复用 scripts/ensure_fresh.py；任何失败只告警、绝不阻断选股（降级到磁盘现有数据）。
    """
    scripts_dir = ROOT / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    try:
        from ensure_fresh import ensure_fresh
    except Exception as exc:  # pragma: no cover - defensive import guard
        print(f"[integrated-selection] freshness gate unavailable: {exc}", flush=True)
        return
    codes = [code for code in (candidate_codes or []) if code]
    if not codes:
        return
    # 联网补数由独立开关控制，不再复用 skip_iwencai：
    # 跳过 iWenCai 不等于要离线，缺失历史增量仍可能需要补齐。
    allow_network = not getattr(args, "no_fresh_backfill", False)
    try:
        ensure_fresh(codes, end_date=getattr(args, "date", None), allow_network=allow_network)
    except Exception as exc:  # pragma: no cover
        print(f"[integrated-selection] freshness backfill skipped: {exc}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
