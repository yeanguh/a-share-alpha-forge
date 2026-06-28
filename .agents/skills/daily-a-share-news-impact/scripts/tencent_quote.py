#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.a_share_data import (
    DEFAULT_TIMEOUT_SECONDS,
    DailyBar,
    TencentQuote as Quote,
    a_share_symbol,
    fetch_tencent_kline,
    fetch_tencent_quote,
    http_get_text,
    parse_tencent_kline,
    parse_tencent_quote,
)

fetch_quote = fetch_tencent_quote
fetch_kline = fetch_tencent_kline
parse_quote = parse_tencent_quote
parse_kline = parse_tencent_kline


__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "DailyBar",
    "Quote",
    "a_share_symbol",
    "fetch_kline",
    "fetch_quote",
    "http_get_text",
    "parse_kline",
    "parse_quote",
]
