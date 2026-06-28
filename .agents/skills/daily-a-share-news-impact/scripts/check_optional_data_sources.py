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


def default_data_fetcher() -> Path | None:
    configured = os.getenv("ASHARE_DATA_FETCHER")
    if configured:
        return Path(configured).expanduser()
    return None


def akshare_fetch_status(code: str | None, data_type: str, data_fetcher: Path | None = None) -> dict[str, object]:
    if not code:
        return {"status": "not_checked", "detail": "No probe code provided."}
    fetcher = data_fetcher or default_data_fetcher()
    if fetcher is None:
        return {
            "status": "not_checked",
            "detail": "No data fetcher configured; set `ASHARE_DATA_FETCHER` or pass `--data-fetcher`.",
        }
    dependency = akshare_dependency_status()
    if dependency["status"] != "installed":
        return {
            "status": "missing_dependency",
            "detail": "akshare fetch probe skipped because `akshare` is not installed.",
        }
    if not fetcher.exists():
        return {"status": "missing_script", "detail": f"`{fetcher}` does not exist."}

    output_dir = Path(os.getenv("TMPDIR") or "tmp")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"a_share_optional_probe_{code}_{data_type}.json"
    command = [
        sys.executable,
        str(fetcher),
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


def mootdx_status(code: str | None) -> dict[str, str]:
    version = package_version("mootdx")
    if version is None:
        return {"status": "missing_dependency", "detail": "`mootdx` is not installed."}
    if not code:
        return {"status": "not_checked", "detail": f"mootdx={version}; no probe code provided."}
    try:
        from mootdx.quotes import Quotes

        client = Quotes.factory(market="std")
        try:
            frame = client.quotes([a_share_region_and_code(code)[1]])
        finally:
            client.close()
    except Exception as exc:  # noqa: BLE001
        return {"status": "fetch_failed", "detail": f"mootdx={version}; {type(exc).__name__}: {exc}"}
    if frame is not None and not frame.empty:
        return {"status": "available", "detail": f"mootdx={version}; Tongdaxin quote returned data."}
    return {"status": "fetch_failed", "detail": f"mootdx={version}; empty quote frame."}


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


def iwencai_status() -> dict[str, str]:
    api_key = os.getenv("IWENCAI_API_KEY")
    pywencai_version = package_version("pywencai")
    if api_key:
        detail = "`IWENCAI_API_KEY` is set"
        if pywencai_version:
            detail += f"; pywencai={pywencai_version}"
        return {"status": "available", "detail": detail}
    if pywencai_version:
        return {
            "status": "missing_credentials",
            "detail": f"pywencai={pywencai_version}; `IWENCAI_API_KEY` is not set.",
        }
    return {
        "status": "missing_credentials",
        "detail": "`IWENCAI_API_KEY` is not set; use generated WenCai queries or AkShare reports as fallback.",
    }


def module_health(result: dict[str, dict[str, object]]) -> dict[str, object]:
    return {
        "realtime_quote": {
            "primary": ["mootdx"],
            "fallback": ["tencent_quote", "eastmoney_quote", "sina_quote", "baostock"],
            "usable": any(
                result.get(name, {}).get("status") == "available"
                for name in ("mootdx", "tencent_quote", "eastmoney_quote", "sina_quote", "baostock")
            ),
        },
        "valuation": {
            "primary": ["tencent_quote", "eastmoney_quote"],
            "fallback": ["akshare_fetch"],
            "usable": any(
                result.get(name, {}).get("status") == "available"
                for name in ("tencent_quote", "eastmoney_quote", "akshare_fetch")
            ),
        },
        "research_reports": {
            "primary": ["akshare"],
            "fallback": ["iwencai_api_when_configured"],
            "usable": result.get("akshare_dependency", {}).get("status") == "installed"
            or result.get("iwencai", {}).get("status") == "available",
        },
        "news": {
            "primary": ["akshare"],
            "fallback": ["manual_authority_checks"],
            "usable": result.get("akshare_dependency", {}).get("status") == "installed",
        },
        "basic_data": {
            "primary": ["mootdx", "akshare"],
            "fallback": ["tencent_quote", "eastmoney_quote", "baostock"],
            "usable": any(
                result.get(name, {}).get("status") in {"available", "installed"}
                for name in ("mootdx", "akshare_dependency", "tencent_quote", "eastmoney_quote", "baostock")
            ),
        },
        "announcements": {
            "primary": ["akshare_cninfo"],
            "fallback": ["akshare_eastmoney_notice"],
            "usable": result.get("akshare_dependency", {}).get("status") == "installed",
        },
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
    data_fetcher = Path(args.data_fetcher).expanduser() if args.data_fetcher else None
    result = {
        "akshare_dependency": akshare_dependency_status(),
        "akshare_fetch": akshare_fetch_status(args.akshare_code, args.akshare_data_type, data_fetcher),
        "mootdx": mootdx_status(quote_code),
        "sina_quote": sina_quote_status(quote_code),
        "tencent_quote": tencent_quote_status(quote_code),
        "eastmoney_quote": eastmoney_quote_status(quote_code),
        "itick": itick_status(quote_code),
        "zhitu": zhitu_status(quote_code),
        "baostock": baostock_status(),
        "iwencai": iwencai_status(),
    }
    if args.include_paid:
        result = {
            "qveris": qveris_status(),
            **result,
            "tushare": tushare_status(),
        }
    result["module_health"] = module_health(result)
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
    parser.add_argument(
        "--data-fetcher",
        help="Optional path to a compatible akshare data_fetcher.py. Overrides ASHARE_DATA_FETCHER.",
    )
    parser.set_defaults(func=check_command)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
