#!/usr/bin/env python3
"""Shared public A-share data adapters used by local stock-analysis skills."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any
from urllib import error, request

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF_SECONDS = 0.5
TENCENT_QUOTE_URL = "https://qt.gtimg.cn/q={symbol}"
TENCENT_KLINE_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,,,{days},qfq"
EASTMONEY_QUOTE_URL = "https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields={fields}"

QUOTE_FIELD_INDEX = {
    "name": 1,
    "ticker": 2,
    "last_price": 3,
    "previous_close": 4,
    "timestamp": 30,
    "pct_change": 32,
    "volume": 36,
    "amount": 37,
    "turnover_rate": 38,
    "pe_ttm": 39,
    "float_market_cap_billion": 44,
    "total_market_cap_billion": 45,
    "pb": 46,
}
MIN_QUOTE_FIELD_COUNT = max(QUOTE_FIELD_INDEX.values()) + 1


@dataclass(frozen=True)
class TencentQuote:
    symbol: str
    ticker: str
    name: str
    last_price: float
    previous_close: float
    pct_change: float
    turnover_rate: float
    float_market_cap_billion: float
    total_market_cap_billion: float
    timestamp: str
    volume: float | None = None
    amount: float | None = None
    pe_ttm: float | None = None
    pb: float | None = None

    def to_snapshot(self) -> dict[str, float | str | None]:
        return {
            "source": "tencent_public_quote",
            "symbol": self.symbol,
            "name": self.name,
            "ticker": self.ticker,
            "last_price": self.last_price,
            "previous_close": self.previous_close,
            "pct_change": self.pct_change,
            "turnover_rate": self.turnover_rate,
            "float_market_cap_billion": self.float_market_cap_billion,
            "total_market_cap_billion": self.total_market_cap_billion,
            "volume": self.volume,
            "amount": self.amount,
            "pe_ttm": self.pe_ttm,
            "pb": self.pb,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class DailyBar:
    trade_date: str
    open_price: float
    close_price: float
    high_price: float
    low_price: float
    volume: float


def safe_float(value: Any) -> float | None:
    if value in (None, "", "--"):
        return None
    try:
        return float(str(value).strip().replace(",", "").replace("%", "").replace("亿", ""))
    except (TypeError, ValueError):
        return None


def raw_code(code: str) -> str:
    normalized = code.strip().lower().replace(".sz", "").replace(".sh", "").replace(".bj", "")
    if normalized.startswith(("sh", "sz", "bj")):
        normalized = normalized[2:]
    return normalized.zfill(6)


def a_share_symbol(code: str) -> str:
    normalized = raw_code(code)
    if normalized.startswith(("6", "9")):
        return f"sh{normalized}"
    if normalized.startswith(("4", "8")):
        return f"bj{normalized}"
    return f"sz{normalized}"


def eastmoney_secid(code: str) -> str:
    normalized = raw_code(code)
    market_id = "1" if normalized.startswith(("6", "9")) else "0"
    return f"{market_id}.{normalized}"


def http_get_text(
    url: str,
    *,
    encoding: str = "utf-8",
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    retries: int = DEFAULT_RETRIES,
    backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
) -> str:
    req = request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    last_exc: Exception | None = None
    for attempt in range(max(1, retries)):
        try:
            with request.urlopen(req, timeout=timeout) as response:
                return response.read().decode(encoding, errors="replace")
        except error.HTTPError:
            raise
        except (TimeoutError, OSError, error.URLError) as exc:
            last_exc = exc
            if attempt >= max(1, retries) - 1:
                break
            sleep_for = backoff_seconds * (attempt + 1)
            logger.warning("HTTP fetch failed (%s), retrying in %.2fs: %s", type(exc).__name__, sleep_for, url)
            time.sleep(sleep_for)
    assert last_exc is not None
    raise last_exc


def parse_tencent_quote(text: str, symbol: str) -> TencentQuote:
    marker = f"v_{symbol}="
    if marker not in text:
        raise ValueError(f"Tencent quote response did not include `{marker}`")
    body = text.split('="', 1)[1].rsplit('";', 1)[0]
    fields = body.split("~")
    if len(fields) < MIN_QUOTE_FIELD_COUNT:
        raise ValueError(f"Tencent quote response for `{symbol}` is missing fields")

    def required_number(field_name: str) -> float:
        value = safe_float(fields[QUOTE_FIELD_INDEX[field_name]])
        if value is None:
            raise ValueError(f"Tencent quote field `{field_name}` is not numeric")
        return value

    def optional_number(field_name: str) -> float | None:
        return safe_float(fields[QUOTE_FIELD_INDEX[field_name]])

    return TencentQuote(
        symbol=symbol,
        ticker=fields[QUOTE_FIELD_INDEX["ticker"]],
        name=fields[QUOTE_FIELD_INDEX["name"]],
        last_price=required_number("last_price"),
        previous_close=required_number("previous_close"),
        pct_change=required_number("pct_change"),
        turnover_rate=required_number("turnover_rate"),
        float_market_cap_billion=required_number("float_market_cap_billion"),
        total_market_cap_billion=required_number("total_market_cap_billion"),
        timestamp=fields[QUOTE_FIELD_INDEX["timestamp"]],
        volume=optional_number("volume"),
        amount=optional_number("amount"),
        pe_ttm=optional_number("pe_ttm"),
        pb=optional_number("pb"),
    )


def fetch_tencent_quote(code: str, *, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> TencentQuote:
    symbol = a_share_symbol(code)
    text = http_get_text(TENCENT_QUOTE_URL.format(symbol=symbol), encoding="gbk", timeout=timeout)
    return parse_tencent_quote(text, symbol)


def parse_tencent_kline(text: str, symbol: str) -> list[DailyBar]:
    payload = json.loads(text)
    series = payload.get("data", {}).get(symbol, {})
    # The K-line URL requests qfq (forward-adjusted) data, so only qfqday is
    # dimensionally consistent. Falling back to the unadjusted `day` series would
    # silently mix price scales and corrupt backtests.
    rows = series.get("qfqday")
    if rows is None:
        raise ValueError(f"Tencent kline response for `{symbol}` is missing forward-adjusted (qfqday) data")
    bars: list[DailyBar] = []
    for index, row in enumerate(rows):
        if len(row) < 6:
            raise ValueError(f"Tencent kline row {index} for `{symbol}` has too few fields")
        try:
            bars.append(
                DailyBar(
                    trade_date=str(row[0]),
                    open_price=float(row[1]),
                    close_price=float(row[2]),
                    high_price=float(row[3]),
                    low_price=float(row[4]),
                    volume=float(row[5]),
                )
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Tencent kline row {index} for `{symbol}` is not numeric") from exc
    return bars


def fetch_tencent_kline(code: str, days: int, *, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> list[DailyBar]:
    symbol = a_share_symbol(code)
    text = http_get_text(TENCENT_KLINE_URL.format(symbol=symbol, days=days), timeout=timeout)
    return parse_tencent_kline(text, symbol)


def fetch_eastmoney_quote(
    code: str,
    *,
    fields: str = "f43,f47,f48,f57,f58,f60,f116,f117,f162,f167,f168,f170",
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    url = EASTMONEY_QUOTE_URL.format(secid=eastmoney_secid(code), fields=fields)
    payload = json.loads(http_get_text(url, timeout=timeout))
    data = payload.get("data") if isinstance(payload, dict) else None
    return data if isinstance(data, dict) else {}
