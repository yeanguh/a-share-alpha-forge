from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

from scripts import a_share_data
from scripts.a_share_data import safe_float


ROOT = Path(__file__).resolve().parents[1]
DATA_FETCHER = ROOT / ".agents/skills/china-stock-analysis/scripts/data_fetcher.py"


def load_data_fetcher():
    spec = importlib.util.spec_from_file_location("china_stock_data_fetcher_test", DATA_FETCHER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_safe_float_accepts_chinese_billion_unit() -> None:
    assert safe_float("1,234.56亿") == 1234.56
    assert safe_float("7.5%") == 7.5
    assert safe_float("--") is None


def test_http_get_text_retries_transient_failures(monkeypatch) -> None:
    calls = {"count": 0}

    class Response:
        def __enter__(self):  # noqa: ANN204
            return self

        def __exit__(self, *_args):  # noqa: ANN002
            return False

        def read(self) -> bytes:
            return "成功".encode("utf-8")

    def fake_urlopen(_req, timeout):  # noqa: ANN001
        calls["count"] += 1
        if calls["count"] == 1:
            raise OSError("remote closed")
        return Response()

    monkeypatch.setattr(a_share_data.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(a_share_data.time, "sleep", lambda _seconds: None)

    assert a_share_data.http_get_text("https://example.test", retries=2) == "成功"
    assert calls["count"] == 2


def test_no_cache_disables_cache_read_and_write(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "akshare", types.ModuleType("akshare"))
    module = load_data_fetcher()
    monkeypatch.setattr(module, "NO_CACHE", True)
    monkeypatch.setattr(module, "get_stock_info", lambda code: {"code": code})

    def fail_cache(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("cache should not be touched when A_STOCK_NO_CACHE is enabled")

    monkeypatch.setattr(module, "load_cache", fail_cache)
    monkeypatch.setattr(module, "save_cache", fail_cache)

    result = module.fetch_stock_data("600584", data_type="basic", use_cache=True)

    assert result["basic_info"] == {"code": "600584"}
