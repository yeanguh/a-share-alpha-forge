from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import pytest

import assemble_report_data
import check_optional_data_sources
import persist_report
import rank_news
import render_report
import review_archive
import run_daily_report
from score_stocks import MarketCapRange, load_observations
from threshold_config import load_thresholds


def write_json(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def candidate(title: str, direction: str, score: float = 4.2) -> dict[str, object]:
    return {
        "title": title,
        "direction": direction,
        "magnitude": score,
        "breadth": score,
        "immediacy": score,
        "confidence": score,
        "novelty": score,
        "liquidity": score,
        "price_volume": score,
    }


def stock(
    ticker: str = "688525",
    sector: str = "半导体材料",
    market_cap_billion: float = 1200.0,
    institutional_trend_score: float = 3.8,
) -> dict[str, object]:
    return {
        "ticker": ticker,
        "name": "佰维存储",
        "sector": sector,
        "directional_role": "beneficiary",
        "market_cap_billion": market_cap_billion,
        "trend_score": 4.0,
        "volume_score": 4.0,
        "retail_sentiment": 3.2,
        "retail_voc_summary": "公开讨论热度中性偏高",
        "capital_recognition": 4.0,
        "event_alignment": 4.2,
        "risk_score": 3.0,
        "institutional_trend_score": institutional_trend_score,
        "external_data": {
            "quote_snapshot": {"source": "tencent_public_quote", "total_market_cap_billion": market_cap_billion}
        },
    }


def bundle() -> dict[str, object]:
    return {
        "window": {
            "timezone": "Asia/Shanghai",
            "start": "2026-06-11T09:30:00+08:00",
            "end": "2026-06-12T09:30:00+08:00",
        },
        "fund_flow": {
            "direction": "结构性流入",
            "data_quality": "partial",
            "pbc_open_market_operation_summary": "逆回购净投放1780亿元",
        },
        "candidates": [candidate(f"正向{i}", "positive") for i in range(10)]
        + [candidate(f"负向{i}", "negative") for i in range(10)],
        "sector_candidates": [candidate("半导体材料", "positive", 4.3)],
        "stocks": [stock()],
    }


def test_persist_report_keeps_versioned_runs_and_latest_copy(tmp_path: Path) -> None:
    bundle_path = write_json(tmp_path / "bundle.json", bundle())
    first_report = (tmp_path / "first.md")
    first_report.write_text("first", encoding="utf-8")
    second_report = tmp_path / "second.md"
    second_report.write_text("second", encoding="utf-8")
    output_root = tmp_path / "archive"

    persist_report.persist_command(
        argparse.Namespace(
            bundle=str(bundle_path),
            assembled=None,
            report=str(first_report),
            close_review=None,
            date=None,
            output_root=str(output_root),
            run_id="run1",
        )
    )
    persist_report.persist_command(
        argparse.Namespace(
            bundle=str(bundle_path),
            assembled=None,
            report=str(second_report),
            close_review=None,
            date=None,
            output_root=str(output_root),
            run_id="run2",
        )
    )

    day_dir = output_root / "2026-06-12"
    assert (day_dir / "runs" / "run1" / "report.md").read_text(encoding="utf-8") == "first"
    assert (day_dir / "runs" / "run2" / "report.md").read_text(encoding="utf-8") == "second"
    assert (day_dir / "report.md").read_text(encoding="utf-8") == "second"
    metadata = json.loads((day_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["run_id"] == "run2"


def test_assemble_report_writes_output_preserves_evidence_and_cleans_temp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    input_path = write_json(tmp_path / "bundle.json", bundle())
    output_path = tmp_path / "assembled.json"

    assemble_report_data.assemble_command(
        argparse.Namespace(
            input=str(input_path),
            output=str(output_path),
            top_positive_sectors=10,
            top_negative_sectors=10,
            top_positive=10,
            top_negative=10,
            min_beneficiary_sector_impact=4.0,
            min_beneficiary_sector_price_volume=4.0,
            min_beneficiary_sector_liquidity=4.0,
            top_mainline_sectors=5,
            top_leading_stocks=10,
            min_market_cap_billion=100.0,
            max_market_cap_billion=2000.0,
        )
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    beneficiary = payload["eligible_beneficiaries"][0]
    assert beneficiary["retail_voc_summary"] == "公开讨论热度中性偏高"
    assert beneficiary["external_data"]["quote_snapshot"]["source"] == "tencent_public_quote"
    assert not list(tmp_path.glob("a_share_*_bundle_*.json"))


def test_assemble_report_uses_threshold_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    config = load_thresholds()
    config["version"] = "test-tight-capital"
    config["stock_gates"]["beneficiary"]["capital_recognition_min"] = 4.2
    config_path = write_json(tmp_path / "thresholds.json", config)
    input_path = write_json(tmp_path / "bundle.json", bundle())
    output_path = tmp_path / "assembled.json"

    assemble_report_data.assemble_command(
        argparse.Namespace(
            input=str(input_path),
            output=str(output_path),
            threshold_config=str(config_path),
            top_positive_sectors=None,
            top_negative_sectors=None,
            top_positive=None,
            top_negative=None,
            min_beneficiary_sector_impact=None,
            min_beneficiary_sector_price_volume=None,
            min_beneficiary_sector_liquidity=None,
            top_mainline_sectors=None,
            top_leading_stocks=None,
            min_market_cap_billion=None,
            max_market_cap_billion=None,
        )
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["threshold_config"]["version"] == "test-tight-capital"
    assert payload["eligible_beneficiaries"] == []
    assert "资金认可度不足" in payload["excluded_stocks"][0]["exclusion_reason"]


def test_render_report_outputs_fixed_sections(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    input_path = write_json(tmp_path / "bundle.json", bundle())
    output_path = tmp_path / "assembled.json"
    assemble_report_data.assemble_command(
        argparse.Namespace(
            input=str(input_path),
            output=str(output_path),
            threshold_config=None,
            top_positive_sectors=None,
            top_negative_sectors=None,
            top_positive=None,
            top_negative=None,
            min_beneficiary_sector_impact=None,
            min_beneficiary_sector_price_volume=None,
            min_beneficiary_sector_liquidity=None,
            top_mainline_sectors=None,
            top_leading_stocks=None,
            min_market_cap_billion=None,
            max_market_cap_billion=None,
        )
    )

    report = render_report.render_report(json.loads(output_path.read_text(encoding="utf-8")))

    assert "# A股投资资讯影响简报" in report
    assert "## 每日主线板块/概念与龙头个股" in report
    assert "## 正向负向事件Top" in report
    assert "## 数据留痕与复盘" in report
    assert "阈值版本：2026-06-default-v1" in report


def test_run_daily_report_assembles_renders_and_persists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    bundle_path = write_json(tmp_path / "bundle.json", bundle())

    run_daily_report.run_command(
        argparse.Namespace(
            bundle=str(bundle_path),
            work_dir=str(tmp_path / "work"),
            assembled_output=None,
            report_output=None,
            output_root=str(tmp_path / "archive"),
            run_id="run1",
            date=None,
            threshold_config=None,
            top_positive_sectors=None,
            top_negative_sectors=None,
            top_positive=None,
            top_negative=None,
            min_beneficiary_sector_impact=None,
            min_beneficiary_sector_price_volume=None,
            min_beneficiary_sector_liquidity=None,
            top_mainline_sectors=None,
            top_leading_stocks=None,
            min_market_cap_billion=None,
            max_market_cap_billion=None,
        )
    )

    day_dir = tmp_path / "archive" / "2026-06-12"
    assert (day_dir / "input_bundle.json").exists()
    assert (day_dir / "assembled.json").exists()
    assert (day_dir / "report.md").exists()
    assert "## 短期市场判断" in (day_dir / "report.md").read_text(encoding="utf-8")


def test_assemble_warns_when_pbc_summary_missing(tmp_path: Path) -> None:
    payload = bundle()
    assert isinstance(payload["fund_flow"], dict)
    payload["fund_flow"].pop("pbc_open_market_operation_summary")

    fund_flow, warnings = assemble_report_data.validate_fund_flow(payload)

    assert fund_flow["direction"] == "结构性流入"
    assert any("pbc_open_market_operation_summary" in warning for warning in warnings)


def test_check_optional_data_sources_uses_explicit_fetcher_not_personal_path(tmp_path: Path) -> None:
    status = check_optional_data_sources.akshare_fetch_status("300750", "basic", data_fetcher=None)

    if status["status"] == "not_checked":
        assert "ASHARE_DATA_FETCHER" in str(status["detail"])
    else:
        assert "/Users/bytedance/.agents" not in str(status["detail"])


def test_rank_news_uses_trading_calendar_for_holiday_window(tmp_path: Path) -> None:
    calendar_path = write_json(
        tmp_path / "calendar.json",
        ["2026-09-30", "2026-10-09", "2026-10-12"],
    )
    calendar = rank_news.load_trading_calendar(calendar_path)

    window = rank_news.latest_completed_window(datetime.fromisoformat("2026-10-09T10:00:00+08:00"), calendar)

    assert window.start.date().isoformat() == "2026-09-30"
    assert window.end.date().isoformat() == "2026-10-09"


def test_review_archive_aggregates_sector_and_stock_hit_rates(tmp_path: Path) -> None:
    day_dir = tmp_path / "2026-06-12"
    day_dir.mkdir()
    write_json(
        day_dir / "close_review.json",
        {
            "direction_hit": True,
            "average_stock_error": 1.5,
            "sector_hits": [{"sector": "半导体", "hit": True}, {"sector": "汽车", "hit": False}],
            "stock_hits": [{"ticker": "688525", "hit": True}],
            "lesson": "强主线有效",
        },
    )

    record = review_archive.load_review_record(day_dir)
    assert record is not None
    summary = review_archive.summarize([record], "weekly")

    period = summary["summaries"][0]
    assert period["direction_hit_rate"] == 1.0
    assert period["sector_hit_rate"] == 0.5
    assert period["sector_sample_count"] == 2
    assert period["stock_hit_rate"] == 1.0


def test_review_archive_writes_periodic_review_output(tmp_path: Path) -> None:
    day_dir = tmp_path / "daily" / "2026-06-12"
    day_dir.mkdir(parents=True)
    write_json(
        day_dir / "close_review.json",
        {
            "direction_hit": True,
            "average_stock_error": 0.8,
            "lesson": "周期复盘应写入专用目录",
        },
    )
    output_path = tmp_path / "reviews" / "weekly" / "weekly_review_2026-06-12_2026-06-12.json"

    review_archive.review_command(
        argparse.Namespace(
            output_root=str(tmp_path / "daily"),
            frequency="weekly",
            start="2026-06-12",
            end="2026-06-12",
            output=str(output_path),
        )
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["frequency"] == "weekly"
    assert payload["summaries"][0]["review_days"] == 1


def test_score_stocks_preserves_voc_and_external_data(tmp_path: Path) -> None:
    path = write_json(tmp_path / "stocks.json", [stock()])

    observations = load_observations(path, MarketCapRange())
    payload = observations[0].to_dict()

    assert payload["retail_voc_summary"] == "公开讨论热度中性偏高"
    assert payload["external_data"]["quote_snapshot"]["total_market_cap_billion"] == 1200.0
    assert payload["institutional_trend_score"] == 3.8


def test_institutional_trend_score_gates_beneficiary_recommendations(tmp_path: Path) -> None:
    weak_trend_path = write_json(tmp_path / "stocks.json", [stock(institutional_trend_score=3.2)])

    observation = load_observations(weak_trend_path, MarketCapRange())[0]

    assert observation.eligible_for_recommendation is False
    assert "机构趋势确认不足" in observation.exclusion_reason
    assert observation.operation_tendency == "等待机构趋势确认"


def test_institutional_trend_score_defaults_to_unconfirmed(tmp_path: Path) -> None:
    item = stock()
    item.pop("institutional_trend_score")
    path = write_json(tmp_path / "stocks.json", [item])

    observation = load_observations(path, MarketCapRange())[0]

    assert observation.institutional_trend_score == 0
    assert observation.eligible_for_recommendation is False
