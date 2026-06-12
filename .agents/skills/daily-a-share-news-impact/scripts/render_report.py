#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"`{path}` must contain a JSON object")
    return payload


def text(value: object, default: str = "-") -> str:
    if value is None:
        return default
    rendered = str(value).strip()
    return rendered if rendered else default


def numeric(value: object, suffix: str = "") -> str:
    if value == "" or value is None:
        return "-"
    if isinstance(value, int | float):
        return f"{value:g}{suffix}"
    return f"{value}{suffix}"


def cell(value: object) -> str:
    return text(value).replace("|", "｜").replace("\n", " ")


def score(value: object) -> str:
    return numeric(value, "/5")


def stock_label(stock: dict[str, Any]) -> str:
    return f"{text(stock.get('ticker'))} {text(stock.get('name'))}"


def candidate_sector(candidate: dict[str, Any]) -> str:
    sectors = candidate.get("affected_sectors")
    if isinstance(sectors, list) and sectors:
        return "、".join(text(sector) for sector in sectors)
    sector = candidate.get("sector")
    return text(sector, "待补充")


def estimate_market_direction(assembled: dict[str, Any]) -> str:
    rankings = assembled.get("rankings", {})
    positive = rankings.get("positive", []) if isinstance(rankings, dict) else []
    negative = rankings.get("negative", []) if isinstance(rankings, dict) else []
    positive_score = sum(float(item.get("impact_score", 0)) for item in positive if isinstance(item, dict))
    negative_score = sum(float(item.get("impact_score", 0)) for item in negative if isinstance(item, dict))
    gap = positive_score - negative_score
    if gap >= 8:
        return "偏强"
    if gap >= 2:
        return "震荡偏强"
    if gap <= -8:
        return "偏弱"
    if gap <= -2:
        return "震荡偏弱"
    return "震荡"


def fund_flow_lines(fund_flow: dict[str, Any]) -> list[str]:
    return [
        f"- 资金方向：{text(fund_flow.get('direction'))}",
        f"- 央行公开市场操作：{text(fund_flow.get('pbc_open_market_operation_summary'), '未记录，需在报告中说明缺口')}",
        f"- 成交额与量能：{text(fund_flow.get('turnover_summary'), '成交额/量能数据不足')}",
        f"- 主力/ETF/融资/北向：{text(fund_flow.get('main_flow_summary'), '分项资金数据不足')}",
        f"- 行业流向：{text(fund_flow.get('sector_flow_summary'), '行业流向数据不足')}",
        f"- 市场宽度：{text(fund_flow.get('breadth_summary'), '宽度数据不足')}",
        f"- 数据质量：{text(fund_flow.get('data_quality'), '未标注')}",
    ]


def mainline_table(rows: list[dict[str, Any]]) -> list[str]:
    output = [
        "| 排名 | 板块/概念 | 方向 | 分数 | 主线依据 | 资金/量价确认 | 风险提示 |",
        "| ---: | --- | --- | ---: | --- | --- | --- |",
    ]
    if not rows:
        output.append("| - | 暂无达标主线 | - | - | 板块候选不足 | 量价确认不足 | 保持观察 |")
        return output
    for row in rows:
        output.append(
            "| "
            + " | ".join(
                [
                    cell(row.get("rank")),
                    cell(row.get("title")),
                    cell(row.get("direction")),
                    cell(score(row.get("impact_score"))),
                    f"强度{score(row.get('magnitude'))}，广度{score(row.get('breadth'))}",
                    f"流动性{score(row.get('liquidity'))}，量价{score(row.get('price_volume'))}",
                    "需跟踪持续性",
                ]
            )
            + " |"
        )
    return output


def leader_table(rows: list[dict[str, Any]]) -> list[str]:
    output = [
        "| 排名 | 股票 | 所属主线 | 市值(亿元) | 龙头依据 | 14日K线/量能 | 散户VOC/情绪 | 资金认可度 | 入选状态 |",
        "| ---: | --- | --- | ---: | --- | --- | --- | --- | --- |",
    ]
    if not rows:
        output.append("| - | 暂无达标龙头 | - | - | 龙头确认不足 | 量价数据不足 | VOC数据不足 | - | 未入选推荐列 |")
        return output
    for rank, row in enumerate(rows, start=1):
        output.append(
            "| "
            + " | ".join(
                [
                    str(rank),
                    cell(stock_label(row)),
                    cell(row.get("sector")),
                    cell(numeric(row.get("market_cap_billion"))),
                    f"事件关联{score(row.get('event_alignment'))}",
                    f"趋势{score(row.get('trend_score'))}，量能{score(row.get('volume_score'))}",
                    cell(row.get("retail_voc_summary") or f"情绪{score(row.get('retail_sentiment'))}"),
                    score(row.get("capital_recognition")),
                    cell(row.get("leader_role") or row.get("eligible_for_recommendation")),
                ]
            )
            + " |"
        )
    return output


def sector_screening_table(assembled: dict[str, Any]) -> list[str]:
    output = [
        "| 方向 | 排名 | 板块/主题 | 分数 | 关键资讯 | 资金/量价确认 | 是否进入个股筛选 |",
        "| --- | ---: | --- | ---: | --- | --- | --- |",
    ]
    sector_rankings = assembled.get("sector_rankings", {})
    rows: list[dict[str, Any]] = []
    if isinstance(sector_rankings, dict):
        for direction in ("positive", "negative"):
            ranked = sector_rankings.get(direction, [])
            rows.extend(row for row in ranked if isinstance(row, dict))
    if not rows:
        output.append("| - | - | 暂无板块候选 | - | 候选不足 | 量价不足 | 否 |")
        return output
    gate = assembled.get("threshold_config", {}).get("beneficiary_sector_gate", {})
    for row in rows:
        direction = text(row.get("direction"))
        enters = "是"
        if direction == "positive":
            enters = (
                "是"
                if float(row.get("impact_score", 0)) >= float(gate.get("impact_score_min", 0))
                and float(row.get("price_volume", 0)) >= float(gate.get("price_volume_min", 0))
                and float(row.get("liquidity", 0)) >= float(gate.get("liquidity_min", 0))
                else "观察"
            )
        output.append(
            "| "
            + " | ".join(
                [
                    cell(direction),
                    cell(row.get("rank")),
                    cell(row.get("title")),
                    cell(score(row.get("impact_score"))),
                    "结构化候选",
                    f"流动性{score(row.get('liquidity'))}，量价{score(row.get('price_volume'))}",
                    enters,
                ]
            )
            + " |"
        )
    return output


def candidate_table(rows: list[dict[str, Any]], direction: str) -> list[str]:
    company_header = "可能受益A股公司" if direction == "positive" else "可能承压A股公司"
    output = [
        f"| 排名 | 分数 | 资讯 | 对应板块 | 影响逻辑 | {company_header} | K线/量能参考 | 短期影响 | 来源 |",
        "| ---: | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    if not rows:
        output.append("| - | - | 暂无达标事件 | - | 候选不足 | - | - | - | - |")
        return output
    for row in rows:
        output.append(
            "| "
            + " | ".join(
                [
                    cell(row.get("rank")),
                    cell(score(row.get("impact_score"))),
                    cell(row.get("title")),
                    cell(candidate_sector(row)),
                    "需结合板块与资金确认",
                    "见个股筛选结果",
                    f"量价{score(row.get('price_volume'))}",
                    "一至三个交易日观察",
                    cell(row.get("source") or "结构化输入"),
                ]
            )
            + " |"
        )
    return output


def stock_table(rows: list[dict[str, Any]], pressure: bool = False) -> list[str]:
    if pressure:
        output = [
            "| 股票 | 市值(亿元) | 板块 | 入选状态 | 14日K线 | 14日量能 | 散户VOC/情绪 | 资金认可度 | 承压因素 | 风险 | 综合评级 | 操作倾向 |",
            "| --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    else:
        output = [
            "| 股票 | 市值(亿元) | 板块 | 入选状态 | 14日K线 | 14日量能 | 机构趋势 | 散户VOC/情绪 | 资金认可度 | 机会 | 风险 | 综合评级 | 操作倾向 |",
            "| --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    if not rows:
        cols = 12 if pressure else 13
        output.append("| " + " | ".join(["暂无达标个股"] + ["-"] * (cols - 1)) + " |")
        return output
    for row in rows:
        common = [
            cell(stock_label(row)),
            cell(numeric(row.get("market_cap_billion"))),
            cell(row.get("sector")),
            cell(row.get("eligible_for_recommendation")),
            score(row.get("trend_score")),
            score(row.get("volume_score")),
        ]
        if pressure:
            values = [
                *common,
                cell(row.get("retail_voc_summary") or f"情绪{score(row.get('retail_sentiment'))}"),
                score(row.get("capital_recognition")),
                cell(row.get("exclusion_reason") or "负向事件压力"),
                score(row.get("risk_score")),
                cell(row.get("research_rating")),
                cell(row.get("operation_tendency")),
            ]
        else:
            values = [
                *common,
                score(row.get("institutional_trend_score")),
                cell(row.get("retail_voc_summary") or f"情绪{score(row.get('retail_sentiment'))}"),
                score(row.get("capital_recognition")),
                cell(row.get("exclusion_reason") or "通过机会门槛"),
                score(row.get("risk_score")),
                cell(row.get("research_rating")),
                cell(row.get("operation_tendency")),
            ]
        output.append("| " + " | ".join(values) + " |")
    return output


def excluded_table(rows: list[dict[str, Any]]) -> list[str]:
    output = ["| 股票 | 原因 |", "| --- | --- |"]
    if not rows:
        output.append("| 暂无 | - |")
        return output
    for row in rows[:20]:
        output.append(f"| {cell(stock_label(row))} | {cell(row.get('exclusion_reason'))} |")
    return output


def render_report(assembled: dict[str, Any]) -> str:
    window = assembled.get("window", {}) if isinstance(assembled.get("window"), dict) else {}
    fund_flow = assembled.get("fund_flow", {}) if isinstance(assembled.get("fund_flow"), dict) else {}
    rankings = assembled.get("rankings", {}) if isinstance(assembled.get("rankings"), dict) else {}
    direction = estimate_market_direction(assembled)
    warnings = assembled.get("warnings", [])
    threshold_config = assembled.get("threshold_config", {})
    lines: list[str] = [
        "# A股投资资讯影响简报",
        "",
        f"时间窗：{text(window.get('start'))} 至 {text(window.get('end'))}（北京时间）",
        f"结论：短期市场预计【{direction}】",
        f"核心驱动：正负催化按结构化评分排序，资金方向为【{text(fund_flow.get('direction'))}】，数据质量为【{text(fund_flow.get('data_quality'))}】。",
        "说明：本简报仅作信息研究，不构成个性化投资建议。",
        "数据源：免费可用接口优先；未启用付费行情/终端接口。",
        f"阈值版本：{text(threshold_config.get('version'), 'unknown')}",
        "",
        "## 大盘整体情绪",
        "",
        "- 指数状态：需结合当日指数收盘与盘前跨市场线索复核。",
        f"- 市场宽度：{text(fund_flow.get('breadth_summary'), '宽度数据不足')}",
        "- 风险偏好：以主线板块、资金方向和量价确认共同判断。",
        f"- 情绪结论：【{direction}】。",
        "",
        "## 资金方向/热度",
        "",
        *fund_flow_lines(fund_flow),
        "",
        "## 每日主线板块/概念与龙头个股",
        "",
        "### 前五主线板块/概念",
        "",
        *mainline_table(assembled.get("daily_mainlines", [])),
        "",
        "### 主线龙头个股 Top 10",
        "",
        *leader_table(assembled.get("leading_stocks", [])),
        "",
        "## 正向负向事件Top",
        "",
        "### 资讯筛出的板块候选",
        "",
        *sector_screening_table(assembled),
        "",
        "### 正向事件 Top 10",
        "",
        *candidate_table(rankings.get("positive", []), "positive"),
        "",
        "### 负向事件 Top 10",
        "",
        *candidate_table(rankings.get("negative", []), "negative"),
        "",
        "## 个股机会的筛选结果",
        "",
        "### 可能受益A股公司",
        "",
        *stock_table(assembled.get("eligible_beneficiaries", [])),
        "",
        "### 可能承压A股公司",
        "",
        *stock_table(assembled.get("eligible_pressure", []), pressure=True),
        "",
        "### 未入选/观察列表",
        "",
        *excluded_table(assembled.get("excluded_stocks", [])),
        "",
        "## 短期市场判断",
        "",
        f"- 方向：{direction}。",
        f"- 理由：正向事件 {len(rankings.get('positive', []))} 条，负向事件 {len(rankings.get('negative', []))} 条；资金方向为 {text(fund_flow.get('direction'))}。",
        "- 多空结构：优先观察高分主线能否获得成交额、主力资金和量价延续确认。",
        f"- 资金方向：{text(fund_flow.get('main_flow_summary'), '分项资金数据不足')}",
        f"- 个股结论：受益达标 {len(assembled.get('eligible_beneficiaries', []))} 只，承压达标 {len(assembled.get('eligible_pressure', []))} 只。",
        "- 主要上行风险：政策或产业催化超预期，资金由结构性流入扩散。",
        "- 主要下行风险：成交额回落、汇率/利率扰动、强主题拥挤后分化。",
        "- 观察指标：成交额、行业主力净流向、ETF/融资数据、汇率、利率、商品价格和关键政策发布时间。",
        "",
        "## 数据留痕与复盘",
        "",
        f"- 日报归档：local/{text(window.get('end'), 'YYYY-MM-DD')[:10]}/",
        "- 收盘复盘：15:00后补充 close_review.json，校准板块命中、个股命中和策略偏差。",
        "- 周期复盘：聚合结果保存到 local/reviews/，不因单日噪音调整策略。",
    ]
    if warnings:
        lines.extend(["", "### 数据缺口/警示", ""])
        lines.extend(f"- {text(warning)}" for warning in warnings)
    return "\n".join(lines).rstrip() + "\n"


def render_command(args: argparse.Namespace) -> None:
    assembled = load_json_object(Path(args.assembled))
    report = render_report(assembled)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
        sys.stdout.write(json.dumps({"output": str(output)}, ensure_ascii=False, indent=2))
        sys.stdout.write("\n")
        return
    sys.stdout.write(report)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render assembled A-share scoring data as a Markdown report.")
    parser.add_argument("--assembled", required=True, help="Path to assembled scoring JSON.")
    parser.add_argument("--output", help="Optional path to write Markdown report.")
    parser.set_defaults(func=render_command)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
