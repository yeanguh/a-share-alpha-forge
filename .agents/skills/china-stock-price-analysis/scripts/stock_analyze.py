#!/usr/bin/env python3
"""
A股股价多维度估值分析脚本
直接调用QVeris API获取实时行情，执行多维度估值计算，输出格式化报告。
"""

import argparse
import json
import os
import sys
from typing import Dict, Optional, Any

import requests

# 行业默认合理PE区间
INDUSTRY_PE_RANGES = {
    "消费电子龙头": (20, 30),
    "白酒龙头": (25, 35),
    "半导体设备": (30, 45),
    "传统制造业": (10, 18),
    "银行": (5, 12),
    "地产": (5, 15),
    "医药": (20, 35),
    "新能源": (25, 40),
}

# 行业默认合理PB区间
INDUSTRY_PB_RANGES = {
    "消费电子龙头": (3, 5),
    "白酒龙头": (5, 10),
    "半导体设备": (4, 8),
    "传统制造业": (1, 3),
    "银行": (0.5, 1.5),
    "地产": (0.5, 2),
}


class AStockAnalyzer:
    """A股多维度估值分析器"""

    def __init__(self, qveris_api_key: Optional[str] = None):
        self.qveris_api_key = qveris_api_key or os.getenv("QVERIS_API_KEY")
        if not self.qveris_api_key:
            raise ValueError("QVERIS_API_KEY environment variable is required")
        
        self.base_url = "https://qveris.ai/api/v1"
        self.tool_id = "thsifind.real_time_quotation.v1"

    def get_real_time_quote(self, code: str, discovery_id: Optional[str] = None) -> Dict[str, Any]:
        """直接调用QVeris API获取实时行情数据"""
        url = f"{self.base_url}/tools/execute"
        headers = {
            "Authorization": f"Bearer {self.qveris_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "tool_id": self.tool_id,
            "search_id": discovery_id,
            "parameters": {"codes": code}
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("success"):
            raise ValueError(f"QVeris API request failed: {data}")
        
        result = data["result"]
        if result.get("status_code") != 200 or not result.get("data"):
            raise ValueError(f"QVeris tool execution failed: {result}")
        
        return result["data"][0][0]  # 返回第一个股票的数据

    @staticmethod
    def judge_pe(pe: float, industry: str) -> str:
        """根据PE判断估值"""
        if industry not in INDUSTRY_PE_RANGES:
            return f"PE {pe:.2f} (行业{industry}无预设区间)"
        
        low, high = INDUSTRY_PE_RANGES[industry]
        if pe < low:
            return f"PE {pe:.2f} → **低估** (区间 {low}~{high})"
        elif pe <= high:
            mid = (low + high) / 2
            if pe < mid:
                return f"PE {pe:.2f} → **合理偏低** (区间 {low}~{high})"
            else:
                return f"PE {pe:.2f} → **合理偏高** (区间 {low}~{high})"
        else:
            return f"PE {pe:.2f} → **高估** (区间 {low}~{high})"

    @staticmethod
    def judge_pb(pb: float, industry: str) -> str:
        """根据PB判断估值"""
        if industry not in INDUSTRY_PB_RANGES:
            return f"PB {pb:.2f} (行业{industry}无预设区间)"
        
        low, high = INDUSTRY_PB_RANGES[industry]
        if pb < low:
            return f"PB {pb:.2f} → **低估** (区间 {low}~{high})"
        elif pb <= high:
            return f"PB {pb:.2f} → **合理** (区间 {low}~{high})"
        else:
            return f"PB {pb:.2f} → **高估** (区间 {low}~{high})"

    @staticmethod
    def judge_pe(pe: float, industry: str) -> str:
        """根据PE判断估值"""
        if industry not in INDUSTRY_PE_RANGES:
            return f"PE {pe:.2f} (行业{industry}无预设区间)"
        
        low, high = INDUSTRY_PE_RANGES[industry]
        if pe < low:
            return f"PE {pe:.2f} → **低估** (区间 {low}~{high})"
        elif pe <= high:
            mid = (low + high) / 2
            if pe < mid:
                return f"PE {pe:.2f} → **合理偏低** (区间 {low}~{high})"
            else:
                return f"PE {pe:.2f} → **合理偏高** (区间 {low}~{high})"
        else:
            return f"PE {pe:.2f} → **高估** (区间 {low}~{high})"

    @staticmethod
    def judge_pb(pb: float, industry: str) -> str:
        """根据PB判断估值"""
        if industry not in INDUSTRY_PB_RANGES:
            return f"PB {pb:.2f} (行业{industry}无预设区间)"
        
        low, high = INDUSTRY_PB_RANGES[industry]
        if pb < low:
            return f"PB {pb:.2f} → **低估** (区间 {low}~{high})"
        elif pb <= high:
            return f"PB {pb:.2f} → **合理** (区间 {low}~{high})"
        else:
            return f"PB {pb:.2f} → **高估** (区间 {low}~{high})"

    @staticmethod
    def calculate_ev_ebitda(market_cap: float, net_debt: float, ebitda: float) -> Dict[str, float]:
        """计算EV/EBITDA"""
        ev = market_cap + net_debt
        ev_ebitda = ev / ebitda
        return {
            "ev": ev,
            "ebitda": ebitda,
            "ev_ebitda": ev_ebitda
        }

    @staticmethod
    def expected_valuation(eps_expected: float, industry: str) -> Dict[str, float]:
        """业绩预期法计算合理估值区间"""
        if industry not in INDUSTRY_PE_RANGES:
            return {}
        low_pe, high_pe = INDUSTRY_PE_RANGES[industry]
        low_val = eps_expected * low_pe
        high_val = eps_expected * high_pe
        mid_val = (low_val + high_val) / 2
        return {
            "low": low_val,
            "high": high_val,
            "mid": mid_val
        }

    def analyze(self, quote: Dict[str, Any], industry: str, 
                eps_expected: Optional[float] = None,
                ebitda: Optional[float] = None,
                net_debt: float = 0,
                consensus_target: Optional[float] = None) -> Dict[str, Any]:
        """完整分析流程
        quote: 已从QVeris获取的实时行情数据
        """
        result = {
            "code": quote["thscode"],
            "industry": industry,
            "quote": quote,
            "pe_judge": self.judge_pe(quote["pe_ttm"], industry),
            "pb_judge": self.judge_pb(quote["pbr_lf"], industry),
        }

        # 业绩预期法估值
        if eps_expected is not None:
            val_range = self.expected_valuation(eps_expected, industry)
            result["expected_valuation"] = val_range
            current_price = quote["latest"]
            if val_range:
                if current_price < val_range["low"]:
                    result["expected_comment"] = "当前价格低于合理估值下限，具备安全边际"
                elif current_price > val_range["high"]:
                    result["expected_comment"] = "当前价格高于合理估值上限，需警惕回调"
                else:
                    result["expected_comment"] = f"当前价格落在合理估值区间，中枢 {val_range['mid']:.2f}"

        # EV/EBITDA分析
        if ebitda is not None:
            market_cap = quote["mv"]
            ev_data = self.calculate_ev_ebitda(market_cap, net_debt, ebitda)
            result["ev_ebitda"] = ev_data

        # 一致性预期空间
        if consensus_target is not None:
            current_price = quote["latest"]
            upside = (consensus_target - current_price) / current_price * 100
            result["consensus_target"] = {
                "price": consensus_target,
                "upside_pct": upside
            }

        return result

    @staticmethod
    def print_report(result: Dict[str, Any]):
        """打印分析报告"""
        quote = result["quote"]
        print("\n" + "=" * 60)
        print(f"📊 {result['code']} 估值分析报告")
        print(f"⏱  数据时间: {quote['time']}")
        print("=" * 60)
        
        print(f"\n📍 当前股价: {quote['latest']:.2f} 元")
        print(f"📈 涨跌幅: {quote['changeRatio']:.2f}%")
        print(f"💰 成交额: {quote['amount'] / 100000000:.2f} 亿元")
        print(f"🏬 总市值: {quote['mv'] / 100000000:.2f} 亿元")
        
        print("\n📊 估值判断:")
        print(f"  {result['pe_judge']}")
        print(f"  {result['pb_judge']}")

        if "expected_valuation" in result and result["expected_valuation"]:
            ev = result["expected_valuation"]
            print(f"\n🎯 业绩预期法合理区间: {ev['low']:.2f} ~ {ev['high']:.2f} 元 (中枢 {ev['mid']:.2f})")
            print(f"💬 {result['expected_comment']}")

        if "ev_ebitda" in result:
            ed = result["ev_ebitda"]
            print(f"\n🔢 EV/EBITDA = {ed['ev_ebitda']:.2f}x")
            print(f"   (EV: {ed['ev']/100000000:.0f}亿, EBITDA: {ed['ebitda']:.0f}亿)")

        if "consensus_target" in result:
            ct = result["consensus_target"]
            print(f"\n🌟 券商一致性目标价: {ct['price']:.2f} 元 → 预期上涨空间: {ct['upside_pct']:.1f}%")

        print("\n" + "=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="A股多维度估值分析")
    parser.add_argument("code", help="股票代码，如 002475.SZ")
    parser.add_argument("--industry", default="消费电子龙头", help="行业分类，默认: 消费电子龙头")
    parser.add_argument("--eps-expected", type=float, help="一致预期EPS（当年/下一年）")
    parser.add_argument("--ebitda", type=float, help="年度EBITDA（亿元）")
    parser.add_argument("--net-debt", type=float, default=0, help="净负债（亿元），默认: 0")
    parser.add_argument("--consensus-target", type=float, help="券商一致目标价")
    # 也支持从JSON文件读取（可选）
    parser.add_argument("--json", help="从JSON文件读取行情数据（可选）")
    args = parser.parse_args()

    try:
        # 从JSON文件读取或直接API获取
        if args.json:
            with open(args.json, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "data" in data:
                    quote = data["data"][0][0]
                else:
                    quote = data
            analyzer = AStockAnalyzer(qveris_api_key=os.getenv("QVERIS_API_KEY", "json-input"))
        else:
            analyzer = AStockAnalyzer()
            # 我们之前discovery得到的discovery_id
            discovery_id = "c2ab2fb6-2e95-448f-a095-6362d2151496"
            quote = analyzer.get_real_time_quote(args.code, discovery_id)

        # 转换EBITDA和净负债到元（API返回市值单位是元）
        ebitda = args.ebitda * 100000000 if args.ebitda else None
        net_debt = args.net_debt * 100000000 if args.net_debt else 0

        result = analyzer.analyze(
            quote=quote,
            industry=args.industry,
            eps_expected=args.eps_expected,
            ebitda=ebitda,
            net_debt=net_debt,
            consensus_target=args.consensus_target
        )
        analyzer.print_report(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
