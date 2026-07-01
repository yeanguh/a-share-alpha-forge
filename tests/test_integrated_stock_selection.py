from __future__ import annotations

import importlib.util
import argparse
import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(".agents/skills/integrated-stock-selection/scripts/run_integrated_selection.py").resolve()


def load_module():
    spec = importlib.util.spec_from_file_location("run_integrated_selection", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_theme_selection_uses_archive_and_scores_candidates() -> None:
    module = load_module()
    date, archive = module.load_archive("2026-06-26")
    candidates = module.collect_candidates(archive, [], "存储芯片")
    rows = [module.render_candidate(candidate) for candidate in candidates.values()]
    rows.sort(key=lambda row: row["score"], reverse=True)

    assert date == "2026-06-26"
    assert rows
    assert rows[0]["code"] == "603986"
    assert rows[0]["bucket"] == "core"
    assert "eligible_beneficiaries" in rows[0]["source_tags"]


def test_iwencai_candidates_are_first_pass_and_can_be_core() -> None:
    module = load_module()
    _, archive = module.load_archive("2026-06-26")
    iwencai = {
        "recommendations": [
            {
                "code": "603688.SH",
                "name": "石英股份",
                "recommend_rank": 1,
                "recommendation_score": 650,
                "score": 4.2,
                "strategy_hits": [{"strategy_name": "主线三日趋势承接", "rank": 1}],
                "reason": "命中主线三日趋势承接",
                "concepts": ["存储芯片", "半导体概念"],
            }
        ],
        "high_confidence_recommendations": [
            {
                "code": "603688.SH",
                "name": "石英股份",
                "high_confidence_rank": 1,
                "recommendation_score": 650,
                "score": 4.2,
                "reason": "满足高置信度三日上涨过滤",
                "concepts": ["存储芯片", "半导体概念"],
            }
        ],
        "pools": {
            "main_theme": [
                {
                    "code": "603688.SH",
                    "name": "石英股份",
                    "rank": 1,
                    "strategy": "main_theme",
                    "strategy_name": "主线三日趋势承接",
                    "score": 4.2,
                    "concepts": ["存储芯片", "半导体概念"],
                }
            ]
        },
    }

    candidates = module.collect_candidates(archive, [], "存储芯片", iwencai)
    row = module.render_candidate(candidates["603688"])

    assert row["bucket"] == "core"
    assert "iwencai-trend-stock-pool" in row["source_tags"]
    assert row["dimensions"]["iwencai"] == 5.0
    assert "通过问财趋势承接高置信度过滤" in row["reasons"]


def test_explicit_codes_do_not_pull_all_industry_companies() -> None:
    module = load_module()
    _, archive = module.load_archive("2026-06-26")
    candidates = module.collect_candidates(archive, ["603986"], None)

    assert "603986" in candidates
    assert "601138" not in candidates


def test_split_codes_arg_repairs_missing_comma_between_six_digit_codes() -> None:
    module = load_module()

    assert module.split_codes_arg("301095,300041600459,603688") == [
        "301095",
        "300041",
        "600459",
        "603688",
    ]


def test_missing_current_archive_uses_close_review_context(tmp_path: Path, monkeypatch) -> None:
    module = load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setenv("A_STOCK_SELECTION_TODAY", "2026-07-01")
    latest_dir = tmp_path / "local" / "2026-06-30"
    today_dir = tmp_path / "local" / "2026-07-01"
    latest_dir.mkdir(parents=True)
    today_dir.mkdir(parents=True)
    (latest_dir / "assembled.json").write_text(
        json.dumps({"daily_mainlines": [{"title": "旧主线", "impact_score": 3.0}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (today_dir / "close_review.json").write_text(
        json.dumps(
            {
                "review_time": "2026-07-01T15:20:00+08:00",
                "actual_market_summary": "科技成长转强，先进封装资金回流。",
                "fund_flow_review": {"actual": "电子和半导体主力净流入。"},
                "sector_hits": [{"sector": "先进封装", "hit": True, "hit_level": "强命中", "actual_move": "+5%"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    date, archive, context = module.load_archive_for_selection(None)
    mainlines = module.close_review_mainlines(context, None)

    assert date == "2026-06-30"
    assert archive["daily_mainlines"][0]["title"] == "旧主线"
    assert context["source"] == "close_review_fallback"
    assert context["requested_date"] == "2026-07-01"
    assert context["archive_date"] == "2026-06-30"
    assert context["close_review_used"] is True
    assert any(item["title"] == "收盘复盘：先进封装" for item in mainlines)


def test_missing_current_archive_without_close_review_warns_stale_context(tmp_path: Path, monkeypatch) -> None:
    module = load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setenv("A_STOCK_SELECTION_TODAY", "2026-07-01")
    latest_dir = tmp_path / "local" / "2026-06-30"
    latest_dir.mkdir(parents=True)
    (latest_dir / "assembled.json").write_text(
        json.dumps({"daily_mainlines": [{"title": "旧主线", "impact_score": 3.0}]}, ensure_ascii=False),
        encoding="utf-8",
    )

    date, _archive, context = module.load_archive_for_selection(None)

    assert date == "2026-06-30"
    assert context["source"] == "latest_archive_fallback"
    assert context["close_review_used"] is False
    assert "未找到 2026-07-01 的 assembled 主线或收盘复盘" in context["warning"]


def test_market_context_adjusts_rows_from_close_review(tmp_path: Path, monkeypatch) -> None:
    module = load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    review_dir = tmp_path / "local" / "2026-07-01"
    review_dir.mkdir(parents=True)
    (review_dir / "close_review.json").write_text(
        json.dumps(
            {
                "stock_hits": [
                    {"ticker": "600584", "name": "长电科技", "hit": True, "hit_level": "强命中", "actual_move": "+4%"},
                    {"ticker": "600276", "name": "恒瑞医药", "hit": False, "hit_level": "未命中", "actual_move": "-2%"},
                ],
                "sector_hits": [{"sector": "先进封装", "hit": True, "hit_level": "强命中", "actual_move": "+5%"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    rows = [
        {"code": "600584", "name": "长电科技", "sector": "先进封装", "bucket": "watch", "score": 72.0, "reasons": [], "source_tags": [], "iwencai_matches": []},
        {"code": "600276", "name": "恒瑞医药", "sector": "创新药", "bucket": "watch", "score": 55.0, "reasons": [], "source_tags": [], "iwencai_matches": []},
    ]

    module.apply_market_context(
        rows,
        {"close_review_used": True, "close_review_date": "2026-07-01", "requested_date": "2026-07-01"},
    )

    assert rows[0]["score"] > 72.0
    assert rows[0]["market_context_evidence"]
    assert rows[1]["score"] < 55.0


def test_quote_refresh_can_downgrade_extreme_valuation(tmp_path: Path) -> None:
    module = load_module()
    snapshot = tmp_path / "quote.json"
    snapshot.write_text(
        '{"quote":{"latest":10,"change_pct":1.2,"market_cap":1000000000,"pe_ttm":150,"pb":8,"source":"test"}}',
        encoding="utf-8",
    )
    row = {
        "bucket": "core",
        "score": 72.0,
        "quote": {},
        "quote_refresh": {},
        "reasons": [],
        "missing_evidence": ["缺少本次归档行情/估值快照"],
        "source_tags": ["iwencai-trend-stock-pool"],
    }

    module.apply_quote_refresh(row, snapshot)

    assert row["bucket"] == "watch"
    assert row["score"] == 67.0
    assert row["quote"]["pe_ttm"] == 150
    assert "刷新行情显示估值显著偏高" in row["reasons"]
    assert "缺少本次归档行情/估值快照" not in row["missing_evidence"]
    assert "估值高位，需要盈利兑现复核" in row["missing_evidence"]


def test_investment_committee_review_adds_action_to_rows() -> None:
    module = load_module()
    rows = [
        {
            "code": "603986",
            "name": "兆易创新",
            "bucket": "core",
            "score": 74.81,
            "dimensions": {
                "trend": 4.0,
                "volume": 3.8,
                "iwencai": 4.0,
                "event": 4.3,
                "beneficiary": 4.0,
                "institutional": 3.8,
                "industry": 2.0,
                "risk_control": 3.6,
            },
            "quote": {"pe_ttm": 80},
            "source_tags": ["eligible_beneficiaries", "iwencai-trend-stock-pool"],
            "missing_evidence": [],
        }
    ]

    review = module.investment_committee_review(rows)

    assert review["mode"] == "local_deterministic_committee"
    assert review["reviews"][0]["code"] == "603986"
    assert rows[0]["committee_review"]["action"] in {"核心观察", "观察等待"}


def test_run_iwencai_stock_pool_passes_local_fallback_inputs(tmp_path, monkeypatch) -> None:
    module = load_module()
    spot_csv = tmp_path / "stock_list.csv"
    theme_cache = tmp_path / "theme_codes.json"
    output_dir = module.ROOT / "tmp" / "pytest-iwencai-fallback"
    spot_csv.write_text("代码,名称\n300042,朗科科技\n", encoding="utf-8")
    theme_cache.write_text(
        '{"theme_codes":["300042.SZ"],"code_concepts":{"300042.SZ":["存储芯片"]},"code_theme_tier":{"300042.SZ":"core"}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "IWENCAI_DEFAULT_SPOT_CSV", spot_csv)
    monkeypatch.setattr(module, "IWENCAI_DEFAULT_THEME_CACHE", theme_cache)
    captured: dict[str, list[str]] = {}

    def fake_run(command, **_kwargs):  # noqa: ANN001
        captured["command"] = command
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "stock_pools.json").write_text('{"pools":{}}', encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    args = argparse.Namespace(
        skip_iwencai=False,
        iwencai_json=None,
        iwencai_output_dir=str(output_dir),
        iwencai_strategies=module.IWENCAI_DEFAULT_STRATEGIES,
        iwencai_max_stocks=300,
        iwencai_top=20,
        iwencai_recommend_top=8,
        iwencai_high_confidence_top=8,
        iwencai_workers=8,
        iwencai_timeout=900,
        iwencai_no_cache=False,
        iwencai_spot_csv=None,
        iwencai_theme_cache_json=None,
    )

    result = module.run_iwencai_stock_pool(args)

    assert result and result["status"] == "generated"
    assert captured["command"][captured["command"].index("--spot-csv") + 1] == str(spot_csv)
    assert captured["command"][captured["command"].index("--theme-cache-json") + 1] == str(theme_cache)
