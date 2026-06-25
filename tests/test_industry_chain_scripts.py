from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from public_data import SourceEntry, SourceTrail, bs_code


def write_test_png(path: Path, *, size: tuple[int, int] = (1000, 700)) -> None:
    from PIL import Image

    image = Image.new("RGB", size, "white")
    image.save(path)


def test_bs_code_normalizes_sh_prefix() -> None:
    assert bs_code("600276") == "sh.600276"
    assert bs_code("688981") == "sh.688981"
    assert bs_code("900901") == "sh.900901"


def test_bs_code_normalizes_sz_prefix() -> None:
    assert bs_code("000001") == "sz.000001"
    assert bs_code("300750") == "sz.300750"
    assert bs_code("002594") == "sz.002594"


def test_bs_code_strips_existing_prefix_and_dots() -> None:
    assert bs_code("sh.600276") == "sh.600276"
    assert bs_code("SZ000001") == "sz.000001"
    assert bs_code("  600276  ") == "sh.600276"


def test_source_trail_record_ok() -> None:
    trail = SourceTrail()
    entry = trail.record(
        tool="akshare",
        function_or_path="stock_zyjs_ths",
        subject="600276",
        payload=[{"name": "恒瑞医药"}],
        error=None,
        confidence="High",
    )
    assert entry.status == "ok"
    assert entry.rows == 1
    assert entry.error is None
    assert entry.confidence == "High"
    assert len(trail.to_list()) == 1


def test_source_trail_record_failed() -> None:
    trail = SourceTrail()
    entry = trail.record(
        tool="third-party-report",
        function_or_path="industry_research.pdf",
        subject="300750",
        payload=None,
        error="RemoteDisconnected: reset",
    )
    assert entry.status == "failed"
    assert entry.rows is None
    assert entry.error == "RemoteDisconnected: reset"


def test_source_trail_record_fallback() -> None:
    trail = SourceTrail()
    entry = trail.record(
        tool="local-cache",
        function_or_path="cached_bundle.json",
        subject="industry-board",
        payload=[{"a": 1}, {"b": 2}],
        error=None,
        fallback=True,
    )
    assert entry.status == "fallback"
    assert entry.rows == 2


def test_source_trail_row_counting_for_str_and_dict() -> None:
    trail = SourceTrail()
    str_entry = trail.record(tool="news", function_or_path="reuters", subject="x", payload="just a string", error=None)
    dict_entry = trail.record(tool="filing", function_or_path="annual", subject="x", payload={"key": "value"}, error=None)
    assert str_entry.rows is None
    assert dict_entry.rows is None


def test_source_trail_write_produces_valid_json(tmp_path: Path) -> None:
    trail = SourceTrail()
    trail.record(
        tool="akshare",
        function_or_path="stock_board_industry_cons_em",
        subject="创新药",
        payload=[{"code": "600276"}, {"code": "300363"}],
        error=None,
    )
    trail.record(
        tool="local-cache",
        function_or_path="cached_bundle.json",
        subject="600276",
        payload=None,
        error="file not found",
    )
    out = trail.write(tmp_path / "source_data.json", extra={"topic": "innovation-drug"})

    assert out == tmp_path / "source_data.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["topic"] == "innovation-drug"
    assert "generated_at" in doc
    assert len(doc["sources"]) == 2
    assert doc["sources"][0]["status"] == "ok"
    assert doc["sources"][1]["status"] == "failed"
    assert doc["sources"][1]["error"] == "file not found"


def test_source_trail_to_list_matches_dataclass_fields() -> None:
    trail = SourceTrail()
    trail.record(tool="baostock", function_or_path="query_history_k_data_plus", subject="600276",
                 payload=[["2026-01-02", "sh.600276", "45.0"]], error=None)
    row = trail.to_list()[0]
    for field_name in ("tool", "function_or_path", "subject", "status", "queried_at", "rows", "error", "confidence"):
        assert field_name in row


def test_check_data_sources_produces_expected_shape() -> None:
    import check_data_sources

    report = check_data_sources.check("600276", "2026-01-02", "2026-01-10")
    assert report["probe_code"] == "600276"
    assert report["probe_concept"] == "创新药"
    assert "dependencies" in report
    assert "adapters" in report
    for key in (
        "akshare_main_business",
        "akshare_concept_cons",
        "akshare_board_fund_flow",
        "baostock_daily",
        "adata_probe",
    ):
        assert key in report["adapters"]
        assert "status" in report["adapters"][key]
        assert "detail" in report["adapters"][key]
        assert report["adapters"][key]["status"] in ("available", "failed")


def test_try_main_business_returns_akshare_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    import public_data

    def fake_akshare_ok(_code: str):
        return [{"股票代码": "600276", "主营业务": "药品研发"}], None

    monkeypatch.setattr(public_data, "try_akshare_main_business", fake_akshare_ok)

    (payload, error), source = public_data.try_main_business("600276")
    assert source == "akshare"
    assert error is None
    assert payload is not None
    assert payload[0]["股票代码"] == "600276"


def test_try_main_business_returns_none_when_akshare_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    import public_data

    def fail(_code: str):
        return None, "RemoteDisconnected: test"

    monkeypatch.setattr(public_data, "try_akshare_main_business", fail)

    (payload, error), source = public_data.try_main_business("600276")
    assert source == "none"
    assert payload is None
    assert error is not None
    assert "RemoteDisconnected" in error


def test_render_company_mapping_table_has_nine_columns() -> None:
    from public_data import COMPANY_MAPPING_COLUMNS, render_company_mapping_table

    rows = [
        {
            "公司": "恒瑞医药",
            "代码": "600276",
            "环节": "中游",
            "细分领域": "创新药研发",
            "产业占比/暴露度": "国内龙头",
            "核心技术/产品": "卡瑞利珠单抗",
            "卡脖子相关性": "Low",
            "环节地位": "核心",
            "证据与备注": "akshare 主营",
        }
    ]
    md = render_company_mapping_table(rows)
    lines = md.strip().split("\n")
    assert len(lines) == 3  # header + sep + 1 row
    header_cols = [c.strip() for c in lines[0].split("|")[1:-1]]
    assert header_cols == COMPANY_MAPPING_COLUMNS
    assert "恒瑞医药" in lines[2]
    assert "600276" in lines[2]


def test_render_chain_overview_table_has_four_columns() -> None:
    from public_data import CHAIN_OVERVIEW_COLUMNS, render_chain_overview_table

    rows = [
        {"环节": "上游", "细分领域": "原料药", "关键价值/壁垒": "工艺", "代表A股公司": "普洛药业"}
    ]
    md = render_chain_overview_table(rows)
    lines = md.strip().split("\n")
    assert len(lines) == 3
    header_cols = [c.strip() for c in lines[0].split("|")[1:-1]]
    assert header_cols == CHAIN_OVERVIEW_COLUMNS


def test_render_upstream_material_table_has_seven_columns() -> None:
    from public_data import UPSTREAM_MATERIAL_COLUMNS, render_upstream_material_table

    rows = [
        {
            "上游层级": "Product BOM",
            "细分材料/部件": "芯片",
            "对目标产业的作用": "算力核心",
            "价值/稀缺性": "高",
            "卡脖子程度": "High",
            "A股候选": "海光信息",
            "纳入主线判断": "Core",
        }
    ]
    md = render_upstream_material_table(rows)
    lines = md.strip().split("\n")
    assert len(lines) == 3
    header_cols = [c.strip() for c in lines[0].split("|")[1:-1]]
    assert header_cols == UPSTREAM_MATERIAL_COLUMNS


def test_render_tables_fill_missing_columns_with_empty() -> None:
    from public_data import render_company_mapping_table

    rows = [{"公司": "测试公司", "代码": "000001"}]  # only 2 of 9 columns
    md = render_company_mapping_table(rows)
    lines = md.strip().split("\n")
    row_cols = [c.strip() for c in lines[2].split("|")[1:-1]]
    assert len(row_cols) == 9
    assert row_cols[0] == "测试公司"
    assert row_cols[2] == ""  # empty 环节


def test_source_trail_from_health_check_mixed_status() -> None:
    from public_data import SourceTrail

    report = {
        "probe_code": "600276",
        "adapters": {
            "akshare_main_business": {"status": "available", "detail": "ok"},
            "akshare_concept_cons": {"status": "available", "detail": "ok"},
            "akshare_board_fund_flow": {"status": "failed", "detail": "timeout"},
            "baostock_daily": {"status": "failed", "detail": "login failed"},
            "adata_probe": {"status": "available", "detail": "ok"},
        },
    }
    trail = SourceTrail.from_health_check(report)
    entries = trail.to_list()
    assert len(entries) == 5
    by_fn = {e["function_or_path"]: e for e in entries}
    assert by_fn["stock_zyjs_ths (health-check)"]["status"] == "ok"
    assert by_fn["stock_board_concept_cons_em (health-check)"]["status"] == "ok"
    assert by_fn["stock_board_concept_name_em (health-check)"]["status"] == "failed"
    assert by_fn["query_history_k_data_plus (health-check)"]["status"] == "failed"
    assert by_fn["probe (health-check)"]["status"] == "ok"
    bs_entry = by_fn["query_history_k_data_plus (health-check)"]
    assert "login failed" in (bs_entry["error"] or "")
    fund_entry = by_fn["stock_board_concept_name_em (health-check)"]
    assert "timeout" in (fund_entry["error"] or "")


def test_report_quality_passes_complete_report(tmp_path: Path) -> None:
    import report_quality

    image = tmp_path / "assets" / "chain.png"
    image.parent.mkdir()
    write_test_png(image)
    report = tmp_path / "report.md"
    report.write_text(
        f"""# 测试行业上下游产业链与A股公司分析报告

## 0. 核心结论
1. 核心部件的价值集中度高，测试公司具备直接受益机会。
2. 核心技术瓶颈在工艺、认证和客户验证，短期弹性来自订单放量。
3. 主要风险是不确定的需求节奏和估值回撤。

## 1. 研究对象、边界与口径
边界清晰。

## 2. 行业背景与需求驱动
需求增长。

## 3. 产业链全景图谱
![产业链图谱](assets/chain.png)

## 4. 上游材料、部件与制程要素挖掘
| 上游层级 | 细分材料/部件 | 对目标产业的作用 | 价值/稀缺性 | 卡脖子程度 | A股候选 | 纳入主线判断 |
| --- | --- | --- | --- | --- | --- | --- |
| Product BOM | 核心部件 | 决定性能 | 高 | High | 测试公司 | Core |

## 5. 产业链核心环节价值分布
| 产业链环节 | 细分领域/关键产品 | BOM成本占比/价值占比 | 核心技术壁垒 | 卡脖子程度 | 代表A股公司 | 公司环节地位 | 证据口径/备注 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 上游 | 核心部件 | 高 | 工艺 | High | 测试公司 | 核心环节龙头 | 官方资料 |

## 6. 竞争格局与核心壁垒
壁垒明确。

## 7. A股公司映射与核心地位判断
| 公司 | 代码 | 环节 | 细分领域 | 产业占比/暴露度 | 核心技术/产品 | 卡脖子相关性 | 环节地位 | 证据与备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 测试公司 | 000001 | 上游 | 核心部件 | 订单披露 | 核心产品 | High | 核心环节龙头 | 年报 |

## 8. 投资线索、交易跟踪与目标价情景
受益顺序：核心环节龙头、重要配套、间接受益、待验证。

| 机会类型 | 产业链逻辑 | 代表A股公司 | 验证里程碑 | 风险 |
| --- | --- | --- | --- | --- |
| 核心环节龙头 | 直接暴露 | 测试公司 | 订单 | 估值 |

## 9. 催化因素与产业传导路径
订单催化。

## 10. 风险提示
风险明确。

## 11. 数据来源、证据强度与待核验事项
证据强度明确。

| 结论/数据 | 来源 | 日期 | 置信度 |
| --- | --- | --- | --- |
| 核心部件直接受益 | 年报 | 2026-06-24 | High |
""",
        encoding="utf-8",
    )
    source_data = tmp_path / "source_data.json"
    source_data.write_text(
        json.dumps(
            {
                "sources": [
                    {"tool": "filing", "status": "ok", "confidence": "High"},
                    {"tool": "web", "status": "ok", "confidence": "High"},
                    {"tool": "sec-edgar", "status": "ok", "confidence": "High"},
                    {"tool": "akshare", "status": "ok", "confidence": "Medium"},
                    {"tool": "efinance", "status": "ok", "confidence": "Medium"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = report_quality.validate(report, source_data)
    assert result["passed"] is True
    assert result["score"] == result["total"]


def test_report_quality_fails_absolute_image_refs(tmp_path: Path) -> None:
    import report_quality

    image = tmp_path / "assets" / "chain.png"
    image.parent.mkdir()
    write_test_png(image)
    report = tmp_path / "report.md"
    report.write_text(
        f"""# 弱报告

## 0. 核心结论
投资线索、核心环节龙头、重要配套、间接受益。

![产业链图谱]({image})
""",
        encoding="utf-8",
    )
    source_data = tmp_path / "source_data.json"
    source_data.write_text(json.dumps({"sources": []}), encoding="utf-8")

    result = report_quality.validate(report, source_data)
    checks = {check["name"]: check for check in result["checks"]}
    assert checks["rendered_visual_assets"]["passed"] is True
    assert checks["relative_markdown_image_refs"]["passed"] is False


def test_report_quality_fails_remote_image_refs(tmp_path: Path) -> None:
    import report_quality

    report = tmp_path / "report.md"
    report.write_text(
        """# 弱报告

## 0. 核心结论
1. 核心价值判断。
2. 机会来自关键瓶颈。
3. 风险和不确定仍需跟踪。

![产业链图谱](https://example.com/chain.png)
""",
        encoding="utf-8",
    )
    source_data = tmp_path / "source_data.json"
    source_data.write_text(json.dumps({"sources": []}), encoding="utf-8")

    result = report_quality.validate(report, source_data)
    checks = {check["name"]: check for check in result["checks"]}
    assert checks["relative_markdown_image_refs"]["passed"] is False
    assert "https://example.com/chain.png" in checks["relative_markdown_image_refs"]["evidence"]


def test_report_quality_fails_invalid_or_tiny_images(tmp_path: Path) -> None:
    import report_quality

    image = tmp_path / "assets" / "chain.png"
    image.parent.mkdir()
    write_test_png(image, size=(120, 80))
    report = tmp_path / "report.md"
    report.write_text(
        """# 弱报告

## 0. 核心结论
投资线索、核心环节龙头、重要配套、间接受益。

![产业链图谱](assets/chain.png)
""",
        encoding="utf-8",
    )
    source_data = tmp_path / "source_data.json"
    source_data.write_text(json.dumps({"sources": []}), encoding="utf-8")

    result = report_quality.validate(report, source_data)
    checks = {check["name"]: check for check in result["checks"]}
    assert checks["rendered_visual_assets"]["passed"] is True
    assert checks["valid_image_files"]["passed"] is False


def test_report_quality_fails_missing_opportunity_table(tmp_path: Path) -> None:
    import report_quality

    image = tmp_path / "assets" / "chain.png"
    image.parent.mkdir()
    write_test_png(image)
    report = tmp_path / "report.md"
    report.write_text(
        """# 弱报告

## 0. 核心结论
核心环节龙头和重要配套。

## 1. 研究对象、边界与口径
边界。

## 2. 行业背景与需求驱动
需求。

## 3. 产业链全景图谱
![产业链图谱](assets/chain.png)

## 4. 上游材料、部件与制程要素挖掘
| 上游层级 | 细分材料/部件 | 对目标产业的作用 | 价值/稀缺性 | 卡脖子程度 | A股候选 | 纳入主线判断 |
| --- | --- | --- | --- | --- | --- | --- |
| Product BOM | 核心部件 | 决定性能 | 高 | High | 测试公司 | Core |

## 5. 产业链核心环节价值分布
| 产业链环节 | 细分领域/关键产品 | BOM成本占比/价值占比 | 核心技术壁垒 | 卡脖子程度 | 代表A股公司 | 公司环节地位 | 证据口径/备注 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 上游 | 核心部件 | 高 | 工艺 | High | 测试公司 | 核心环节龙头 | 官方资料 |

## 6. 竞争格局与核心壁垒
壁垒。

## 7. A股公司映射与核心地位判断
| 公司 | 代码 | 环节 | 细分领域 | 产业占比/暴露度 | 核心技术/产品 | 卡脖子相关性 | 环节地位 | 证据与备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 测试公司 | 000001 | 上游 | 核心部件 | 订单披露 | 核心产品 | High | 核心环节龙头 | 年报 |

## 8. 投资线索、交易跟踪与目标价情景
只有叙述，没有机会表。

## 9. 催化因素与产业传导路径
订单催化。

## 10. 风险提示
风险。

## 11. 数据来源、证据强度与待核验事项
| 结论/数据 | 来源 | 日期 | 置信度 |
| --- | --- | --- | --- |
| 核心部件直接受益 | 年报 | 2026-06-24 | High |
""",
        encoding="utf-8",
    )
    source_data = tmp_path / "source_data.json"
    source_data.write_text(
        json.dumps(
            {
                "sources": [
                    {"tool": "filing", "status": "ok", "confidence": "High"},
                    {"tool": "web", "status": "ok", "confidence": "High"},
                    {"tool": "sec-edgar", "status": "ok", "confidence": "High"},
                    {"tool": "akshare", "status": "ok", "confidence": "Medium"},
                    {"tool": "efinance", "status": "ok", "confidence": "Medium"},
                ]
            }
        ),
        encoding="utf-8",
    )

    result = report_quality.validate(report, source_data)
    checks = {check["name"]: check for check in result["checks"]}
    assert checks["investment_opportunity_table"]["passed"] is False


def test_report_quality_fails_missing_source_summary(tmp_path: Path) -> None:
    import report_quality

    image = tmp_path / "assets" / "chain.png"
    image.parent.mkdir()
    write_test_png(image)
    report = tmp_path / "report.md"
    report.write_text(
        """# 弱报告

## 0. 核心结论
核心环节龙头、重要配套、投资线索、待验证。

## 1. 研究对象、边界与口径
边界。

## 2. 行业背景与需求驱动
需求。

## 3. 产业链全景图谱
![产业链图谱](assets/chain.png)

## 4. 上游材料、部件与制程要素挖掘
| 上游层级 | 细分材料/部件 | 对目标产业的作用 | 价值/稀缺性 | 卡脖子程度 | A股候选 | 纳入主线判断 |
| --- | --- | --- | --- | --- | --- | --- |
| Product BOM | 核心部件 | 决定性能 | 高 | High | 测试公司 | Core |

## 5. 产业链核心环节价值分布
| 产业链环节 | 细分领域/关键产品 | BOM成本占比/价值占比 | 核心技术壁垒 | 卡脖子程度 | 代表A股公司 | 公司环节地位 | 证据口径/备注 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 上游 | 核心部件 | 高 | 工艺 | High | 测试公司 | 核心环节龙头 | 官方资料 |

## 6. 竞争格局与核心壁垒
壁垒。

## 7. A股公司映射与核心地位判断
| 公司 | 代码 | 环节 | 细分领域 | 产业占比/暴露度 | 核心技术/产品 | 卡脖子相关性 | 环节地位 | 证据与备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 测试公司 | 000001 | 上游 | 核心部件 | 订单披露 | 核心产品 | High | 核心环节龙头 | 年报 |

## 8. 投资线索、交易跟踪与目标价情景
| 机会类型 | 产业链逻辑 | 代表A股公司 | 验证里程碑 | 风险 |
| --- | --- | --- | --- | --- |
| 核心环节龙头 | 直接暴露 | 测试公司 | 订单 | 估值 |

## 9. 催化因素与产业传导路径
订单催化。

## 10. 风险提示
风险。

## 11. 数据来源、证据强度与待核验事项
只有文字，没有来源表。
""",
        encoding="utf-8",
    )
    source_data = tmp_path / "source_data.json"
    source_data.write_text(
        json.dumps(
            {
                "sources": [
                    {"tool": "filing", "status": "ok", "confidence": "High"},
                    {"tool": "web", "status": "ok", "confidence": "High"},
                    {"tool": "sec-edgar", "status": "ok", "confidence": "High"},
                    {"tool": "akshare", "status": "ok", "confidence": "Medium"},
                    {"tool": "efinance", "status": "ok", "confidence": "Medium"},
                ]
            }
        ),
        encoding="utf-8",
    )

    result = report_quality.validate(report, source_data)
    checks = {check["name"]: check for check in result["checks"]}
    assert checks["claim_level_source_summary"]["passed"] is False


def test_report_quality_fails_runtime_logs_and_missing_assets(tmp_path: Path) -> None:
    import report_quality

    report = tmp_path / "report.md"
    report.write_text(
        """# 弱报告

## 0. 核心结论
RemoteDisconnected and baostock should not appear.
""",
        encoding="utf-8",
    )
    source_data = tmp_path / "source_data.json"
    source_data.write_text(json.dumps({"sources": []}), encoding="utf-8")

    result = report_quality.validate(report, source_data)
    checks = {check["name"]: check for check in result["checks"]}
    assert result["passed"] is False
    assert checks["no_adapter_logs_in_report"]["passed"] is False
    assert checks["rendered_visual_assets"]["passed"] is False
    assert checks["source_trail_present"]["passed"] is False


def test_render_source_trail_table_seven_columns() -> None:
    from public_data import SourceTrail, render_source_trail_table

    trail = SourceTrail()
    trail.record(
        tool="akshare",
        function_or_path="stock_board_concept_cons_em",
        subject="创新药概念成分",
        payload=[{"code": "600276"}, {"code": "300363"}],
        error=None,
        confidence="Low",
    )
    trail.record(
        tool="baostock",
        function_or_path="query_history_k_data_plus",
        subject="恒瑞医药日K",
        payload=None,
        error="login failed",
    )
    md = render_source_trail_table(trail.to_list())
    lines = md.strip().split("\n")
    assert len(lines) == 4  # header + sep + 2 rows
    header_cols = [c.strip() for c in lines[0].split("|")[1:-1]]
    assert len(header_cols) == 7
    assert "可用" in lines[2]
    assert "失败" in lines[3]
    assert "login failed" in lines[3]
    assert "2" in lines[2]  # row count


def test_render_source_trail_table_accepts_entries_directly() -> None:
    from public_data import SourceEntry, render_source_trail_table

    entry = SourceEntry(
        tool="filing",
        function_or_path="2025_annual_report.pdf",
        subject="恒瑞医药年报",
        status="ok",
        rows=1,
        confidence="High",
    )
    md = render_source_trail_table([entry])
    assert "恒瑞医药年报" in md
    assert "High" in md


def test_try_akshare_concept_cons_returns_list(monkeypatch: pytest.MonkeyPatch) -> None:
    import public_data

    def fake_call(_concept: str):
        return [{"代码": "600276", "名称": "恒瑞医药"}], None

    monkeypatch.setattr(public_data, "try_akshare_concept_cons", fake_call)
    payload, error = public_data.try_akshare_concept_cons("创新药")
    assert error is None
    assert payload is not None
    assert len(payload) == 1
    assert payload[0]["代码"] == "600276"


def test_try_akshare_board_cons_returns_list(monkeypatch: pytest.MonkeyPatch) -> None:
    import public_data

    def fake_call(_board: str):
        return [{"代码": "600276", "名称": "恒瑞医药"}], None

    monkeypatch.setattr(public_data, "try_akshare_board_cons", fake_call)
    payload, error = public_data.try_akshare_board_cons("化学制药")
    assert error is None
    assert payload is not None
    assert len(payload) == 1


def test_try_akshare_board_fund_flow_concept(monkeypatch: pytest.MonkeyPatch) -> None:
    import public_data

    def fake_call(_board: str, *, is_concept: bool = False):
        return [{"板块名称": "创新药", "主力净流入": "1000万"}], None

    monkeypatch.setattr(public_data, "try_akshare_board_fund_flow", fake_call)
    payload, error = public_data.try_akshare_board_fund_flow("创新药", is_concept=True)
    assert error is None
    assert payload is not None
    assert payload[0]["板块名称"] == "创新药"
