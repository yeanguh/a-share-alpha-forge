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
BSE_PREFIXES = ("4", "8", "920")
STAR_MARKET_PREFIXES = ("688", "689")
ST_MARKERS = ("ST", "*ST", "SST", "S*ST", "退市")


def normalized_ticker(value: str) -> str:
    return value.strip().upper().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")


def is_star_market_ticker(value: str) -> bool:
    return normalized_ticker(value).startswith(STAR_MARKET_PREFIXES)


def is_bse_ticker(value: str) -> bool:
    return normalized_ticker(value).startswith(BSE_PREFIXES)


def is_st_stock_name(value: str) -> bool:
    normalized = value.strip().upper().replace(" ", "")
    return any(marker in normalized for marker in ST_MARKERS)


def retail_voc_quality_score(retail_sentiment: float) -> float:
    if retail_sentiment == 0:
        return 2.2
    distance_from_balanced = abs(retail_sentiment - 3.0)
    return round(max(1.0, 4.0 - 1.2 * distance_from_balanced), 2)


@dataclass(frozen=True)
class GateFailure:
    code: str
    reason: str


def derive_research_rating(
    *,
    research_score: float,
    risk_score: float,
    capital_recognition: float,
    config: dict[str, Any],
) -> str:
    rating = config["research_rating"]
    if risk_score >= rating["risk_avoidance_risk_min"] and research_score < rating["risk_avoidance_score_max"]:
        return "风险回避"
    if (
        research_score >= rating["high_attention_score_min"]
        and capital_recognition >= rating["high_attention_capital_min"]
        and risk_score <= rating["high_attention_risk_max"]
    ):
        return "高关注"
    if research_score >= rating["attention_score_min"] and risk_score <= rating["attention_risk_max"]:
        return "关注"
    if research_score >= rating["neutral_score_min"]:
        return "中性观察"
    if risk_score >= rating["risk_avoidance_fallback_risk_min"]:
        return "风险回避"
    return "谨慎观察"


def compute_beneficiary_quality_score(
    *,
    trend: float,
    volume: float,
    capital_recognition: float,
    event_alignment: float,
    institutional_trend: float,
    retail_sentiment: float,
    risk: float,
    config: dict[str, Any],
) -> float:
    weights = config["scoring_weights"]["beneficiary_quality_score"]
    return round(
        weights["trend"] * trend
        + weights["volume"] * volume
        + weights["capital_recognition"] * capital_recognition
        + weights["event_alignment"] * event_alignment
        + weights["institutional_trend"] * institutional_trend
        + weights["retail_voc_quality"] * retail_voc_quality_score(retail_sentiment)
        + weights["risk"] * risk,
        2,
    )


@dataclass(frozen=True)
class GateContext:
    role: str
    trend: float
    volume: float
    retail_sentiment: float
    capital_recognition: float
    event_alignment: float
    institutional_trend: float
    risk: float
    research_rating: str
    cyclical_resource: bool
    crowding_risk: bool
    disconfirmation_risk: bool
    excluded_security_reason: str


SUPPORTIVE_PRESSURE_RATINGS = frozenset({"风险回避", "谨慎观察", "中性观察"})


def evaluate_stock_gates(ctx: GateContext, config: dict[str, Any]) -> list[GateFailure]:
    failures: list[GateFailure] = []
    if ctx.excluded_security_reason:
        failures.append(GateFailure("excluded_security", ctx.excluded_security_reason))
    if ctx.role not in {"beneficiary", "pressure"}:
        failures.append(GateFailure("role_invalid", "未设置受益/承压角色"))
        return failures
    if ctx.role == "beneficiary":
        gates = config["stock_gates"]["beneficiary"]
        if ctx.event_alignment < gates["event_alignment_min"]:
            failures.append(GateFailure("event_alignment_below", "事件关联不足"))
        if ctx.trend < gates["trend_min"]:
            failures.append(GateFailure("trend_below", "14日走势不足"))
        if ctx.volume < gates["volume_min"]:
            failures.append(GateFailure("volume_below", "量能确认不足"))
        if ctx.capital_recognition < gates["capital_recognition_min"]:
            failures.append(GateFailure("capital_below", "资金认可度不足"))
        if ctx.cyclical_resource:
            resource = config["stock_gates"]["resource_beneficiary"]
            if (
                ctx.trend < resource["trend_min"]
                or ctx.volume < resource["volume_min"]
                or ctx.capital_recognition < resource["capital_recognition_min"]
            ):
                failures.append(GateFailure("resource_confirmation_below", "周期资源需更强量价/资金确认"))
        if ctx.retail_sentiment >= gates["retail_hot_min"] and (
            ctx.capital_recognition < gates["retail_hot_capital_min"]
            or ctx.volume < gates["retail_hot_volume_min"]
        ):
            failures.append(GateFailure("retail_hot_unconfirmed", "散户情绪过热但主力/量能确认不足"))
        if ctx.risk > gates["risk_max"]:
            failures.append(GateFailure("risk_above", "风险过高"))
        if ctx.research_rating == "风险回避":
            failures.append(GateFailure("research_rating_risk_avoidance", "综合评级为风险回避"))
        return failures
    pressure_gates = config["stock_gates"]["pressure"]
    observation_gates = config["stock_gates"]["observation_pressure"]
    if ctx.event_alignment < pressure_gates["event_alignment_min"]:
        failures.append(GateFailure("event_alignment_below", "事件关联不足"))
    if ctx.trend > pressure_gates["trend_max"]:
        failures.append(GateFailure("pressure_trend_above", "14日承压走势不足"))
    if ctx.capital_recognition > pressure_gates["capital_recognition_max"]:
        failures.append(GateFailure("pressure_capital_above", "资金弱化不足"))
    if ctx.volume < pressure_gates["volume_min"] and ctx.risk < pressure_gates["risk_min"]:
        failures.append(GateFailure("pressure_volume_or_risk_below", "承压量能/风险确认不足"))
    if (
        ctx.trend >= pressure_gates["strong_mainline_trend_min"]
        and ctx.capital_recognition >= pressure_gates["strong_mainline_capital_min"]
    ):
        failures.append(GateFailure("strong_mainline_reverse", "强主线反向风险，转观察"))
    if ctx.crowding_risk and (
        ctx.trend > observation_gates["trend_max"]
        or ctx.capital_recognition > observation_gates["capital_recognition_max"]
    ):
        failures.append(GateFailure("crowding_observation_only", "高位拥挤仅作风险观察"))
    if ctx.disconfirmation_risk and (
        ctx.trend > observation_gates["trend_max"]
        or ctx.capital_recognition > observation_gates["capital_recognition_max"]
    ):
        failures.append(GateFailure("disconfirmation_observation_only", "题材证伪需破位确认"))
    if ctx.research_rating not in SUPPORTIVE_PRESSURE_RATINGS:
        failures.append(GateFailure("research_rating_unsupportive", "综合评级未支持承压"))
    return failures


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
    def excluded_security_reason(self) -> str:
        if is_star_market_ticker(self.ticker):
            return "科创板股票排除"
        if is_bse_ticker(self.ticker):
            return "北交所股票排除"
        if is_st_stock_name(self.name):
            return "ST/退市风险股票排除"
        return ""

    @property
    def excluded_security(self) -> bool:
        return bool(self.excluded_security_reason)

    @property
    def retail_voc_quality_score(self) -> float:
        return retail_voc_quality_score(self.retail_sentiment)

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
        return compute_beneficiary_quality_score(
            trend=self.trend_score,
            volume=self.volume_score,
            capital_recognition=self.capital_recognition,
            event_alignment=self.event_alignment,
            institutional_trend=self.institutional_trend_score,
            retail_sentiment=self.retail_sentiment,
            risk=self.risk_score,
            config=self.threshold_config,
        )

    @property
    def research_rating(self) -> str:
        return derive_research_rating(
            research_score=self.research_score,
            risk_score=self.risk_score,
            capital_recognition=self.capital_recognition,
            config=self.threshold_config,
        )

    @property
    def gate_context(self) -> GateContext:
        return GateContext(
            role=self.directional_role,
            trend=self.trend_score,
            volume=self.volume_score,
            retail_sentiment=self.retail_sentiment,
            capital_recognition=self.capital_recognition,
            event_alignment=self.event_alignment,
            institutional_trend=self.institutional_trend_score,
            risk=self.risk_score,
            research_rating=self.research_rating,
            cyclical_resource=self.cyclical_resource_sector,
            crowding_risk=self.crowding_risk_sector,
            disconfirmation_risk=self.disconfirmation_risk_sector,
            excluded_security_reason=self.excluded_security_reason,
        )

    @property
    def gate_failures(self) -> list[GateFailure]:
        return evaluate_stock_gates(self.gate_context, self.threshold_config)

    @property
    def operation_tendency(self) -> str:
        if self.excluded_security:
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
        if self.capital_recognition >= 3.8 and self.trend_score >= 3.5:
            return "趋势跟踪观察"
        return "事件落地后再评估"

    @property
    def eligible_for_recommendation(self) -> bool:
        return not self.gate_failures

    @property
    def market_cap_in_range(self) -> bool:
        return self.market_cap_range.contains(self.market_cap_billion)

    @property
    def exclusion_reason(self) -> str:
        return "、".join(failure.reason for failure in self.gate_failures)

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
    if not isinstance(value, (int, float)):
        raise ValueError(f"`{field_name}` must be a number from 0 to 5")
    score = float(value)
    if score < 0 or score > 5:
        raise ValueError(f"`{field_name}` must be from 0 to 5")
    return score


def require_optional_market_cap(value: object) -> float | None:
    if value is None or value == "":
        return None
    if not isinstance(value, (int, float)):
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
        help="Deprecated; market cap is retained as display context, not recommendation eligibility.",
    )
    parser.add_argument(
        "--max-market-cap-billion",
        type=float,
        default=None,
        help="Deprecated; market cap is retained as display context, not recommendation eligibility.",
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
