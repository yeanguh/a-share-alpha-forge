#!/usr/bin/env python3
"""Local-first A-share daily history loader with incremental top-up.

Reads the full historical archive under ``a-data/hist/<code>.csv`` first and only
fetches the *missing tail* from akshare, appending it back into the archive so the
archive stays authoritative and disk usage stops growing from repeated full downloads.

Archive口径 (must not be mixed):
- One CSV per 6-digit code, UTF-8 with BOM.
- Columns: 日期,股票代码,开盘,收盘,最高,最低,成交量,成交额,振幅,涨跌幅,涨跌额,换手率
- Rows sorted ascending by 日期.
- **Unadjusted** daily bars (adjust=""), so a plain tail-append is口径-safe
  (no qfq rebasing). Increments are fetched with the same adjust="" basis.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

HIST_COLUMNS = [
    "日期", "股票代码", "开盘", "收盘", "最高", "最低",
    "成交量", "成交额", "振幅", "涨跌幅", "涨跌额", "换手率",
]
DATE_COL = "日期"
CODE_COL = "股票代码"
ARCHIVE_ADJUST = ""  # archive is unadjusted; keep increments consistent

# a-analysis/  <- parents[2] of this file (scripts/ -> stock-analysis/ -> a-analysis/)
_A_ANALYSIS_ROOT = Path(__file__).resolve().parents[2]


def data_root() -> Path:
    """Return the a-data root, overridable via A_STOCK_DATA_DIR."""
    override = os.environ.get("A_STOCK_DATA_DIR")
    if override:
        return Path(override).expanduser()
    return _A_ANALYSIS_ROOT / "a-data"


def hist_dir() -> Path:
    return data_root() / "hist"


def manifest_path() -> Path:
    return data_root() / "hist_manifest.json"


def normalize_code(code: str) -> str:
    """Strip any exchange prefix/suffix and zero-pad to 6 digits."""
    normalized = code.strip().lower()
    normalized = normalized.replace(".sz", "").replace(".sh", "").replace(".bj", "")
    if normalized.startswith(("sh", "sz", "bj")):
        normalized = normalized[2:]
    return normalized.zfill(6)


def hist_csv_path(code: str) -> Path:
    return hist_dir() / f"{normalize_code(code)}.csv"


def load_local_hist(code: str) -> pd.DataFrame:
    """Load the local archive for one code. Empty DataFrame if absent."""
    path = hist_csv_path(code)
    if not path.exists():
        return pd.DataFrame(columns=HIST_COLUMNS)
    # utf-8-sig transparently strips the BOM.
    df = pd.read_csv(path, dtype={CODE_COL: str}, encoding="utf-8-sig")
    if DATE_COL in df.columns:
        df[DATE_COL] = df[DATE_COL].astype(str)
        df = df.sort_values(DATE_COL).reset_index(drop=True)
    return df


def local_last_date(code: str) -> str | None:
    """Latest trade date present locally, as 'YYYY-MM-DD', or None if empty."""
    df = load_local_hist(code)
    if df.empty or DATE_COL not in df.columns:
        return None
    return str(df[DATE_COL].iloc[-1])


def _fetch_increment(code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch [start_date, end_date] unadjusted daily bars via akshare.

    Dates are 'YYYYMMDD'. Returns archive-schema columns; empty on any failure.
    """
    import akshare as ak

    raw = normalize_code(code)
    df = ak.stock_zh_a_hist(
        symbol=raw, period="daily",
        start_date=start_date, end_date=end_date, adjust=ARCHIVE_ADJUST,
    )
    if df is None or df.empty:
        return pd.DataFrame(columns=HIST_COLUMNS)
    # akshare returns 日期 as date objects; align to archive schema.
    if DATE_COL in df.columns:
        df[DATE_COL] = df[DATE_COL].astype(str)
    if CODE_COL not in df.columns:
        df[CODE_COL] = raw
    df[CODE_COL] = df[CODE_COL].astype(str)
    for col in HIST_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    return df[HIST_COLUMNS]


def _write_archive(code: str, df: pd.DataFrame) -> None:
    """Atomically write the merged archive back with BOM, ascending, deduped."""
    df = df.drop_duplicates(subset=[DATE_COL], keep="last")
    df = df.sort_values(DATE_COL).reset_index(drop=True)
    path = hist_csv_path(code)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".csv.tmp")
    df.to_csv(tmp, index=False, encoding="utf-8-sig")
    os.replace(tmp, path)


def _next_day_str(date_str: str) -> str:
    """Given 'YYYY-MM-DD', return the following day as 'YYYYMMDD'."""
    d = datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)
    return d.strftime("%Y%m%d")


def get_hist(
    code: str,
    *,
    end_date: str | None = None,
    allow_network: bool = True,
    persist: bool = True,
) -> pd.DataFrame:
    """Local-first daily history with incremental top-up.

    1. Load the local archive.
    2. If it already reaches ``end_date`` (default: today), return it — zero network.
    3. Otherwise fetch only the missing tail (last_local+1 .. end_date), append it
       back into the archive, and return the merged frame.

    Set ``allow_network=False`` for a strictly offline read, or ``persist=False``
    to fetch the tail without rewriting the archive.
    """
    end = end_date or datetime.now().strftime("%Y-%m-%d")
    local = load_local_hist(code)
    last = str(local[DATE_COL].iloc[-1]) if not local.empty else None

    if last is not None and last >= end:
        return local
    if not allow_network:
        return local

    start = _next_day_str(last) if last else "19900101"
    try:
        increment = _fetch_increment(code, start, end.replace("-", ""))
    except Exception:
        return local
    if increment.empty:
        return local

    merged = pd.concat([local, increment], ignore_index=True)
    merged = merged.drop_duplicates(subset=[DATE_COL], keep="last")
    merged = merged.sort_values(DATE_COL).reset_index(drop=True)

    if persist:
        _write_archive(code, merged)
        _update_manifest(code, len(merged))
    return merged


def _update_manifest(code: str, rows: int) -> None:
    """Refresh the manifest row-count for one code; tolerate a missing manifest."""
    path = manifest_path()
    raw = normalize_code(code)
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        manifest = {"results": []}
    results = manifest.setdefault("results", [])
    for entry in results:
        if entry.get("code") == raw:
            entry["rows"] = rows
            entry["status"] = "updated"
            entry.pop("path", None)
            break
    else:
        results.append({"code": raw, "status": "updated", "rows": rows})
    manifest["last_incremental_at"] = datetime.now().isoformat(timespec="seconds")
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)
