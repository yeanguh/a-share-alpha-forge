#!/usr/bin/env python3
"""Build iWenCai-style A-share trend support stock pools.

The script uses public akshare data to approximate iWenCai conditions. Fields
that are specific to iWenCai, such as 3-day main fund inflow, are represented by
liquidity and volume-confirmation proxies.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import pandas as pd


CORE_THEME_CONCEPTS = [
    "CPO概念",
    "铜缆高速连接",
    "PCB",
    "玻璃基板",
    "存储芯片",
    "半导体概念",
    "AI芯片",
    "液冷概念",
]

SATELLITE_THEME_CONCEPTS = [
    "光刻机(胶)",
    "工业气体",
    "新材料",
    "MLCC",
]

CORE_CONCEPTS = CORE_THEME_CONCEPTS + SATELLITE_THEME_CONCEPTS


@dataclass(frozen=True)
class Strategy:
    key: str
    name: str
    source: str
    min_amount: float
    turnover_min: float
    turnover_max: float
    day_ret_min: float
    day_ret_max: float
    gap_min: float
    gap_max: float
    momentum20_min: float
    momentum20_max: float
    momentum5_max: float
    vol_ratio_min: float
    vol_ratio_max: float
    avg_range20_max: float | None
    ma20_heat_max: float
    high20_heat_max: float
    lower_shadow_min: float = 0.01
    require_quality: bool = False
    breakout: bool = False
    sort_key: str = "score"


STRATEGIES = {
    "main_theme": Strategy(
        key="main_theme",
        name="主线三日趋势承接",
        source="theme",
        min_amount=100_000_000,
        turnover_min=1.0,
        turnover_max=15.0,
        day_ret_min=-3.5,
        day_ret_max=8.0,
        gap_min=-3.0,
        gap_max=5.5,
        momentum20_min=0.0,
        momentum20_max=68.0,
        momentum5_max=15.0,
        vol_ratio_min=0.55,
        vol_ratio_max=3.20,
        avg_range20_max=12.5,
        ma20_heat_max=28.0,
        high20_heat_max=2.5,
    ),
    "broad_trend": Strategy(
        key="broad_trend",
        name="宽基趋势承接",
        source="all",
        min_amount=100_000_000,
        turnover_min=1.0,
        turnover_max=12.0,
        day_ret_min=-3.5,
        day_ret_max=8.0,
        gap_min=-3.0,
        gap_max=5.5,
        momentum20_min=0.0,
        momentum20_max=55.0,
        momentum5_max=12.0,
        vol_ratio_min=0.55,
        vol_ratio_max=3.20,
        avg_range20_max=11.0,
        ma20_heat_max=20.0,
        high20_heat_max=2.5,
    ),
    "fund_flow": Strategy(
        key="fund_flow",
        name="资金/量能承接近似",
        source="all",
        min_amount=100_000_000,
        turnover_min=1.0,
        turnover_max=12.0,
        day_ret_min=-3.5,
        day_ret_max=8.0,
        gap_min=-3.0,
        gap_max=5.5,
        momentum20_min=-3.0,
        momentum20_max=30.0,
        momentum5_max=12.0,
        vol_ratio_min=0.75,
        vol_ratio_max=3.20,
        avg_range20_max=None,
        ma20_heat_max=20.0,
        high20_heat_max=2.5,
        sort_key="amount_score",
    ),
    "quality_trend": Strategy(
        key="quality_trend",
        name="质量趋势",
        source="all",
        min_amount=100_000_000,
        turnover_min=0.8,
        turnover_max=10.0,
        day_ret_min=-3.5,
        day_ret_max=8.0,
        gap_min=-3.0,
        gap_max=5.5,
        momentum20_min=-3.0,
        momentum20_max=28.0,
        momentum5_max=10.0,
        vol_ratio_min=0.50,
        vol_ratio_max=3.00,
        avg_range20_max=None,
        ma20_heat_max=18.0,
        high20_heat_max=4.0,
        require_quality=True,
        sort_key="quality_score",
    ),
    "breakout_theme": Strategy(
        key="breakout_theme",
        name="主线突破增强",
        source="theme",
        min_amount=150_000_000,
        turnover_min=1.0,
        turnover_max=15.0,
        day_ret_min=-3.5,
        day_ret_max=8.0,
        gap_min=-3.0,
        gap_max=5.5,
        momentum20_min=0.0,
        momentum20_max=68.0,
        momentum5_max=15.0,
        vol_ratio_min=0.85,
        vol_ratio_max=3.50,
        avg_range20_max=None,
        ma20_heat_max=35.0,
        high20_heat_max=4.0,
        breakout=True,
    ),
}

RECOMMENDATION_ORDER = [
    "main_theme",
    "fund_flow",
    "broad_trend",
    "quality_trend",
    "breakout_theme",
]

RECOMMENDATION_WEIGHTS = {
    "main_theme": 500,
    "broad_trend": 30,
    "fund_flow": 35,
    "quality_trend": 25,
    "breakout_theme": 25,
}

HIGH_CONFIDENCE_PROFILE = {
    "name": "high_confidence_v1",
    "description": "回测校准后的高置信度二次过滤，目标是提高买入后三日内上涨概率。",
    "max_recommend_rank": 5,
    "max_strategy_rank": 8,
    "min_score": 3.8,
    "day_ret_min": -3.0,
    "day_ret_max": 8.0,
    "momentum5_min": -6.0,
    "momentum5_max": 3.0,
    "momentum20_min": 8.0,
    "momentum20_max": 35.0,
    "vol_ratio_min": 0.75,
    "vol_ratio_max": 1.90,
    "ma20_dist_min": 0.0,
    "ma20_dist_max": 28.0,
    "upper_shadow_max": 0.35,
    "close_position_min": 0.60,
}


def import_akshare():
    try:
        import akshare as ak  # type: ignore
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "akshare is not installed in this Python environment. "
            "Run with `uv run python ...` from the repository root."
        ) from exc
    return ak


def normalize_code(code: str) -> str:
    code = str(code).zfill(6)
    if code.startswith(("5", "6", "9")):
        return f"{code}.SH"
    return f"{code}.SZ"


def raw_code(code: str) -> str:
    return str(code).split(".")[0].zfill(6)


def is_allowed_code(code: str, include_star: bool) -> bool:
    raw = raw_code(code)
    if raw.startswith(("4", "8", "920")):
        return False
    if not include_star and raw.startswith(("688", "689")):
        return False
    return raw.startswith(("000", "001", "002", "003", "300", "301", "600", "601", "603", "605", "688", "689"))


def to_float(value, default: float = math.nan) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def fetch_spot(ak, include_star: bool) -> pd.DataFrame:
    df = ak.stock_zh_a_spot_em()
    df = df.rename(
        columns={
            "代码": "code",
            "名称": "name",
            "最新价": "price",
            "涨跌幅": "day_ret",
            "成交额": "amount",
            "换手率": "turnover",
            "市盈率-动态": "pe",
            "市净率": "pb",
            "总市值": "market_cap",
        }
    )
    keep = ["code", "name", "price", "day_ret", "amount", "turnover", "pe", "pb", "market_cap"]
    df = df[[col for col in keep if col in df.columns]].copy()
    df["code"] = df["code"].map(normalize_code)
    for col in ["price", "day_ret", "amount", "turnover", "pe", "pb", "market_cap"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df[df["code"].map(lambda x: is_allowed_code(x, include_star))]
    df = df[~df["name"].astype(str).str.contains("ST|退", regex=True, na=False)]
    return df.drop_duplicates("code").reset_index(drop=True)


def fetch_theme_codes(
    ak, concepts: list[str]
) -> tuple[set[str], dict[str, list[str]], dict[str, str], list[str]]:
    theme_codes: set[str] = set()
    code_concepts: dict[str, list[str]] = {}
    code_theme_tier: dict[str, str] = {}
    failed: list[str] = []
    for concept in concepts:
        tier = "core" if concept in CORE_THEME_CONCEPTS else "satellite"
        try:
            cons = ak.stock_board_concept_cons_em(symbol=concept)
        except Exception:
            failed.append(concept)
            continue
        if cons is None or cons.empty or "代码" not in cons.columns:
            failed.append(concept)
            continue
        for code in cons["代码"].dropna().map(normalize_code).tolist():
            theme_codes.add(code)
            code_concepts.setdefault(code, []).append(concept)
            if tier == "core" or code not in code_theme_tier:
                code_theme_tier[code] = tier
    return theme_codes, code_concepts, code_theme_tier, failed


def fetch_hist(ak, code: str, cache_dir: Path, use_cache: bool) -> pd.DataFrame | None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{raw_code(code)}.csv"
    if use_cache and cache_file.exists():
        try:
            df = pd.read_csv(cache_file)
            if len(df) >= 80:
                return df
        except Exception:
            pass

    try:
        df = ak.stock_zh_a_hist(symbol=raw_code(code), period="daily", adjust="qfq")
    except Exception:
        return None
    if df is None or df.empty:
        return None
    try:
        df.to_csv(cache_file, index=False)
    except Exception:
        pass
    return df


def calc_metrics(code: str, hist: pd.DataFrame) -> dict | None:
    if hist is None or hist.empty or len(hist) < 60:
        return None
    df = hist.tail(80).copy()
    for col in ["开盘", "收盘", "最高", "最低", "成交量", "成交额", "振幅", "涨跌幅", "换手率"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["开盘", "收盘", "最高", "最低", "成交量"])
    if len(df) < 60:
        return None

    close = df["收盘"]
    open_ = df["开盘"]
    high = df["最高"]
    low = df["最低"]
    volume = df["成交量"]

    price = float(close.iloc[-1])
    prev_close = float(close.iloc[-2])
    day_ret = price / prev_close * 100 - 100
    ma5 = float(close.tail(5).mean())
    ma10 = float(close.tail(10).mean())
    ma20 = float(close.tail(20).mean())
    ma60 = float(close.tail(60).mean())
    high20 = float(high.tail(20).max())
    low5 = float(low.tail(5).min())
    vol5 = float(volume.tail(5).mean())
    vol20 = float(volume.tail(20).mean())
    vol_ratio = vol5 / max(vol20, 1.0)
    avg_range20 = float(((high.tail(20) - low.tail(20)) / close.tail(20)).mean() * 100)
    momentum20 = price / float(close.iloc[-20]) * 100 - 100
    momentum5 = price / float(close.iloc[-5]) * 100 - 100
    today_range = max(float(high.iloc[-1] - low.iloc[-1]), 0.01)
    close_position = (price - float(low.iloc[-1])) / today_range
    upper_shadow = (float(high.iloc[-1]) - price) / today_range
    lower_shadow = (min(float(open_.iloc[-1]), price) - float(low.iloc[-1])) / today_range
    gap = float(open_.iloc[-1]) / prev_close * 100 - 100
    ma10_dist = price / ma10 * 100 - 100
    ma20_dist = price / ma20 * 100 - 100
    high20_dist = price / high20 * 100 - 100

    return {
        "code": code,
        "trade_date": str(df["日期"].iloc[-1]) if "日期" in df.columns else "",
        "price": price,
        "day_ret": day_ret,
        "ma5": ma5,
        "ma10": ma10,
        "ma20": ma20,
        "ma60": ma60,
        "low5": low5,
        "high20": high20,
        "vol_ratio": vol_ratio,
        "avg_range20": avg_range20,
        "momentum20": momentum20,
        "momentum5": momentum5,
        "close_position": close_position,
        "upper_shadow": upper_shadow,
        "lower_shadow": lower_shadow,
        "gap": gap,
        "ma10_dist": ma10_dist,
        "ma20_dist": ma20_dist,
        "high20_dist": high20_dist,
    }


def passes_strategy(row: dict, strategy: Strategy) -> bool:
    price = row["price"]
    ma5 = row["ma5"]
    ma10 = row["ma10"]
    ma20 = row["ma20"]
    ma60 = row["ma60"]

    if row["amount"] < strategy.min_amount:
        return False
    if not (strategy.turnover_min <= row["turnover"] <= strategy.turnover_max):
        return False
    if not (strategy.day_ret_min <= row["day_ret"] <= strategy.day_ret_max):
        return False
    if not (strategy.gap_min <= row["gap"] <= strategy.gap_max):
        return False
    if not (strategy.momentum20_min <= row["momentum20"] <= strategy.momentum20_max):
        return False
    if row["momentum5"] > strategy.momentum5_max:
        return False
    if not (strategy.vol_ratio_min <= row["vol_ratio"] <= strategy.vol_ratio_max):
        return False
    if strategy.avg_range20_max is not None and row["avg_range20"] > strategy.avg_range20_max:
        return False
    if row["ma20_dist"] > strategy.ma20_heat_max:
        return False
    if row["high20_dist"] > strategy.high20_heat_max:
        return False
    if row["upper_shadow"] > 0.52:
        return False
    if row["lower_shadow"] < strategy.lower_shadow_min:
        return False

    trend_ok = price > ma20 and ma10 > ma20 * 0.995 and ma20 > ma60 * 0.985
    support_ok = row["low"] <= ma10 * 1.045 or row["low5"] <= ma10 * 1.055 or price <= ma10 * 1.055
    recover_ok = price >= ma5 * (0.995 if strategy.breakout else 0.99)
    close_ok = row["close_position"] >= (0.56 if strategy.breakout else 0.50)
    breakout_ok = price >= row["high20"] * 0.965 and price <= ma10 * 1.105

    if strategy.breakout:
        if not (trend_ok and breakout_ok and recover_ok and close_ok):
            return False
    else:
        if not (trend_ok and support_ok and recover_ok and close_ok):
            return False

    if strategy.require_quality:
        if not (0 < row["pe"] < 35 and 0 < row["pb"] < 4):
            return False
    return True


def score_row(row: dict) -> dict:
    trend_score = row["ma20_dist"] / 100
    support_multiplier = 5 if row.get("is_core_theme") else 8
    support_score = max(0.0, 1 - abs(row["ma10_dist"] / 100) * support_multiplier)
    breakout_score = 0.35 if row.get("is_core_theme") and row["high20_dist"] >= -3.5 else 0.0
    kline_score = row["close_position"] + row["lower_shadow"] - row["upper_shadow"]
    volume_score = 1 - min(abs(row["vol_ratio"] - 1.15), 1.5) / 1.5
    momentum_score = max(0.0, min(row["momentum20"] / 100, 0.30)) * 1.35
    low_vol_score = max(0.0, 0.095 - row["avg_range20"] / 100)
    momentum_heat_line = 0.32 if row.get("is_core_theme") else 0.20
    heat_penalty = (
        max(row["day_ret"] / 100 - 0.045, 0) * 4
        + max(row["momentum20"] / 100 - momentum_heat_line, 0) * 2
    )
    theme_bonus = 0.90 if row.get("is_core_theme") else 0.25 if row.get("is_satellite_theme") else 0.0
    base_score = (
        trend_score
        + support_score
        + breakout_score
        + kline_score
        + volume_score
        + momentum_score
        + low_vol_score
        + theme_bonus
        - heat_penalty
    )
    amount_score = math.log10(max(row["amount"], 1)) + row["vol_ratio"] + max(row["momentum20"], -10) / 20
    quality_score = base_score + max(0.0, 35 - row["pe"]) / 35 + max(0.0, 4 - row["pb"]) / 4
    row["score"] = round(base_score, 6)
    row["amount_score"] = round(amount_score, 6)
    row["quality_score"] = round(quality_score, 6)
    return row


def enrich_one(args) -> dict | None:
    ak, code, spot_row, cache_dir, use_cache = args
    hist = fetch_hist(ak, code, cache_dir, use_cache)
    metrics = calc_metrics(code, hist) if hist is not None else None
    if metrics is None:
        return None
    if hist is not None and not hist.empty:
        tail = hist.tail(1).iloc[0]
        metrics["low"] = to_float(tail.get("最低"))
    row = dict(spot_row)
    row.update(metrics)
    return score_row(row)


def coarse_filter(spot: pd.DataFrame, strategy_keys: list[str], theme_codes: set[str]) -> pd.DataFrame:
    min_amount = min(STRATEGIES[key].min_amount for key in strategy_keys)
    min_turnover = min(STRATEGIES[key].turnover_min for key in strategy_keys)
    max_turnover = max(STRATEGIES[key].turnover_max for key in strategy_keys)
    df = spot.copy()
    df = df[df["amount"] >= min_amount * 0.8]
    df = df[df["turnover"].between(min_turnover * 0.5, max_turnover * 1.2)]
    df = df[df["day_ret"].between(-6.0, 10.5)]
    need_theme = all(STRATEGIES[key].source == "theme" for key in strategy_keys)
    if need_theme:
        df = df[df["code"].isin(theme_codes)]
    return df.sort_values("amount", ascending=False)


def fetch_etf_hist(ak, symbol: str) -> pd.DataFrame | None:
    try:
        df = ak.fund_etf_hist_em(symbol=symbol, period="daily", adjust="qfq")
    except Exception:
        return None
    if df is None or df.empty:
        return None
    return df


def is_etf_trend_up(ak, symbol: str) -> bool | None:
    df = fetch_etf_hist(ak, symbol)
    if df is None or len(df) < 120:
        return None
    df = df.tail(150).copy()
    if "收盘" not in df.columns:
        return None
    close = pd.to_numeric(df["收盘"], errors="coerce").dropna()
    if len(close) < 120:
        return None
    price = float(close.iloc[-1])
    ma20 = float(close.tail(20).mean())
    ma60 = float(close.tail(60).mean())
    ma120 = float(close.tail(120).mean())
    return price > ma120 and ma20 > ma60 * 0.99


def build_etf_overlay(ak) -> dict:
    """Mirror supermind_broad_etf_combo_v73 as a market-environment note."""

    cyb_up = is_etf_trend_up(ak, "159915")
    zz500_up = is_etf_trend_up(ak, "510500")
    if cyb_up is None or zz500_up is None:
        return {
            "available": False,
            "note": "ETF trend overlay unavailable; stock-pool ranking was generated without v73 broad-index weights.",
        }

    cyb_weight = 0.50 if cyb_up else 0.15
    zz500_weight = 0.30 if zz500_up else 0.20
    hs300_weight = max(0.0, 1.0 - cyb_weight - zz500_weight)
    return {
        "available": True,
        "source": "supermind_broad_etf_combo_v73",
        "signals": {
            "159915.SZ": bool(cyb_up),
            "510500.SH": bool(zz500_up),
            "510310.SH": True,
        },
        "target_weights": {
            "159915.SZ": round(cyb_weight, 2),
            "510500.SH": round(zz500_weight, 2),
            "510310.SH": round(hs300_weight, 2),
        },
        "note": "创业板 ETF 趋势向上给 50%，否则 15%；中证500 ETF 趋势向上给 30%，否则 20%；余额给沪深300 ETF。",
    }


def build_pools(args: argparse.Namespace) -> dict:
    ak = import_akshare()
    strategy_keys = [key.strip() for key in args.strategies.split(",") if key.strip()]
    unknown = [key for key in strategy_keys if key not in STRATEGIES]
    if unknown:
        raise SystemExit(f"Unknown strategies: {', '.join(unknown)}")

    spot = fetch_spot(ak, include_star=args.include_star)
    theme_codes, code_concepts, code_theme_tier, failed_concepts = fetch_theme_codes(ak, CORE_CONCEPTS)
    candidates = coarse_filter(spot, strategy_keys, theme_codes)
    if args.max_stocks:
        candidates = candidates.head(args.max_stocks)

    records = candidates.to_dict("records")
    tasks = []
    cache_dir = Path(args.output_dir) / "cache" / "hist"
    for record in records:
        code = record["code"]
        spot_row = {
            "code": code,
            "name": record.get("name", ""),
            "amount": to_float(record.get("amount"), 0.0),
            "turnover": to_float(record.get("turnover"), 0.0),
            "pe": to_float(record.get("pe"), math.nan),
            "pb": to_float(record.get("pb"), math.nan),
            "market_cap": to_float(record.get("market_cap"), math.nan),
            "is_theme": code in theme_codes,
            "is_core_theme": code_theme_tier.get(code) == "core",
            "is_satellite_theme": code_theme_tier.get(code) == "satellite",
            "theme_tier": code_theme_tier.get(code, ""),
            "concepts": code_concepts.get(code, []),
        }
        tasks.append((ak, code, spot_row, cache_dir, not args.no_cache))

    enriched: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        for row in executor.map(enrich_one, tasks):
            if row is not None:
                enriched.append(row)

    pools: dict[str, list[dict]] = {}
    for key in strategy_keys:
        strategy = STRATEGIES[key]
        rows = []
        for row in enriched:
            if strategy.source == "theme" and not row["is_theme"]:
                continue
            if passes_strategy(row, strategy):
                rows.append(row.copy())
        rows.sort(key=lambda item: item.get(strategy.sort_key, item.get("score", 0)), reverse=True)
        rows = rows[: args.top]
        for rank, row in enumerate(rows, start=1):
            row["rank"] = rank
            row["strategy"] = key
            row["strategy_name"] = strategy.name
        pools[key] = rows

    result = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "data_note": "akshare public data; main fund inflow is approximated by liquidity/volume/trend conditions; ETF overlay mirrors v73 broad-index trend weights.",
        "strategies": {key: STRATEGIES[key].name for key in strategy_keys},
        "failed_concepts": failed_concepts,
        "theme_design": {
            "core": CORE_THEME_CONCEPTS,
            "satellite": SATELLITE_THEME_CONCEPTS,
        },
        "market_overlay": build_etf_overlay(ak),
        "input_counts": {
            "spot": int(len(spot)),
            "theme_codes": int(len(theme_codes)),
            "coarse_candidates": int(len(candidates)),
            "enriched": int(len(enriched)),
        },
        "pools": pools,
    }
    result["recommendations"] = build_recommendations(result, limit=args.recommend_top)
    result["high_confidence_profile"] = HIGH_CONFIDENCE_PROFILE
    result["high_confidence_recommendations"] = build_high_confidence_recommendations(
        result["recommendations"],
        limit=args.high_confidence_top,
    )
    return result


def build_recommendations(result: dict, limit: int = 5) -> list[dict]:
    """Rank candidates by the skill's recommended strategy order.

    The main theme pool is the primary source. Other pools add confirmation
    points, so a candidate that appears in several strategies can outrank a
    single-pool candidate with a slightly higher raw score.
    """

    candidate_map: dict[str, dict] = {}
    hits_by_code: dict[str, list[dict]] = {}
    pools = result.get("pools", {})

    for strategy_key in RECOMMENDATION_ORDER:
        rows = pools.get(strategy_key, [])
        for row in rows:
            code = row["code"]
            candidate_map.setdefault(code, row)
            hits_by_code.setdefault(code, []).append(
                {
                    "strategy": strategy_key,
                    "strategy_name": STRATEGIES[strategy_key].name,
                    "rank": row.get("rank", 999),
                }
            )

    rows = []
    for code, row in candidate_map.items():
        hits = hits_by_code.get(code, [])
        has_main_theme = any(hit["strategy"] == "main_theme" for hit in hits)
        if not has_main_theme and pools.get("main_theme"):
            continue

        recommendation_score = 0.0
        for hit in hits:
            strategy_key = hit["strategy"]
            rank = hit["rank"]
            weight = RECOMMENDATION_WEIGHTS.get(strategy_key, 0)
            if strategy_key == "main_theme":
                recommendation_score += weight - rank * 20
            else:
                recommendation_score += max(weight - rank, 1)
        if row.get("is_core_theme"):
            recommendation_score += 90
        elif row.get("is_satellite_theme"):
            recommendation_score += 25
        recommendation_score += min(float(row.get("score", 0.0)), 4.0) * 5

        recommendation = row.copy()
        recommendation["recommendation_score"] = round(recommendation_score, 3)
        recommendation["strategy_hits"] = hits
        recommendation["hit_count"] = len(hits)
        recommendation["reason"] = build_recommendation_reason(recommendation)
        rows.append(recommendation)

    rows.sort(key=lambda item: item["recommendation_score"], reverse=True)
    for rank, row in enumerate(rows[:limit], start=1):
        row["recommend_rank"] = rank
    return rows[:limit]


def is_high_confidence_recommendation(row: dict) -> bool:
    profile = HIGH_CONFIDENCE_PROFILE
    checks = [
        row.get("recommend_rank", 999) <= profile["max_recommend_rank"],
        row.get("rank", 999) <= profile["max_strategy_rank"],
        row.get("score", 0.0) >= profile["min_score"],
        profile["day_ret_min"] <= row.get("day_ret", 0.0) <= profile["day_ret_max"],
        profile["momentum5_min"] <= row.get("momentum5", 0.0) <= profile["momentum5_max"],
        profile["momentum20_min"] <= row.get("momentum20", 0.0) <= profile["momentum20_max"],
        profile["vol_ratio_min"] <= row.get("vol_ratio", 0.0) <= profile["vol_ratio_max"],
        profile["ma20_dist_min"] <= row.get("ma20_dist", 0.0) <= profile["ma20_dist_max"],
        row.get("upper_shadow", 1.0) <= profile["upper_shadow_max"],
        row.get("close_position", 0.0) >= profile["close_position_min"],
    ]
    return all(checks)


def build_high_confidence_recommendations(recommendations: list[dict], limit: int = 5) -> list[dict]:
    rows = [row.copy() for row in recommendations if is_high_confidence_recommendation(row)]
    for rank, row in enumerate(rows[:limit], start=1):
        row["high_confidence_rank"] = rank
        row["high_confidence_profile"] = HIGH_CONFIDENCE_PROFILE["name"]
        row["reason"] = row.get("reason", "") + "；满足高置信度三日上涨过滤"
    return rows[:limit]


def build_recommendation_reason(row: dict) -> str:
    hit_names = [hit["strategy_name"] for hit in row.get("strategy_hits", [])]
    concepts = ",".join(row.get("concepts", [])[:3]) or "非主题补充"
    reasons = [
        "命中" + "、".join(hit_names),
        "概念=" + concepts,
        "20日涨幅%.2f%%" % row.get("momentum20", 0.0),
        "量比%.2f" % row.get("vol_ratio", 0.0),
        "换手%.2f%%" % row.get("turnover", 0.0),
    ]
    day_ret = row.get("day_ret", 0.0)
    if day_ret <= 4.5:
        reasons.append("当日涨幅%.2f%%，追高压力相对可控" % day_ret)
    else:
        reasons.append("当日涨幅%.2f%%，需等分时承接确认" % day_ret)
    return "；".join(reasons)


def write_outputs(result: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_file = output_dir / "stock_pools.json"
    json_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# 同花顺问财趋势承接股票池",
        "",
        f"- 生成时间：{result['generated_at']}",
        f"- 数据说明：{result['data_note']}",
        f"- 输入统计：{result['input_counts']}",
    ]
    if result.get("failed_concepts"):
        lines.append(f"- 未匹配概念板块：{', '.join(result['failed_concepts'])}")
    overlay = result.get("market_overlay", {})
    if overlay.get("available"):
        weights = overlay.get("target_weights", {})
        lines.append(
            "- 宽基ETF v73：159915={cyb:.0%}，510500={zz500:.0%}，510310={hs300:.0%}".format(
                cyb=weights.get("159915.SZ", 0.0),
                zz500=weights.get("510500.SH", 0.0),
                hs300=weights.get("510310.SH", 0.0),
            )
        )
    elif overlay:
        lines.append(f"- 宽基ETF v73：{overlay.get('note')}")
    lines.append("")

    recommendations = result.get("recommendations", [])
    lines.extend(["## 综合推荐 Top 5", ""])
    if recommendations:
        lines.append("| 推荐 | 代码 | 名称 | 推荐分 | 命中策略 | 关键理由 |")
        lines.append("| ---: | --- | --- | ---: | --- | --- |")
        for row in recommendations:
            hit_names = "、".join(hit["strategy_name"] for hit in row.get("strategy_hits", []))
            lines.append(
                "| {rank} | {code} | {name} | {recommendation_score:.1f} | {hits} | {reason} |".format(
                    rank=row["recommend_rank"],
                    code=row["code"],
                    name=row["name"],
                    recommendation_score=row["recommendation_score"],
                    hits=hit_names,
                    reason=row["reason"],
                )
            )
        lines.append("")
        pd.DataFrame(recommendations).to_csv(
            output_dir / "recommendations.csv", index=False, encoding="utf-8-sig"
        )
        (output_dir / "recommendations.md").write_text(
            "\n".join(
                [
                    "# 综合推荐 Top 5",
                    "",
                    "| 推荐 | 代码 | 名称 | 推荐分 | 理由 |",
                    "| ---: | --- | --- | ---: | --- |",
                    *[
                        "| {rank} | {code} | {name} | {score:.1f} | {reason} |".format(
                            rank=row["recommend_rank"],
                            code=row["code"],
                            name=row["name"],
                            score=row["recommendation_score"],
                            reason=row["reason"],
                        )
                        for row in recommendations
                    ],
                    "",
                ]
            ),
            encoding="utf-8",
        )
    else:
        lines.extend(["无综合推荐。", ""])

    high_confidence = result.get("high_confidence_recommendations", [])
    profile = result.get("high_confidence_profile", {})
    lines.extend(["## 高置信度三日上涨池", ""])
    if profile:
        lines.append(f"- 配置：{profile.get('name')}；{profile.get('description')}")
        lines.append(
            "- 条件：推荐Top5、主线排名<=8、score>=3.8、20日涨幅8%-35%、5日涨幅-6%-3%、"
            "量比0.75-1.90、距20日线0%-28%、上影线<=35%、收盘位于当日振幅60%以上。"
        )
        lines.append("")
    if high_confidence:
        lines.append("| 高置信 | 代码 | 名称 | 推荐分 | 关键理由 |")
        lines.append("| ---: | --- | --- | ---: | --- |")
        for row in high_confidence:
            lines.append(
                "| {rank} | {code} | {name} | {recommendation_score:.1f} | {reason} |".format(
                    rank=row["high_confidence_rank"],
                    code=row["code"],
                    name=row["name"],
                    recommendation_score=row["recommendation_score"],
                    reason=row["reason"],
                )
            )
        lines.append("")
        pd.DataFrame(high_confidence).to_csv(
            output_dir / "high_confidence_recommendations.csv",
            index=False,
            encoding="utf-8-sig",
        )
    else:
        lines.extend(["今日无高置信度信号；按回测口径应降低出手频率。", ""])

    for key, rows in result["pools"].items():
        name = result["strategies"][key]
        lines.extend([f"## {name}", "", f"候选数：{len(rows)}", ""])
        if not rows:
            lines.extend(["无候选。", ""])
            continue
        lines.append("| 排名 | 代码 | 名称 | 分数 | 收盘 | 当日% | 20日% | 跳空% | 量比 | 换手% | 主题 | 概念 |")
        lines.append("| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |")
        for row in rows[:20]:
            concepts = ",".join(row.get("concepts", [])[:3])
            lines.append(
                "| {rank} | {code} | {name} | {score:.3f} | {price:.2f} | {day_ret:.2f} | "
                "{momentum20:.2f} | {gap:.2f} | {vol_ratio:.2f} | {turnover:.2f} | {tier} | {concepts} |".format(
                    rank=row["rank"],
                    code=row["code"],
                    name=row["name"],
                    score=row["score"],
                    price=row["price"],
                    day_ret=row["day_ret"],
                    momentum20=row["momentum20"],
                    gap=row.get("gap", 0.0),
                    vol_ratio=row["vol_ratio"],
                    turnover=row["turnover"],
                    tier=row.get("theme_tier", ""),
                    concepts=concepts,
                )
            )
        lines.append("")

        df = pd.DataFrame(rows)
        if not df.empty:
            df.to_csv(output_dir / f"{key}.csv", index=False, encoding="utf-8-sig")

    (output_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strategies",
        default="main_theme,broad_trend,fund_flow,quality_trend,breakout_theme",
        help="Comma-separated strategy keys.",
    )
    parser.add_argument("--output-dir", default="local/stock_pools/latest", help="Output directory.")
    parser.add_argument("--top", type=int, default=30, help="Max rows per strategy.")
    parser.add_argument("--recommend-top", type=int, default=5, help="Top recommendations to write.")
    parser.add_argument("--high-confidence-top", type=int, default=5, help="Top high-confidence recommendations to write.")
    parser.add_argument("--max-stocks", type=int, default=500, help="Max coarse candidates to enrich; 0 means no limit.")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent history fetch workers.")
    parser.add_argument("--include-star", action="store_true", help="Include STAR market stocks.")
    parser.add_argument("--no-cache", action="store_true", help="Disable local history cache.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.max_stocks == 0:
        args.max_stocks = None
    result = build_pools(args)
    write_outputs(result, Path(args.output_dir))
    print(Path(args.output_dir).resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
