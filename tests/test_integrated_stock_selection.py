from __future__ import annotations

import importlib.util
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
