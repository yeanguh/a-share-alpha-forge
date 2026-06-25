#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import itertools
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rank_news import weighted_impact_score
from score_stocks import (
    GateContext,
    GateFailure,
    compute_beneficiary_quality_score,
    derive_research_rating,
    evaluate_stock_gates,
    is_bse_ticker,
    is_st_stock_name,
    is_star_market_ticker,
    retail_voc_quality_score,
)
from threshold_config import get_number, load_thresholds

DEFAULT_ROOT = Path("local")
DEFAULT_REVIEW_ROOT = DEFAULT_ROOT / "reviews"
DEFAULT_THRESHOLDS = load_thresholds()
DEFAULT_MIN_MARKET_CAP_BILLION = get_number(DEFAULT_THRESHOLDS, "market_cap_billion", "min")
DEFAULT_MAX_MARKET_CAP_BILLION = get_number(DEFAULT_THRESHOLDS, "market_cap_billion", "max")
VALID_ROLE_SCOPES = {"all", "beneficiary", "pressure"}
RESOURCE_MARKERS = ("有色", "金属", "稀土", "钨", "锡", "铝", "煤", "钢铁")
OBSERVATION_PRESSURE_MARKERS = ("高位", "拥挤", "过热", "追涨", "证伪", "传闻落空", "澄清", "辟谣")
CROWDING_MARKERS = ("高位", "拥挤", "过热", "追涨")
DISCONFIRMATION_MARKERS = ("证伪", "传闻落空", "澄清", "辟谣")


@dataclass(frozen=True)
class ThresholdProfile:
    name: str
    beneficiary_trend: float
    beneficiary_volume: float
    beneficiary_capital: float
    beneficiary_event: float
    beneficiary_quality_min: float
    beneficiary_risk_max: float
    resource_trend: float
    resource_volume: float
    resource_capital: float
    beneficiary_sector_impact: float
    beneficiary_sector_price_volume: float
    beneficiary_sector_liquidity: float
    pressure_trend_max: float
    pressure_capital_max: float
    pressure_volume_min: float
    observation_pressure_trend_max: float
    observation_pressure_capital_max: float

    def to_dict(self) -> dict[str, float | str]:
        return self.__dict__


@dataclass(frozen=True)
class Sample:
    report_date: str
    ticker: str
    name: str
    sector: str
    role: str
    trend_score: float
    volume_score: float
    retail_sentiment: float
    capital_recognition: float
    event_alignment: float
    institutional_trend_score: float
    risk_score: float
    sector_impact_score: float
    sector_price_volume: float
    sector_liquidity: float
    market_cap_billion: float | None
    hit: bool
    return_pct: float
    directional_return_pct: float

    @property
    def is_resource(self) -> bool:
        return any(marker in self.sector for marker in RESOURCE_MARKERS)

    @property
    def is_observation_pressure(self) -> bool:
        return any(marker in self.sector for marker in OBSERVATION_PRESSURE_MARKERS)

    @property
    def retail_voc_quality_score(self) -> float:
        return retail_voc_quality_score(self.retail_sentiment)

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
            config=DEFAULT_THRESHOLDS,
        )


def load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"`{path}` must contain a JSON object")
    return payload


def number_field(payload: dict[str, Any], field_name: str) -> float:
    value = payload.get(field_name)
    if not isinstance(value, (int, float)):
        raise ValueError(f"`{field_name}` must be numeric")
    return float(value)


def optional_market_cap(payload: dict[str, Any]) -> float | None:
    value = payload.get("market_cap_billion")
    return float(value) if isinstance(value, (int, float)) else None


def allowed_security(sample: Sample) -> bool:
    return not (
        is_star_market_ticker(sample.ticker)
        or is_bse_ticker(sample.ticker)
        or is_st_stock_name(sample.name)
    )


def role_in_scope(sample: Sample, role_scope: str) -> bool:
    return role_scope == "all" or sample.role == role_scope


def impact_score(payload: dict[str, Any]) -> float:
    return weighted_impact_score(
        magnitude=number_field(payload, "magnitude"),
        breadth=number_field(payload, "breadth"),
        immediacy=number_field(payload, "immediacy"),
        confidence=number_field(payload, "confidence"),
        novelty=number_field(payload, "novelty"),
        liquidity=number_field(payload, "liquidity"),
        price_volume=number_field(payload, "price_volume"),
        config=DEFAULT_THRESHOLDS,
    )


def load_sector_scores(bundle: dict[str, Any]) -> dict[tuple[str, str], dict[str, float]]:
    sector_candidates = bundle.get("sector_candidates", [])
    if not isinstance(sector_candidates, list):
        return {}
    scores: dict[tuple[str, str], dict[str, float]] = {}
    for item in sector_candidates:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", ""))
        direction = str(item.get("direction", ""))
        if not title or direction not in {"positive", "negative"}:
            continue
        scores[(title, direction)] = {
            "impact_score": impact_score(item),
            "price_volume": number_field(item, "price_volume"),
            "liquidity": number_field(item, "liquidity"),
        }
    return scores


def stock_key(report_date: str, ticker: str, role: str) -> tuple[str, str, str]:
    return report_date, ticker, role


def load_outcomes(path: Path) -> dict[tuple[str, str, str], dict[str, Any]]:
    payload = load_json_object(path)
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError("Backtest payload must include array `rows`")
    outcomes: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or row.get("status") != "evaluated":
            continue
        report_date = str(row.get("report_date", ""))
        ticker = str(row.get("ticker", ""))
        role = str(row.get("role", ""))
        outcomes[stock_key(report_date, ticker, role)] = row
    return outcomes


def load_samples(root: Path, outcomes: dict[tuple[str, str, str], dict[str, Any]]) -> list[Sample]:
    samples: list[Sample] = []
    for report_date, ticker, role in sorted(outcomes):
        if role not in {"beneficiary", "pressure"}:
            continue
        bundle_path = root / report_date / "input_bundle.json"
        if not bundle_path.exists():
            continue
        bundle = load_json_object(bundle_path)
        stocks = bundle.get("stocks", [])
        if not isinstance(stocks, list):
            continue
        sector_scores = load_sector_scores(bundle)
        stock = next(
            (
                item
                for item in stocks
                if isinstance(item, dict) and item.get("ticker") == ticker and item.get("directional_role") == role
            ),
            None,
        )
        if not isinstance(stock, dict):
            continue
        outcome = outcomes[stock_key(report_date, ticker, role)]
        sector_score = sector_scores.get(
            (str(stock.get("sector", "")), "positive" if role == "beneficiary" else "negative"), {}
        )
        samples.append(
            Sample(
                report_date=report_date,
                ticker=ticker,
                name=str(stock.get("name", outcome.get("name", ""))),
                sector=str(stock.get("sector", outcome.get("sector", ""))),
                role=role,
                trend_score=number_field(stock, "trend_score"),
                volume_score=number_field(stock, "volume_score"),
                retail_sentiment=number_field(stock, "retail_sentiment"),
                capital_recognition=number_field(stock, "capital_recognition"),
                event_alignment=number_field(stock, "event_alignment"),
                institutional_trend_score=float(stock.get("institutional_trend_score", 0) or 0),
                risk_score=number_field(stock, "risk_score"),
                sector_impact_score=float(sector_score.get("impact_score", 0)),
                sector_price_volume=float(sector_score.get("price_volume", 0)),
                sector_liquidity=float(sector_score.get("liquidity", 0)),
                market_cap_billion=optional_market_cap(stock),
                hit=bool(outcome.get("hit")),
                return_pct=float(outcome.get("return_since_report_open_pct", 0)),
                directional_return_pct=float(
                    outcome.get(
                        "directional_return_pct",
                        -float(outcome.get("return_since_report_open_pct", 0))
                        if role == "pressure"
                        else float(outcome.get("return_since_report_open_pct", 0)),
                    )
                ),
            )
        )
    return samples


def passes_profile(sample: Sample, profile: ThresholdProfile) -> bool:
    return not profile_failures(sample, profile)


def profile_failure_reasons(sample: Sample, profile: ThresholdProfile) -> list[str]:
    return [failure.code for failure in profile_failures(sample, profile)]


def profile_to_config(profile: ThresholdProfile, base: dict[str, Any]) -> dict[str, Any]:
    config = copy.deepcopy(base)
    beneficiary = config["stock_gates"]["beneficiary"]
    beneficiary["event_alignment_min"] = profile.beneficiary_event
    beneficiary["trend_min"] = profile.beneficiary_trend
    beneficiary["volume_min"] = profile.beneficiary_volume
    beneficiary["capital_recognition_min"] = profile.beneficiary_capital
    beneficiary["risk_max"] = profile.beneficiary_risk_max
    resource = config["stock_gates"]["resource_beneficiary"]
    resource["trend_min"] = profile.resource_trend
    resource["volume_min"] = profile.resource_volume
    resource["capital_recognition_min"] = profile.resource_capital
    pressure = config["stock_gates"]["pressure"]
    pressure["trend_max"] = profile.pressure_trend_max
    pressure["capital_recognition_max"] = profile.pressure_capital_max
    pressure["volume_min"] = profile.pressure_volume_min
    observation = config["stock_gates"]["observation_pressure"]
    observation["trend_max"] = profile.observation_pressure_trend_max
    observation["capital_recognition_max"] = profile.observation_pressure_capital_max
    sector = config["sector_gates"]["beneficiary"]
    sector["impact_score_min"] = profile.beneficiary_sector_impact
    sector["price_volume_min"] = profile.beneficiary_sector_price_volume
    sector["liquidity_min"] = profile.beneficiary_sector_liquidity
    return config


def sample_gate_context(sample: Sample, config: dict[str, Any]) -> GateContext:
    research_weights = config["scoring_weights"]["research_score"]
    research_score = round(
        research_weights["trend"] * sample.trend_score
        + research_weights["volume"] * sample.volume_score
        + research_weights["retail_voc_quality"] * sample.retail_voc_quality_score
        + research_weights["capital_recognition"] * sample.capital_recognition
        + research_weights["event_alignment"] * sample.event_alignment
        + research_weights["institutional_trend"] * sample.institutional_trend_score
        + research_weights["risk"] * sample.risk_score,
        2,
    )
    rating = derive_research_rating(
        research_score=research_score,
        risk_score=sample.risk_score,
        capital_recognition=sample.capital_recognition,
        config=config,
    )
    return GateContext(
        role=sample.role,
        trend=sample.trend_score,
        volume=sample.volume_score,
        retail_sentiment=sample.retail_sentiment,
        capital_recognition=sample.capital_recognition,
        event_alignment=sample.event_alignment,
        institutional_trend=sample.institutional_trend_score,
        risk=sample.risk_score,
        research_rating=rating,
        cyclical_resource=sample.is_resource,
        crowding_risk=any(marker in sample.sector for marker in CROWDING_MARKERS),
        disconfirmation_risk=any(marker in sample.sector for marker in DISCONFIRMATION_MARKERS),
        excluded_security_reason="",
    )


def sector_gate_failures(sample: Sample, profile: ThresholdProfile) -> list[GateFailure]:
    if sample.role != "beneficiary":
        return []
    failures: list[GateFailure] = []
    if sample.sector_impact_score < profile.beneficiary_sector_impact:
        failures.append(GateFailure("sector_impact_below_profile", "板块影响分数不足"))
    if sample.sector_price_volume < profile.beneficiary_sector_price_volume:
        failures.append(GateFailure("sector_price_volume_below_profile", "板块量价确认不足"))
    if sample.sector_liquidity < profile.beneficiary_sector_liquidity:
        failures.append(GateFailure("sector_liquidity_below_profile", "板块流动性不足"))
    return failures


def quality_gate_failure(sample: Sample, profile: ThresholdProfile) -> list[GateFailure]:
    if sample.role != "beneficiary" or profile.beneficiary_quality_min <= 0:
        return []
    if sample.beneficiary_quality_score < profile.beneficiary_quality_min:
        return [GateFailure("beneficiary_quality_score_below_profile", "受益质量分数不足")]
    return []


def profile_failures(sample: Sample, profile: ThresholdProfile) -> list[GateFailure]:
    config = profile_to_config(profile, DEFAULT_THRESHOLDS)
    ctx = sample_gate_context(sample, config)
    return [
        *evaluate_stock_gates(ctx, config),
        *sector_gate_failures(sample, profile),
        *quality_gate_failure(sample, profile),
    ]


def summarize(samples: list[Sample]) -> dict[str, Any]:
    if not samples:
        return {
            "count": 0,
            "hit_rate": None,
            "average_return_pct": None,
            "average_directional_return_pct": None,
            "median_return_pct": None,
            "median_directional_return_pct": None,
            "average_gain_pct": None,
            "average_loss_pct": None,
            "average_directional_gain_pct": None,
            "average_directional_loss_pct": None,
            "payoff_ratio": None,
            "worst_return_pct": None,
            "best_return_pct": None,
            "worst_directional_return_pct": None,
            "best_directional_return_pct": None,
        }
    returns = sorted(sample.return_pct for sample in samples)
    directional_returns = sorted(sample.directional_return_pct for sample in samples)
    gains = [value for value in returns if value > 0]
    losses = [value for value in returns if value < 0]
    directional_gains = [value for value in directional_returns if value > 0]
    directional_losses = [value for value in directional_returns if value < 0]
    return_midpoint = len(returns) // 2
    directional_midpoint = len(directional_returns) // 2
    median = (
        returns[return_midpoint] if len(returns) % 2 else (returns[return_midpoint - 1] + returns[return_midpoint]) / 2
    )
    directional_median = (
        directional_returns[directional_midpoint]
        if len(directional_returns) % 2
        else (directional_returns[directional_midpoint - 1] + directional_returns[directional_midpoint]) / 2
    )
    average_gain = sum(gains) / len(gains) if gains else None
    average_loss = sum(losses) / len(losses) if losses else None
    average_directional_gain = sum(directional_gains) / len(directional_gains) if directional_gains else None
    average_directional_loss = sum(directional_losses) / len(directional_losses) if directional_losses else None
    payoff_ratio = None
    if average_directional_gain is not None and average_directional_loss is not None and average_directional_loss != 0:
        payoff_ratio = abs(average_directional_gain / average_directional_loss)
    return {
        "count": len(samples),
        "hit_rate": round(sum(1 for sample in samples if sample.hit) / len(samples), 3),
        "average_return_pct": round(sum(returns) / len(returns), 3),
        "average_directional_return_pct": round(sum(directional_returns) / len(directional_returns), 3),
        "median_return_pct": round(median, 3),
        "median_directional_return_pct": round(directional_median, 3),
        "average_gain_pct": None if average_gain is None else round(average_gain, 3),
        "average_loss_pct": None if average_loss is None else round(average_loss, 3),
        "average_directional_gain_pct": (
            None if average_directional_gain is None else round(average_directional_gain, 3)
        ),
        "average_directional_loss_pct": (
            None if average_directional_loss is None else round(average_directional_loss, 3)
        ),
        "payoff_ratio": None if payoff_ratio is None else round(payoff_ratio, 3),
        "worst_return_pct": round(returns[0], 3),
        "best_return_pct": round(returns[-1], 3),
        "worst_directional_return_pct": round(directional_returns[0], 3),
        "best_directional_return_pct": round(directional_returns[-1], 3),
    }


def summarize_by_report(samples: list[Sample]) -> list[dict[str, Any]]:
    report_dates = sorted({sample.report_date for sample in samples})
    return [
        {
            "report_date": report_date,
            **summarize([sample for sample in samples if sample.report_date == report_date]),
        }
        for report_date in report_dates
    ]


def sample_output(sample: Sample) -> dict[str, Any]:
    return {
        **sample.__dict__,
        "retail_voc_quality_score": sample.retail_voc_quality_score,
        "beneficiary_quality_score": sample.beneficiary_quality_score,
    }


def score_summary(summary: dict[str, Any], beneficiary_summary: dict[str, Any]) -> float:
    hit_rate = float(summary["hit_rate"] or 0)
    average_return = float(summary["average_directional_return_pct"] or 0)
    beneficiary_hit_rate = float(beneficiary_summary["hit_rate"] or 0)
    payoff_ratio = float(summary["payoff_ratio"] or 0)
    worst_return = float(summary["worst_return_pct"] or 0)
    count = int(summary["count"])
    count_penalty = max(0, 12 - count) * 0.025
    tail_penalty = max(0.0, -worst_return - 5.0) * 0.02
    return round(
        hit_rate
        + 0.05 * average_return
        + 0.25 * beneficiary_hit_rate
        + 0.04 * min(payoff_ratio, 3.0)
        - count_penalty
        - tail_penalty,
        4,
    )


def report_coverage_penalty(report_count: int) -> float:
    return max(0, 3 - report_count) * 0.04


def current_production_profile() -> ThresholdProfile:
    config = load_thresholds()
    return ThresholdProfile(
        name="current_production_gate",
        beneficiary_trend=get_number(config, "stock_gates", "beneficiary", "trend_min"),
        beneficiary_volume=get_number(config, "stock_gates", "beneficiary", "volume_min"),
        beneficiary_capital=get_number(config, "stock_gates", "beneficiary", "capital_recognition_min"),
        beneficiary_event=get_number(config, "stock_gates", "beneficiary", "event_alignment_min"),
        beneficiary_quality_min=0.0,
        beneficiary_risk_max=get_number(config, "stock_gates", "beneficiary", "risk_max"),
        resource_trend=get_number(config, "stock_gates", "resource_beneficiary", "trend_min"),
        resource_volume=get_number(config, "stock_gates", "resource_beneficiary", "volume_min"),
        resource_capital=get_number(config, "stock_gates", "resource_beneficiary", "capital_recognition_min"),
        beneficiary_sector_impact=get_number(config, "sector_gates", "beneficiary", "impact_score_min"),
        beneficiary_sector_price_volume=get_number(config, "sector_gates", "beneficiary", "price_volume_min"),
        beneficiary_sector_liquidity=get_number(config, "sector_gates", "beneficiary", "liquidity_min"),
        pressure_trend_max=get_number(config, "stock_gates", "pressure", "trend_max"),
        pressure_capital_max=get_number(config, "stock_gates", "pressure", "capital_recognition_max"),
        pressure_volume_min=get_number(config, "stock_gates", "pressure", "volume_min"),
        observation_pressure_trend_max=get_number(config, "stock_gates", "observation_pressure", "trend_max"),
        observation_pressure_capital_max=get_number(
            config,
            "stock_gates",
            "observation_pressure",
            "capital_recognition_max",
        ),
    )


def promotion_failure_reasons(evaluation: dict[str, Any], gate: dict[str, float | int]) -> list[str]:
    overall = evaluation["overall"]
    report_count = int(evaluation["report_count"])
    hit_rate = float(overall["hit_rate"] or 0)
    average_directional_return = float(overall["average_directional_return_pct"] or 0)
    worst_directional_return = float(overall["worst_directional_return_pct"] or 0)
    worst_report_directional_return = float(evaluation["worst_report_directional_return_pct"] or 0)
    reasons: list[str] = []
    if report_count < int(gate["min_report_count"]):
        reasons.append("report_count_below_gate")
    if hit_rate < float(gate["min_hit_rate"]):
        reasons.append("hit_rate_below_gate")
    if average_directional_return < float(gate["min_average_directional_return_pct"]):
        reasons.append("average_directional_return_below_gate")
    if worst_directional_return < float(gate["min_worst_directional_return_pct"]):
        reasons.append("worst_directional_return_below_gate")
    if worst_report_directional_return < float(gate["min_worst_report_directional_return_pct"]):
        reasons.append("worst_report_directional_return_below_gate")
    return reasons


def apply_promotion_gate(evaluation: dict[str, Any], gate: dict[str, float | int]) -> dict[str, Any]:
    reasons = promotion_failure_reasons(evaluation, gate)
    return {
        **evaluation,
        "passes_promotion_gate": not reasons,
        "promotion_failure_reasons": reasons,
    }


def metric_value(summary: dict[str, Any], field_name: str) -> float:
    return float(summary.get(field_name) or 0)


def production_comparison_failure_reasons(evaluation: dict[str, Any], baseline: dict[str, Any]) -> list[str]:
    current_overall = evaluation["overall"]
    baseline_overall = baseline["overall"]
    reasons: list[str] = []
    if int(evaluation["report_count"]) < int(baseline["report_count"]):
        reasons.append("report_count_below_production")
    if metric_value(current_overall, "hit_rate") < metric_value(baseline_overall, "hit_rate"):
        reasons.append("hit_rate_below_production")
    if metric_value(current_overall, "average_directional_return_pct") < metric_value(
        baseline_overall,
        "average_directional_return_pct",
    ):
        reasons.append("average_directional_return_below_production")
    if metric_value(current_overall, "worst_directional_return_pct") < metric_value(
        baseline_overall,
        "worst_directional_return_pct",
    ):
        reasons.append("worst_directional_return_below_production")
    return reasons


def apply_production_comparison(evaluation: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    reasons = production_comparison_failure_reasons(evaluation, baseline)
    current_overall = evaluation["overall"]
    baseline_overall = baseline["overall"]
    return {
        **evaluation,
        "beats_production_baseline": not reasons,
        "production_comparison_failure_reasons": reasons,
        "production_metric_delta": {
            "report_count": int(evaluation["report_count"]) - int(baseline["report_count"]),
            "hit_rate": round(
                metric_value(current_overall, "hit_rate") - metric_value(baseline_overall, "hit_rate"),
                3,
            ),
            "average_directional_return_pct": round(
                metric_value(current_overall, "average_directional_return_pct")
                - metric_value(baseline_overall, "average_directional_return_pct"),
                3,
            ),
            "worst_directional_return_pct": round(
                metric_value(current_overall, "worst_directional_return_pct")
                - metric_value(baseline_overall, "worst_directional_return_pct"),
                3,
            ),
        },
    }


def best_by_beneficiary_quality_min(evaluations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best_profiles: dict[float, dict[str, Any]] = {}
    for evaluation in evaluations:
        profile = evaluation["profile"]
        quality_min = float(profile["beneficiary_quality_min"])
        current_best = best_profiles.get(quality_min)
        if current_best is None or float(evaluation["score"]) > float(current_best["score"]):
            best_profiles[quality_min] = evaluation
    return [best_profiles[quality_min] for quality_min in sorted(best_profiles)]


def diagnostic_sample_output(sample: Sample, profile: ThresholdProfile) -> dict[str, Any]:
    return {
        **sample_output(sample),
        "profile_failure_reasons": profile_failure_reasons(sample, profile),
    }


def production_error_diagnostics(
    samples: list[Sample],
    profile: ThresholdProfile,
    limit: int,
) -> dict[str, Any]:
    selected = [sample for sample in samples if passes_profile(sample, profile)]
    unselected = [sample for sample in samples if not passes_profile(sample, profile)]
    selected_misses = sorted(
        [sample for sample in selected if not sample.hit],
        key=lambda sample: sample.directional_return_pct,
    )
    missed_winners = sorted(
        [sample for sample in unselected if sample.hit],
        key=lambda sample: sample.directional_return_pct,
        reverse=True,
    )
    avoided_losers = sorted(
        [sample for sample in unselected if not sample.hit],
        key=lambda sample: sample.directional_return_pct,
    )
    failure_reason_summary = summarize_failure_reasons(unselected, profile)
    return {
        "selected_count": len(selected),
        "unselected_count": len(unselected),
        "selected_miss_count": len(selected_misses),
        "missed_winner_count": len(missed_winners),
        "avoided_loser_count": len(avoided_losers),
        "selected_misses": [diagnostic_sample_output(sample, profile) for sample in selected_misses[:limit]],
        "missed_winners": [diagnostic_sample_output(sample, profile) for sample in missed_winners[:limit]],
        "avoided_losers": [diagnostic_sample_output(sample, profile) for sample in avoided_losers[:limit]],
        "failure_reason_summary": failure_reason_summary,
    }


def summarize_failure_reasons(samples: list[Sample], profile: ThresholdProfile) -> list[dict[str, Any]]:
    samples_by_reason: dict[str, list[Sample]] = {}
    for sample in samples:
        for reason in profile_failure_reasons(sample, profile):
            samples_by_reason.setdefault(reason, []).append(sample)

    summary = []
    for reason, reason_samples in samples_by_reason.items():
        outcome = summarize(reason_samples)
        missed_winners = [sample for sample in reason_samples if sample.hit]
        avoided_losers = [sample for sample in reason_samples if not sample.hit]
        avoided_count = len(avoided_losers)
        missed_count = len(missed_winners)
        average_return = float(outcome["average_return_pct"] or 0)
        summary.append(
            {
                "reason": reason,
                "sample_count": len(reason_samples),
                "missed_winner_count": missed_count,
                "avoided_loser_count": avoided_count,
                "hit_rate": outcome["hit_rate"],
                "average_return_pct": outcome["average_return_pct"],
                "worst_return_pct": outcome["worst_return_pct"],
                "best_return_pct": outcome["best_return_pct"],
                **gate_action_recommendation(average_return, missed_count, avoided_count),
            }
        )
    return sorted(
        summary,
        key=lambda item: (
            int(item["avoided_loser_count"]) - int(item["missed_winner_count"]),
            int(item["sample_count"]),
            -float(item["average_return_pct"] or 0),
        ),
        reverse=True,
    )


def gate_action_recommendation(
    average_return_pct: float,
    missed_winner_count: int,
    avoided_loser_count: int,
) -> dict[str, str]:
    avoided_minus_missed = avoided_loser_count - missed_winner_count
    if average_return_pct < 0 and avoided_minus_missed >= 2:
        return {
            "gate_action": "keep_strict",
            "gate_action_reason": "Excluded samples have negative average return and avoided losers outnumber missed winners.",
        }
    if average_return_pct >= 0 and missed_winner_count > avoided_loser_count:
        return {
            "gate_action": "review_relaxation_candidate",
            "gate_action_reason": "Excluded samples have non-negative average return and missed winners outnumber avoided losers.",
        }
    return {
        "gate_action": "monitor",
        "gate_action_reason": "Evidence is mixed or too thin for a production threshold change.",
    }


def evaluate_profile(samples: list[Sample], profile: ThresholdProfile) -> dict[str, Any]:
    selected = [sample for sample in samples if passes_profile(sample, profile)]
    beneficiary_samples = [sample for sample in selected if sample.role == "beneficiary"]
    pressure_samples = [sample for sample in selected if sample.role == "pressure"]
    overall = summarize(selected)
    beneficiary_summary = summarize(beneficiary_samples)
    pressure_summary = summarize(pressure_samples)
    by_report = summarize_by_report(selected)
    report_count = len(by_report)
    base_score = score_summary(overall, beneficiary_summary)
    return {
        "profile": profile.to_dict(),
        "score": round(base_score - report_coverage_penalty(report_count), 4),
        "base_score": base_score,
        "report_count": report_count,
        "worst_report_directional_return_pct": (
            None if not by_report else min(float(report["average_directional_return_pct"] or 0) for report in by_report)
        ),
        "overall": overall,
        "by_role": {
            "beneficiary": beneficiary_summary,
            "pressure": pressure_summary,
        },
        "by_report": by_report,
        "selected": [sample_output(sample) for sample in selected],
    }


def profile_grid() -> list[ThresholdProfile]:
    profiles: list[ThresholdProfile] = []
    index = 1
    for (
        beneficiary_trend,
        beneficiary_volume,
        beneficiary_capital,
        beneficiary_quality_min,
        beneficiary_risk_max,
        resource_level,
        sector_impact,
        sector_price_volume,
        sector_liquidity,
        pressure_trend_max,
        pressure_capital_max,
        observation_level,
    ) in itertools.product(
        (3.0, 3.2, 3.4),
        (3.2, 3.4, 3.6),
        (3.0, 3.2, 3.4, 3.6),
        (0.0, 3.0, 3.2, 3.4),
        (3.8, 4.0, 4.2),
        (3.6, 3.8, 4.0),
        (3.6, 3.8, 4.0),
        (3.6, 3.8, 4.0),
        (3.6, 3.8, 4.0),
        (2.4, 2.6, 2.8),
        (2.6, 2.8),
        (2.0, 2.2),
    ):
        profiles.append(
            ThresholdProfile(
                name=f"profile_{index:04d}",
                beneficiary_trend=beneficiary_trend,
                beneficiary_volume=beneficiary_volume,
                beneficiary_capital=beneficiary_capital,
                beneficiary_event=3.5,
                beneficiary_quality_min=beneficiary_quality_min,
                beneficiary_risk_max=beneficiary_risk_max,
                resource_trend=resource_level,
                resource_volume=resource_level,
                resource_capital=resource_level,
                beneficiary_sector_impact=sector_impact,
                beneficiary_sector_price_volume=sector_price_volume,
                beneficiary_sector_liquidity=sector_liquidity,
                pressure_trend_max=pressure_trend_max,
                pressure_capital_max=pressure_capital_max,
                pressure_volume_min=3.2,
                observation_pressure_trend_max=observation_level,
                observation_pressure_capital_max=2.5,
            )
        )
        index += 1
    return profiles


def scan_command(args: argparse.Namespace) -> None:
    if args.role_scope not in VALID_ROLE_SCOPES:
        raise ValueError("`role_scope` must be all, beneficiary, or pressure")

    outcomes = load_outcomes(Path(args.backtest))
    all_samples = load_samples(Path(args.output_root), outcomes)
    security_samples = [sample for sample in all_samples if allowed_security(sample)]
    samples = [sample for sample in security_samples if role_in_scope(sample, args.role_scope)]
    production_profile = current_production_profile()
    promotion_gate = {
        "min_report_count": args.promotion_min_report_count,
        "min_hit_rate": args.promotion_min_hit_rate,
        "min_average_directional_return_pct": args.promotion_min_average_directional_return_pct,
        "min_worst_directional_return_pct": args.promotion_min_worst_directional_return_pct,
        "min_worst_report_directional_return_pct": args.promotion_min_worst_report_directional_return_pct,
    }
    production_baseline = apply_promotion_gate(evaluate_profile(samples, production_profile), promotion_gate)
    production_baseline = apply_production_comparison(production_baseline, production_baseline)
    evaluated = [
        apply_production_comparison(
            apply_promotion_gate(evaluate_profile(samples, profile), promotion_gate),
            production_baseline,
        )
        for profile in profile_grid()
    ]
    ranked = sorted(evaluated, key=lambda item: item["score"], reverse=True)
    promotable = [profile for profile in ranked if profile["passes_promotion_gate"]]
    deployable = [
        profile for profile in ranked if profile["passes_promotion_gate"] and profile["beats_production_baseline"]
    ]
    payload = {
        "security_exclusions": {
            "exclude_star_market": True,
            "exclude_bse": True,
            "exclude_st": True,
        },
        "role_scope": args.role_scope,
        "raw_sample_count": len(all_samples),
        "security_filtered_sample_count": len(security_samples),
        "sample_count": len(samples),
        "excluded_by_security_count": len(all_samples) - len(security_samples),
        "excluded_by_role_count": len(security_samples) - len(samples),
        "promotion_gate": promotion_gate,
        "production_baseline_profile": production_profile.to_dict(),
        "production_baseline_evaluation": production_baseline,
        "production_error_diagnostics": production_error_diagnostics(samples, production_profile, args.top),
        "profile_count": len(evaluated),
        "promotable_profile_count": len(promotable),
        "deployable_profile_count": len(deployable),
        "best_by_beneficiary_quality_min": best_by_beneficiary_quality_min(evaluated),
        "top_profiles": ranked[: args.top],
        "top_promotable_profiles": promotable[: args.top],
        "top_deployable_profiles": deployable[: args.top],
    }
    write_json(payload, Path(args.output) if args.output else None)


def write_json(payload: object, output_path: Path | None = None) -> None:
    encoded = json.dumps(payload, ensure_ascii=False, indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(f"{encoded}\n", encoding="utf-8")
        sys.stdout.write(json.dumps({"output": str(output_path)}, ensure_ascii=False, indent=2))
        sys.stdout.write("\n")
        return
    sys.stdout.write(encoded)
    sys.stdout.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scan archived A-share selection thresholds against board/ST-filtered backtest labels."
    )
    parser.add_argument("--output-root", default=str(DEFAULT_ROOT), help="Archive root containing input bundles.")
    parser.add_argument("--backtest", required=True, help="Backtest JSON containing evaluated rows.")
    parser.add_argument(
        "--output",
        help=f"Optional path for threshold-scan JSON. Recommended root: {DEFAULT_REVIEW_ROOT}/threshold_scans/.",
    )
    parser.add_argument("--top", type=int, default=10, help="Number of top profiles to emit.")
    parser.add_argument(
        "--role-scope",
        choices=sorted(VALID_ROLE_SCOPES),
        default="all",
        help="Calibration sample role scope. Use beneficiary for opportunity-pool optimization.",
    )
    parser.add_argument(
        "--min-market-cap-billion",
        type=float,
        default=DEFAULT_MIN_MARKET_CAP_BILLION,
        help="Deprecated; market cap is no longer used as a calibration sample gate.",
    )
    parser.add_argument(
        "--max-market-cap-billion",
        type=float,
        default=DEFAULT_MAX_MARKET_CAP_BILLION,
        help="Deprecated; market cap is no longer used as a calibration sample gate.",
    )
    parser.add_argument(
        "--promotion-min-report-count",
        type=int,
        default=3,
        help="Minimum report-date coverage required before a scanned profile can be treated as promotable.",
    )
    parser.add_argument(
        "--promotion-min-hit-rate",
        type=float,
        default=0.8,
        help="Minimum effective hit rate required before a scanned profile can be treated as promotable.",
    )
    parser.add_argument(
        "--promotion-min-average-directional-return-pct",
        type=float,
        default=2.0,
        help="Minimum average directional return required before a scanned profile can be treated as promotable.",
    )
    parser.add_argument(
        "--promotion-min-worst-directional-return-pct",
        type=float,
        default=-1.0,
        help="Minimum worst selected-row directional return allowed before a scanned profile can be promotable.",
    )
    parser.add_argument(
        "--promotion-min-worst-report-directional-return-pct",
        type=float,
        default=0.0,
        help="Minimum worst report-date directional return required before a scanned profile can be promotable.",
    )
    parser.set_defaults(func=scan_command)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
