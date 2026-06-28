#!/usr/bin/env python3
"""A-share quote and valuation helper with module-level fallback sources.

Realtime quote path:
1. mootdx/Tongdaxin for realtime price, order book, and K-line style fields.
2. Tencent public quote for no-key realtime quote and market-cap fields.
3. Eastmoney public quote for PE/PB/market-cap valuation fields.

The script keeps paid or credentialed sources out of the default path. If a
source fails, the report records the failure and continues with the next source.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.a_share_data import (
    a_share_symbol,
    fetch_eastmoney_quote,
    fetch_tencent_quote,
    raw_code,
    safe_float,
)


INDUSTRY_PE_RANGES = {
    "消费电子龙头": (20, 30),
    "白酒龙头": (25, 35),
    "半导体设备": (30, 45),
    "传统制造业": (10, 18),
    "银行": (5, 12),
    "地产": (5, 15),
    "医药": (20, 35),
    "新能源": (25, 40),
}

INDUSTRY_PB_RANGES = {
    "消费电子龙头": (3, 5),
    "白酒龙头": (5, 10),
    "半导体设备": (4, 8),
    "传统制造业": (1, 3),
    "银行": (0.5, 1.5),
    "地产": (0.5, 2),
}


@dataclass
class SourceStatus:
    source: str
    status: str
    detail: str


@dataclass
class QuoteSnapshot:
    code: str
    name: str = ""
    latest: float | None = None
    previous_close: float | None = None
    change_pct: float | None = None
    volume: float | None = None
    amount: float | None = None
    market_cap: float | None = None
    float_market_cap: float | None = None
    pe_ttm: float | None = None
    pb: float | None = None
    timestamp: str = ""
    source: str = ""
    sources: list[SourceStatus] = field(default_factory=list)


def tencent_symbol(code: str) -> str:
    return a_share_symbol(code)


def apply_mootdx_quote(snapshot: QuoteSnapshot) -> SourceStatus:
    try:
        from mootdx.quotes import Quotes

        client = Quotes.factory(market="std")
        try:
            frame = client.quotes([raw_code(snapshot.code)])
        finally:
            client.close()
        if frame is None or frame.empty:
            return SourceStatus("mootdx", "failed", "empty quote frame")
        row = frame.iloc[0].to_dict()
        snapshot.latest = safe_float(row.get("price")) or snapshot.latest
        snapshot.previous_close = safe_float(row.get("last_close")) or snapshot.previous_close
        snapshot.volume = safe_float(row.get("vol")) or snapshot.volume
        snapshot.amount = safe_float(row.get("amount")) or snapshot.amount
        snapshot.timestamp = str(row.get("servertime") or snapshot.timestamp)
        if snapshot.latest is not None and snapshot.previous_close:
            snapshot.change_pct = (snapshot.latest - snapshot.previous_close) / snapshot.previous_close * 100
        snapshot.source = snapshot.source or "mootdx"
        return SourceStatus("mootdx", "available", "quote/order-book fields fetched")
    except Exception as exc:  # noqa: BLE001
        return SourceStatus("mootdx", "failed", f"{type(exc).__name__}: {exc}")


def apply_tencent_quote(snapshot: QuoteSnapshot) -> SourceStatus:
    try:
        quote = fetch_tencent_quote(snapshot.code)
        snapshot.name = snapshot.name or quote.name
        snapshot.latest = snapshot.latest or quote.last_price
        snapshot.previous_close = snapshot.previous_close or quote.previous_close
        snapshot.change_pct = snapshot.change_pct if snapshot.change_pct is not None else quote.pct_change
        snapshot.volume = snapshot.volume or quote.volume
        snapshot.amount = snapshot.amount or quote.amount
        snapshot.float_market_cap = snapshot.float_market_cap or quote.float_market_cap_billion * 100000000
        snapshot.market_cap = snapshot.market_cap or quote.total_market_cap_billion * 100000000
        snapshot.pe_ttm = snapshot.pe_ttm or quote.pe_ttm
        snapshot.pb = snapshot.pb or quote.pb
        snapshot.timestamp = snapshot.timestamp or quote.timestamp
        snapshot.source = snapshot.source or "tencent"
        return SourceStatus("tencent", "available", "public quote fields fetched")
    except Exception as exc:  # noqa: BLE001
        return SourceStatus("tencent", "failed", f"{type(exc).__name__}: {exc}")


def apply_eastmoney_quote(snapshot: QuoteSnapshot) -> SourceStatus:
    try:
        data = fetch_eastmoney_quote(snapshot.code)
        if not data:
            return SourceStatus("eastmoney", "failed", "empty quote payload")
        snapshot.name = snapshot.name or str(data.get("f58") or "")
        snapshot.latest = snapshot.latest or ((safe_float(data.get("f43")) or 0) / 100)
        snapshot.previous_close = snapshot.previous_close or ((safe_float(data.get("f60")) or 0) / 100)
        snapshot.change_pct = snapshot.change_pct if snapshot.change_pct is not None else ((safe_float(data.get("f170")) or 0) / 100)
        snapshot.volume = snapshot.volume or safe_float(data.get("f47"))
        snapshot.amount = snapshot.amount or safe_float(data.get("f48"))
        snapshot.market_cap = snapshot.market_cap or safe_float(data.get("f116"))
        snapshot.float_market_cap = snapshot.float_market_cap or safe_float(data.get("f117"))
        snapshot.pe_ttm = snapshot.pe_ttm or ((safe_float(data.get("f162")) or 0) / 100)
        snapshot.pb = snapshot.pb or ((safe_float(data.get("f167")) or 0) / 100)
        snapshot.source = snapshot.source or "eastmoney"
        return SourceStatus("eastmoney", "available", "valuation fields fetched")
    except Exception as exc:  # noqa: BLE001
        return SourceStatus("eastmoney", "failed", f"{type(exc).__name__}: {exc}")


def load_quote(code: str, json_path: str | None = None) -> QuoteSnapshot:
    if json_path:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "quote" in data:
            data = data["quote"]
        return QuoteSnapshot(
            code=str(data.get("code") or data.get("thscode") or code),
            name=str(data.get("name") or ""),
            latest=safe_float(data.get("latest") or data.get("last_price")),
            previous_close=safe_float(data.get("previous_close")),
            change_pct=safe_float(data.get("change_pct") or data.get("changeRatio")),
            volume=safe_float(data.get("volume")),
            amount=safe_float(data.get("amount")),
            market_cap=safe_float(data.get("market_cap") or data.get("mv")),
            float_market_cap=safe_float(data.get("float_market_cap")),
            pe_ttm=safe_float(data.get("pe_ttm")),
            pb=safe_float(data.get("pb") or data.get("pbr_lf")),
            timestamp=str(data.get("timestamp") or data.get("time") or ""),
            source=str(data.get("source") or "json"),
        )

    snapshot = QuoteSnapshot(code=raw_code(code))
    for fetcher in (apply_mootdx_quote, apply_tencent_quote, apply_eastmoney_quote):
        status = fetcher(snapshot)
        snapshot.sources.append(status)
    if snapshot.latest is None:
        details = "; ".join(f"{s.source}: {s.detail}" for s in snapshot.sources)
        raise RuntimeError(f"No quote source available for {code}: {details}")
    return snapshot


def judge_multiple(value: float | None, industry: str, ranges: dict[str, tuple[float, float]], label: str) -> str:
    if value is None:
        return f"{label}: 缺少数据"
    if industry not in ranges:
        return f"{label} {value:.2f}: 行业 {industry} 无预设区间"
    low, high = ranges[industry]
    if value < low:
        return f"{label} {value:.2f}: 低于参考区间 {low}~{high}"
    if value <= high:
        return f"{label} {value:.2f}: 位于参考区间 {low}~{high}"
    return f"{label} {value:.2f}: 高于参考区间 {low}~{high}"


def expected_valuation(eps_expected: float | None, industry: str) -> dict[str, float]:
    if eps_expected is None or industry not in INDUSTRY_PE_RANGES:
        return {}
    low_pe, high_pe = INDUSTRY_PE_RANGES[industry]
    return {
        "low": eps_expected * low_pe,
        "high": eps_expected * high_pe,
        "mid": eps_expected * (low_pe + high_pe) / 2,
    }


def print_report(snapshot: QuoteSnapshot, industry: str, eps_expected: float | None, ebitda: float | None, net_debt: float, consensus_target: float | None) -> None:
    print(f"# {snapshot.code} {snapshot.name} 估值分析")
    print()
    print(f"- 行业口径: {industry}")
    print(f"- 最新价: {snapshot.latest:.2f} 元")
    if snapshot.change_pct is not None:
        print(f"- 涨跌幅: {snapshot.change_pct:.2f}%")
    if snapshot.amount is not None:
        print(f"- 成交额: {snapshot.amount / 100000000:.2f} 亿元")
    if snapshot.market_cap is not None:
        print(f"- 总市值: {snapshot.market_cap / 100000000:.2f} 亿元")
    print(f"- 数据主源: {snapshot.source or 'fallback'}")
    if snapshot.timestamp:
        print(f"- 数据时间: {snapshot.timestamp}")
    print()
    print("## 数据源状态")
    for status in snapshot.sources:
        print(f"- {status.source}: {status.status} ({status.detail})")
    print()
    print("## 相对估值")
    print(f"- {judge_multiple(snapshot.pe_ttm, industry, INDUSTRY_PE_RANGES, 'PE TTM')}")
    print(f"- {judge_multiple(snapshot.pb, industry, INDUSTRY_PB_RANGES, 'PB')}")
    val_range = expected_valuation(eps_expected, industry)
    if val_range and snapshot.latest is not None:
        print()
        print("## 业绩预期法")
        print(f"- 合理区间: {val_range['low']:.2f}~{val_range['high']:.2f} 元，中枢 {val_range['mid']:.2f} 元")
        print(f"- 当前价相对中枢: {(snapshot.latest / val_range['mid'] - 1) * 100:.1f}%")
    if ebitda and snapshot.market_cap:
        ev = snapshot.market_cap + net_debt
        print()
        print("## EV/EBITDA")
        print(f"- EV/EBITDA: {ev / ebitda:.2f}x")
    if consensus_target and snapshot.latest:
        print()
        print("## 一致目标价")
        print(f"- 目标价 {consensus_target:.2f} 元，对应空间 {(consensus_target / snapshot.latest - 1) * 100:.1f}%")


def main() -> int:
    parser = argparse.ArgumentParser(description="A股股价与估值分析")
    parser.add_argument("code", help="股票代码，如 002475.SZ 或 600519")
    parser.add_argument("--industry", default="消费电子龙头", help="行业分类")
    parser.add_argument("--eps-expected", type=float, help="一致预期EPS")
    parser.add_argument("--ebitda", type=float, help="年度EBITDA（亿元）")
    parser.add_argument("--net-debt", type=float, default=0, help="净负债（亿元）")
    parser.add_argument("--consensus-target", type=float, help="券商一致目标价")
    parser.add_argument("--json", help="从JSON文件读取行情数据")
    parser.add_argument("--dump-json", help="额外保存标准化行情快照")
    args = parser.parse_args()

    snapshot = load_quote(args.code, args.json)
    if args.dump_json:
        with open(args.dump_json, "w", encoding="utf-8") as f:
            json.dump(asdict(snapshot), f, ensure_ascii=False, indent=2)
    print_report(
        snapshot,
        args.industry,
        args.eps_expected,
        args.ebitda * 100000000 if args.ebitda else None,
        args.net_debt * 100000000,
        args.consensus_target,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
