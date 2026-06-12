#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from importlib import metadata
from pathlib import Path
from urllib import error, request

DATA_FETCHER = Path("/Users/bytedance/.agents/skills/china-stock-analysis/scripts/data_fetcher.py")
DEFAULT_TIMEOUT_SECONDS = 10


def a_share_symbol(code: str) -> str:
    normalized = code.strip().lower().replace(".sz", "").replace(".sh", "")
    if normalized.startswith(("sh", "sz")):
        return normalized
    if normalized.startswith(("6", "9")):
        return f"sh{normalized}"
    return f"sz{normalized}"


def a_share_region_and_code(code: str) -> tuple[str, str]:
    symbol = a_share_symbol(code)
    region = "SH" if symbol.startswith("sh") else "SZ"
    return region, symbol[2:]


def http_get_text(url: str, headers: dict[str, str] | None = None) -> str:
    req = request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            **(headers or {}),
        },
    )
    with request.urlopen(req, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
        return response.read().decode("utf-8", errors="replace")


def package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def qveris_status() -> dict[str, str]:
    if os.getenv("QVERIS_API_KEY"):
        return {"status": "available", "detail": "`QVERIS_API_KEY` is set."}
    return {
        "status": "missing_credentials",
        "detail": "`QVERIS_API_KEY` is not set; use akshare or other quote sources as fallback.",
    }


def akshare_dependency_status() -> dict[str, str]:
    version = package_version("akshare")
    if version is None:
        return {"status": "missing_dependency", "detail": "`akshare` is not installed."}
    pandas_version = package_version("pandas") or "unknown"
    numpy_version = package_version("numpy") or "unknown"
    return {
        "status": "installed",
        "detail": f"akshare={version}, pandas={pandas_version}, numpy={numpy_version}",
    }


def akshare_fetch_status(code: str | None, data_type: str) -> dict[str, object]:
    dependency = akshare_dependency_status()
    if dependency["status"] != "installed":
        return {
            "status": "not_checked",
            "detail": "akshare fetch probe skipped because `akshare` is not installed.",
        }
    if not code:
        return {"status": "not_checked", "detail": "No probe code provided."}
    if not DATA_FETCHER.exists():
        return {"status": "missing_script", "detail": f"`{DATA_FETCHER}` does not exist."}

    output_dir = Path(os.getenv("TMPDIR") or "tmp")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"a_share_optional_probe_{code}_{data_type}.json"
    command = [
        sys.executable,
        str(DATA_FETCHER),
        "--code",
        code,
        "--data-type",
        data_type,
        "--no-cache",
        "--output",
        str(output_path),
    ]
    completed = subprocess.run(command, check=False, text=True, capture_output=True, timeout=60)
    if completed.returncode != 0:
        return {
            "status": "fetch_failed",
            "detail": completed.stderr.strip() or completed.stdout.strip(),
            "output_path": str(output_path),
        }
    try:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "fetch_failed", "detail": str(exc), "output_path": str(output_path)}

    errors = collect_error_messages(payload)
    if errors:
        return {
            "status": "fetch_failed",
            "detail": "; ".join(errors[:3]),
            "output_path": str(output_path),
        }
    return {"status": "available", "detail": "akshare fetch succeeded.", "output_path": str(output_path)}


def sina_quote_status(code: str | None) -> dict[str, str]:
    if not code:
        return {"status": "not_checked", "detail": "No probe code provided."}
    symbol = a_share_symbol(code)
    try:
        text = http_get_text(
            f"https://hq.sinajs.cn/list={symbol}",
            {"Referer": "https://finance.sina.com.cn/"},
        )
    except (OSError, error.URLError) as exc:
        return {"status": "fetch_failed", "detail": str(exc)}
    if f"var hq_str_{symbol}=" in text and "," in text:
        return {"status": "available", "detail": "Sina public quote endpoint returned quote text."}
    return {"status": "fetch_failed", "detail": text[:200]}


def tencent_quote_status(code: str | None) -> dict[str, str]:
    if not code:
        return {"status": "not_checked", "detail": "No probe code provided."}
    symbol = a_share_symbol(code)
    try:
        text = http_get_text(f"https://qt.gtimg.cn/q={symbol}")
    except (OSError, error.URLError) as exc:
        return {"status": "fetch_failed", "detail": str(exc)}
    if f"v_{symbol}=" in text and "~" in text:
        return {"status": "available", "detail": "Tencent public quote endpoint returned quote text."}
    return {"status": "fetch_failed", "detail": text[:200]}


def eastmoney_quote_status(code: str | None) -> dict[str, str]:
    if not code:
        return {"status": "not_checked", "detail": "No probe code provided."}
    symbol = a_share_symbol(code)
    market_id = "1" if symbol.startswith("sh") else "0"
    numeric_code = symbol[2:]
    url = (
        "https://push2.eastmoney.com/api/qt/stock/get"
        f"?secid={market_id}.{numeric_code}&fields=f43,f57,f58,f60,f170,f47,f48,f116"
    )
    try:
        payload = json.loads(http_get_text(url))
    except (OSError, error.URLError, json.JSONDecodeError) as exc:
        return {"status": "fetch_failed", "detail": str(exc)}
    data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data, dict) and str(data.get("f57")) == numeric_code:
        return {"status": "available", "detail": "Eastmoney public quote endpoint returned JSON quote data."}
    return {"status": "fetch_failed", "detail": json.dumps(payload, ensure_ascii=False)[:200]}


def itick_status(code: str | None) -> dict[str, str]:
    token = os.getenv("ITICK_API_TOKEN")
    if not token:
        return {"status": "missing_credentials", "detail": "`ITICK_API_TOKEN` is not set."}
    if not code:
        return {"status": "not_checked", "detail": "No probe code provided."}
    region, numeric_code = a_share_region_and_code(code)
    try:
        payload = json.loads(
            http_get_text(
                f"https://api.itick.org/stock/quote?region={region}&code={numeric_code}",
                {"accept": "application/json", "token": token},
            )
        )
    except (OSError, error.URLError, json.JSONDecodeError) as exc:
        return {"status": "fetch_failed", "detail": str(exc)}
    if isinstance(payload, dict) and payload.get("code") == 0 and payload.get("data"):
        return {"status": "available", "detail": "iTick quote endpoint returned data."}
    return {"status": "fetch_failed", "detail": json.dumps(payload, ensure_ascii=False)[:200]}


def zhitu_status(code: str | None) -> dict[str, str]:
    token = os.getenv("ZHITU_API_TOKEN")
    probe_token = token or "ZHITU_TOKEN_LIMIT_TEST"
    probe_code = code if token and code else "000001"
    try:
        payload = json.loads(http_get_text(f"https://api.zhituapi.com/hs/real/time/{probe_code}?token={probe_token}"))
    except (OSError, error.URLError, json.JSONDecodeError) as exc:
        return {"status": "fetch_failed", "detail": str(exc)}
    if not isinstance(payload, dict) or "p" not in payload or "t" not in payload:
        return {"status": "fetch_failed", "detail": json.dumps(payload, ensure_ascii=False)[:200]}
    if token:
        return {"status": "available", "detail": "Zhitu quote endpoint returned JSON quote data."}
    return {
        "status": "demo_only",
        "detail": "Zhitu demo token responded, but real stock-specific use requires `ZHITU_API_TOKEN`.",
    }


def tushare_status() -> dict[str, str]:
    version = package_version("tushare")
    if version is None:
        return {"status": "missing_dependency", "detail": "`tushare` is not installed."}
    if not os.getenv("TUSHARE_TOKEN"):
        return {"status": "missing_credentials", "detail": f"tushare={version}; `TUSHARE_TOKEN` is not set."}
    return {"status": "available", "detail": f"tushare={version}; `TUSHARE_TOKEN` is set."}


def baostock_status() -> dict[str, str]:
    version = package_version("baostock")
    if version is None:
        return {"status": "missing_dependency", "detail": "`baostock` is not installed."}
    return {
        "status": "available",
        "detail": f"baostock={version} is installed; use as no-key historical K-line fallback.",
    }


def collect_error_messages(value: object) -> list[str]:
    messages: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "error" and item:
                messages.append(str(item))
            else:
                messages.extend(collect_error_messages(item))
    elif isinstance(value, list):
        for item in value:
            messages.extend(collect_error_messages(item))
    return messages


def check_command(args: argparse.Namespace) -> None:
    quote_code = args.quote_code or args.akshare_code
    result = {
        "akshare_dependency": akshare_dependency_status(),
        "akshare_fetch": akshare_fetch_status(args.akshare_code, args.akshare_data_type),
        "sina_quote": sina_quote_status(quote_code),
        "tencent_quote": tencent_quote_status(quote_code),
        "eastmoney_quote": eastmoney_quote_status(quote_code),
        "itick": itick_status(quote_code),
        "zhitu": zhitu_status(quote_code),
        "baostock": baostock_status(),
    }
    if args.include_paid:
        result = {
            "qveris": qveris_status(),
            **result,
            "tushare": tushare_status(),
        }
    write_json(result)


def write_json(payload: object) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check optional A-share data source availability.")
    parser.add_argument("--akshare-code", help="Optional stock code used to probe akshare fetching.")
    parser.add_argument("--quote-code", help="Optional stock code used to probe public quote APIs.")
    parser.add_argument(
        "--include-paid",
        action="store_true",
        help="Also probe paid or quasi-paid sources such as QVeris and Tushare Pro.",
    )
    parser.add_argument(
        "--akshare-data-type",
        default="basic",
        choices=["all", "basic", "financial", "valuation", "holder"],
        help="akshare data type to probe.",
    )
    parser.set_defaults(func=check_command)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
