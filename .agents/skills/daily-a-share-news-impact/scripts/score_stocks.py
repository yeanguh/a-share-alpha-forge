#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from threshold_config import get_number, load_thresholds

DirectionalRole = str
DEFAULT_THRESHOLDS = load_thresholds()
MIN_MARKET_CAP_BILLION = get_number(DEFAULT_THRESHOLDS, "market_cap_billion", "min")
MAX_MARKET_CAP_BILLION = get_number(DEFAULT_THRESHOLDS, "market_cap_billion", "max")


@dataclass(frozen=True)
class MarketCapRange:
    minimum_billion: float = MIN_MARKET_CAP_BILLION
    maximum_billion: float = MAX_MARKET_CAP_BILLION

    def __post_init__(self) -> None:
        if self.minimum_billion <= 0:
            raise ValueError("`min_market_cap_billion` must be positive")
        if self.maximum_billion < self.minimum_billion:
            raise ValueError("`max_market_cap_billion` must be greater than or equal to `min_market_cap_billion`")

    def contains(self, market_cap_billion: float | None) -> bool:
        if market_cap_billion is None:
            return False
        return self.minimum_billion <= market_cap_billion <= self.maximum_billion

    @property
    def description(self) -> str:
        return f"{self.minimum_billion:g}-{self.maximum_billion:g}亿元"


@dataclass(frozen=True)
class StockObservation:
    ticker: str
    name: str
    sector: str
    directional_role: DirectionalRole
    market_cap_billion: float | None
    trend_score: float
    volume_score: float
    retail_sentiment: float
    capital_recognition: float
    event_alignment: float
    risk_score: float
    institutional_trend_score: float = 0.0
    retail_voc_summary: str = ""
    external_data: dict[str, Any] | None = None
    market_cap_range: MarketCapRange = MarketCapRange()
    threshold_config: dict[str, Any] = field(default_factory=load_thresholds)

    def threshold(self, *path: str) -> float:
        return get_number(self.threshold_config, *path)

    @property
    def crowding_risk_sector(self) -> bool:
        return any(marker in self.sector for marker in ("高位", "拥挤", "过热", "追涨"))

    @property
    def disconfirmation_risk_sector(self) -> bool:
        return any(marker in self.sector for marker in ("证伪", "传闻落空", "澄清", "辟谣"))

    @property
    def observation_only_pressure_sector(self) -> bool:
        return self.crowding_risk_sector or self.disconfirmation_risk_sector

    @property
    def cyclical_resource_sector(self) -> bool:
        return any(marker in self.sector for marker in ("有色", "金属", "稀土", "钨", "锡", "铝", "煤", "钢铁"))

    @property
    def retail_voc_quality_score(self) -> float:
        if self.retail_sentiment == 0:
            return 2.2
        distance_from_balanced = abs(self.retail_sentiment - 3.0)
        return round(max(1.0, 4.0 - 1.2 * distance_from_balanced), 2)

    @property
    def research_score(self) -> float:
        weights = self.threshold_config["scoring_weights"]["research_score"]
        return round(
            weights["trend"] * self.trend_score
            + weights["volume"] * self.volume_score
            + weights["retail_voc_quality"] * self.retail_voc_quality_score
            + weights["capital_recognition"] * self.capital_recognition
            + weights["event_alignment"] * self.event_alignment
            + weights["institutional_trend"] * self.institutional_trend_score
            + weights["risk"] * self.risk_score,
            2,
        )

    @property
    def beneficiary_quality_score(self) -> float:
        weights = self.threshold_config["scoring_weights"]["beneficiary_quality_score"]
        return round(
            weights["trend"] * self.trend_score
            + weights["volume"] * self.volume_score
            + weights["capital_recognition"] * self.capital_recognition
            + weights["event_alignment"] * self.event_alignment
            + weights["institutional_trend"] * self.institutional_trend_score
            + weights["retail_voc_quality"] * self.retail_voc_quality_score
            + weights["risk"] * self.risk_score,
            2,
        )

    @property
    def research_rating(self) -> str:
        if self.risk_score >= 4.2 and self.research_score < 3.2:
            return "风险回避"
        if self.research_score >= 3.8 and self.capital_recognition >= 3.5 and self.risk_score <= 3.2:
            return "高关注"
        if self.research_score >= 3.2 and self.risk_score <= 3.8:
            return "关注"
        if self.research_score >= 2.6:
            return "中性观察"
        if self.risk_score >= 3.8:
            return "风险回避"
        return "谨慎观察"

    @property
    def operation_tendency(self) -> str:
        if not self.market_cap_in_range:
            if self.directional_role == "pressure":
                return "仅作风险跟踪"
            return "仅作主题跟踪"
        if self.directional_role == "pressure":
            if self.eligible_for_recommendation:
                return "风险回避观察"
            return "仅作风险跟踪"
        if self.research_rating == "风险回避":
            return "风险回避观察"
        if self.event_alignment < 3:
            return "仅作主题跟踪"
        if self.risk_score >= 3.8:
            return "回撤后再评估"
        if self.volume_score < 3:
            return "等待放量确认"
        if self.institutional_trend_score < 3.5:
            return "等待机构趋势确认"
        if self.capital_recognition >= 3.8 and self.trend_score >= 3.5:
            return "趋势跟踪观察"
        return "事件落地后再评估"

    @property
    def eligible_for_recommendation(self) -> bool:
        if not self.market_cap_in_range:
            return False
        if self.directional_role == "beneficiary":
            return (
                self.event_alignment >= self.threshold("stock_gates", "beneficiary", "event_alignment_min")
                and self.trend_score >= self.threshold("stock_gates", "beneficiary", "trend_min")
                and self.volume_score >= self.threshold("stock_gates", "beneficiary", "volume_min")
                and self.capital_recognition >= self.threshold("stock_gates", "beneficiary", "capital_recognition_min")
                and self.institutional_trend_score
                >= self.threshold("stock_gates", "beneficiary", "institutional_trend_min")
                and (
                    not self.cyclical_resource_sector
                    or (
                        self.trend_score >= self.threshold("stock_gates", "resource_beneficiary", "trend_min")
                        and self.volume_score >= self.threshold("stock_gates", "resource_beneficiary", "volume_min")
                        and self.capital_recognition
                        >= self.threshold("stock_gates", "resource_beneficiary", "capital_recognition_min")
                    )
                )
                and (
                    self.retail_sentiment < self.threshold("stock_gates", "beneficiary", "retail_hot_min")
                    or (
                        self.capital_recognition
                        >= self.threshold("stock_gates", "beneficiary", "retail_hot_capital_min")
                        and self.volume_score >= self.threshold("stock_gates", "beneficiary", "retail_hot_volume_min")
                    )
                )
                and self.risk_score <= self.threshold("stock_gates", "beneficiary", "risk_max")
                and self.research_rating != "风险回避"
            )
        if self.directional_role == "pressure":
            return (
                self.event_alignment >= self.threshold("stock_gates", "pressure", "event_alignment_min")
                and self.trend_score <= self.threshold("stock_gates", "pressure", "trend_max")
                and self.capital_recognition <= self.threshold("stock_gates", "pressure", "capital_recognition_max")
                and (
                    self.volume_score >= self.threshold("stock_gates", "pressure", "volume_min")
                    or self.risk_score >= self.threshold("stock_gates", "pressure", "risk_min")
                )
                and (
                    not self.observation_only_pressure_sector
                    or (
                        self.trend_score <= self.threshold("stock_gates", "observation_pressure", "trend_max")
                        and self.capital_recognition
                        <= self.threshold("stock_gates", "observation_pressure", "capital_recognition_max")
                    )
                )
                and self.research_rating in {"风险回避", "谨慎观察", "中性观察"}
            )
        return False

    @property
    def market_cap_in_range(self) -> bool:
        return self.market_cap_range.contains(self.market_cap_billion)

    @property
    def exclusion_reason(self) -> str:
        if self.eligible_for_recommendation:
            return ""
        reasons: list[str] = []
        if self.market_cap_billion is None:
            reasons.append("未获取市值")
        elif not self.market_cap_in_range:
            reasons.append(f"市值不在{self.market_cap_range.description}区间")
        if self.directional_role not in {"beneficiary", "pressure"}:
            reasons.append("未设置受益/承压角色")
        if self.event_alignment < self.threshold("stock_gates", "beneficiary", "event_alignment_min"):
            reasons.append("事件关联不足")
        if self.directional_role == "beneficiary":
            if self.trend_score < self.threshold("stock_gates", "beneficiary", "trend_min"):
                reasons.append("14日走势不足")
            if self.volume_score < self.threshold("stock_gates", "beneficiary", "volume_min"):
                reasons.append("量能确认不足")
            if self.capital_recognition < self.threshold("stock_gates", "beneficiary", "capital_recognition_min"):
                reasons.append("资金认可度不足")
            if self.institutional_trend_score < self.threshold("stock_gates", "beneficiary", "institutional_trend_min"):
                reasons.append("机构趋势确认不足")
            if self.cyclical_resource_sector and (
                self.trend_score < self.threshold("stock_gates", "resource_beneficiary", "trend_min")
                or self.volume_score < self.threshold("stock_gates", "resource_beneficiary", "volume_min")
                or self.capital_recognition
                < self.threshold("stock_gates", "resource_beneficiary", "capital_recognition_min")
            ):
                reasons.append("周期资源需更强量价/资金确认")
            if self.retail_sentiment >= self.threshold("stock_gates", "beneficiary", "retail_hot_min") and (
                self.capital_recognition < self.threshold("stock_gates", "beneficiary", "retail_hot_capital_min")
                or self.volume_score < self.threshold("stock_gates", "beneficiary", "retail_hot_volume_min")
            ):
                reasons.append("散户情绪过热但主力/量能确认不足")
            if self.risk_score > self.threshold("stock_gates", "beneficiary", "risk_max"):
                reasons.append("风险过高")
            if self.research_rating == "风险回避":
                reasons.append("综合评级为风险回避")
        if self.directional_role == "pressure":
            if self.trend_score > self.threshold("stock_gates", "pressure", "trend_max"):
                reasons.append("14日承压走势不足")
            if self.capital_recognition > self.threshold("stock_gates", "pressure", "capital_recognition_max"):
                reasons.append("资金弱化不足")
            if (
                self.volume_score < self.threshold("stock_gates", "pressure", "volume_min")
                and self.risk_score < self.threshold("stock_gates", "pressure", "risk_min")
            ):
                reasons.append("承压量能/风险确认不足")
            if (
                self.trend_score >= self.threshold("stock_gates", "pressure", "strong_mainline_trend_min")
                and self.capital_recognition
                >= self.threshold("stock_gates", "pressure", "strong_mainline_capital_min")
            ):
                reasons.append("强主线反向风险，转观察")
            if self.crowding_risk_sector and (
                self.trend_score > self.threshold("stock_gates", "observation_pressure", "trend_max")
                or self.capital_recognition
                > self.threshold("stock_gates", "observation_pressure", "capital_recognition_max")
            ):
                reasons.append("高位拥挤仅作风险观察")
            if self.disconfirmation_risk_sector and (
                self.trend_score > self.threshold("stock_gates", "observation_pressure", "trend_max")
                or self.capital_recognition
                > self.threshold("stock_gates", "observation_pressure", "capital_recognition_max")
            ):
                reasons.append("题材证伪需破位确认")
            if self.research_rating not in {"风险回避", "谨慎观察", "中性观察"}:
                reasons.append("综合评级未支持承压")
        return "、".join(reasons)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ticker": self.ticker,
            "name": self.name,
            "sector": self.sector,
            "directional_role": self.directional_role,
            "market_cap_billion": "" if self.market_cap_billion is None else self.market_cap_billion,
            "research_score": self.research_score,
            "beneficiary_quality_score": self.beneficiary_quality_score,
            "research_rating": self.research_rating,
            "operation_tendency": self.operation_tendency,
            "eligible_for_recommendation": "yes" if self.eligible_for_recommendation else "no",
            "exclusion_reason": self.exclusion_reason,
            "trend_score": self.trend_score,
            "volume_score": self.volume_score,
            "retail_sentiment": self.retail_sentiment,
            "retail_voc_quality_score": self.retail_voc_quality_score,
            "capital_recognition": self.capital_recognition,
            "event_alignment": self.event_alignment,
            "institutional_trend_score": self.institutional_trend_score,
            "risk_score": self.risk_score,
        }
        if self.retail_voc_summary:
            payload["retail_voc_summary"] = self.retail_voc_summary
        if self.external_data:
            payload["external_data"] = self.external_data
        return payload


def require_score(value: object, field_name: str) -> float:
    if not isinstance(value, int | float):
        raise ValueError(f"`{field_name}` must be a number from 0 to 5")
    score = float(value)
    if score < 0 or score > 5:
        raise ValueError(f"`{field_name}` must be from 0 to 5")
    return score


def require_optional_market_cap(value: object) -> float | None:
    if value is None or value == "":
        return None
    if not isinstance(value, int | float):
        raise ValueError("`market_cap_billion` must be a number when present")
    market_cap = float(value)
    if market_cap <= 0:
        raise ValueError("`market_cap_billion` must be positive when present")
    return market_cap


def require_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"`{field_name}` must be a non-empty string")
    return value.strip()


def require_optional_text(value: object, field_name: str) -> str:
    if value is None:
        return ""
    return require_text(value, field_name)


def require_directional_role(value: object) -> DirectionalRole:
    if value is None:
        return "watch"
    role = require_text(value, "directional_role")
    if role not in {"beneficiary", "pressure", "watch"}:
        raise ValueError("`directional_role` must be beneficiary, pressure, or watch")
    return role


def load_observations(
    path: Path,
    market_cap_range: MarketCapRange | None = None,
    threshold_config: dict[str, Any] | None = None,
) -> list[StockObservation]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Stock observation file must contain a JSON array")

    observations: list[StockObservation] = []
    active_range = market_cap_range or MarketCapRange()
    active_threshold_config = threshold_config or load_thresholds()
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Stock observation #{index} must be an object")
        observations.append(
            StockObservation(
                ticker=require_text(item.get("ticker"), "ticker"),
                name=require_text(item.get("name"), "name"),
                sector=require_optional_text(item.get("sector"), "sector"),
                directional_role=require_directional_role(item.get("directional_role")),
                market_cap_billion=require_optional_market_cap(item.get("market_cap_billion")),
                trend_score=require_score(item.get("trend_score"), "trend_score"),
                volume_score=require_score(item.get("volume_score"), "volume_score"),
                retail_sentiment=require_score(item.get("retail_sentiment"), "retail_sentiment"),
                capital_recognition=require_score(item.get("capital_recognition"), "capital_recognition"),
                event_alignment=require_score(item.get("event_alignment"), "event_alignment"),
                risk_score=require_score(item.get("risk_score"), "risk_score"),
                institutional_trend_score=require_score(
                    item.get("institutional_trend_score", 0),
                    "institutional_trend_score",
                ),
                retail_voc_summary=require_optional_text(item.get("retail_voc_summary"), "retail_voc_summary"),
                external_data=item.get("external_data") if isinstance(item.get("external_data"), dict) else None,
                market_cap_range=active_range,
                threshold_config=active_threshold_config,
            )
        )
    return observations


def ranking_key(observation: StockObservation) -> tuple[float, ...]:
    if observation.directional_role == "beneficiary":
        return (
            observation.beneficiary_quality_score,
            observation.institutional_trend_score,
            observation.capital_recognition,
            observation.trend_score,
            -observation.risk_score,
        )
    return (
        observation.research_score,
        observation.capital_recognition,
        observation.trend_score,
        -observation.risk_score,
    )


def score_command(args: argparse.Namespace) -> None:
    threshold_config = load_thresholds(getattr(args, "threshold_config", None))
    min_market_cap = (
        args.min_market_cap_billion
        if args.min_market_cap_billion is not None
        else get_number(threshold_config, "market_cap_billion", "min")
    )
    max_market_cap = (
        args.max_market_cap_billion
        if args.max_market_cap_billion is not None
        else get_number(threshold_config, "market_cap_billion", "max")
    )
    market_cap_range = MarketCapRange(min_market_cap, max_market_cap)
    observations = load_observations(Path(args.input), market_cap_range, threshold_config)
    ranked = sorted(observations, key=ranking_key, reverse=True)
    write_json([observation.to_dict() for observation in ranked])


def write_json(payload: object) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Score A-share stock observations.")
    parser.add_argument("--input", required=True, help="Path to a JSON array of stock observations.")
    parser.add_argument(
        "--min-market-cap-billion",
        type=float,
        default=None,
        help="Minimum market cap in CNY billions for recommendation eligibility.",
    )
    parser.add_argument(
        "--max-market-cap-billion",
        type=float,
        default=None,
        help="Maximum market cap in CNY billions for recommendation eligibility.",
    )
    parser.add_argument("--threshold-config", help="Optional threshold config JSON. Defaults to skill config.")
    parser.set_defaults(func=score_command)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
