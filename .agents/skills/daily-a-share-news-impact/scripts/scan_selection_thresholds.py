#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_ROOT = Path(".local/daily-a-share-news-impact")
DEFAULT_MIN_MARKET_CAP_BILLION = 100.0
DEFAULT_MAX_MARKET_CAP_BILLION = 2000.0
VALID_ROLE_SCOPES = {"all", "beneficiary", "pressure"}
RESOURCE_MARKERS = ("有色", "金属", "稀土", "钨", "锡", "铝", "煤", "钢铁")
OBSERVATION_PRESSURE_MARKERS = ("高位", "拥挤", "过热", "追涨", "证伪", "传闻落空", "澄清", "辟谣")


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
        if self.retail_sentiment == 0:
            return 2.2
        distance_from_balanced = abs(self.retail_sentiment - 3.0)
        return round(max(1.0, 4.0 - 1.2 * distance_from_balanced), 2)

    @property
    def beneficiary_quality_score(self) -> float:
        return round(
            0.27 * self.trend_score
            + 0.22 * self.volume_score
            + 0.27 * self.capital_recognition
            + 0.18 * self.event_alignment
            + 0.06 * self.retail_voc_quality_score
            - 0.20 * self.risk_score,
            2,
        )


def load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"`{path}` must contain a JSON object")
    return payload


def number_field(payload: dict[str, Any], field_name: str) -> float:
    value = payload.get(field_name)
    if not isinstance(value, int | float):
        raise ValueError(f"`{field_name}` must be numeric")
    return float(value)


def optional_market_cap(payload: dict[str, Any]) -> float | None:
    value = payload.get("market_cap_billion")
    return float(value) if isinstance(value, int | float) else None


def market_cap_in_range(sample: Sample, minimum_billion: float, maximum_billion: float) -> bool:
    return sample.market_cap_billion is not None and minimum_billion <= sample.market_cap_billion <= maximum_billion


def role_in_scope(sample: Sample, role_scope: str) -> bool:
    return role_scope == "all" or sample.role == role_scope


def impact_score(payload: dict[str, Any]) -> float:
    return round(
        0.30 * number_field(payload, "magnitude")
        + 0.18 * number_field(payload, "breadth")
        + 0.12 * number_field(payload, "immediacy")
        + 0.15 * number_field(payload, "confidence")
        + 0.08 * number_field(payload, "novelty")
        + 0.07 * number_field(payload, "liquidity")
        + 0.10 * number_field(payload, "price_volume"),
        2,
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
    if sample.role == "beneficiary":
        if sample.event_alignment < profile.beneficiary_event:
            return False
        if sample.trend_score < profile.beneficiary_trend:
            return False
        if sample.volume_score < profile.beneficiary_volume:
            return False
        if sample.capital_recognition < profile.beneficiary_capital:
            return False
        if sample.beneficiary_quality_score < profile.beneficiary_quality_min:
            return False
        if sample.risk_score > profile.beneficiary_risk_max:
            return False
        if sample.sector_impact_score < profile.beneficiary_sector_impact:
            return False
        if sample.sector_price_volume < profile.beneficiary_sector_price_volume:
            return False
        if sample.sector_liquidity < profile.beneficiary_sector_liquidity:
            return False
        if sample.retail_sentiment >= 4.5 and (sample.capital_recognition < 3.8 or sample.volume_score < 3.4):
            return False
        if sample.is_resource:
            return (
                sample.trend_score >= profile.resource_trend
                and sample.volume_score >= profile.resource_volume
                and sample.capital_recognition >= profile.resource_capital
            )
        return True
    if sample.role == "pressure":
        if sample.event_alignment < 3.5:
            return False
        if sample.trend_score > profile.pressure_trend_max:
            return False
        if sample.capital_recognition > profile.pressure_capital_max:
            return False
        if sample.volume_score < profile.pressure_volume_min and sample.risk_score < 3.8:
            return False
        if sample.is_observation_pressure:
            return (
                sample.trend_score <= profile.observation_pressure_trend_max
                and sample.capital_recognition <= profile.observation_pressure_capital_max
            )
        return True
    return False


def profile_failure_reasons(sample: Sample, profile: ThresholdProfile) -> list[str]:
    reasons: list[str] = []
    if sample.role == "beneficiary":
        if sample.event_alignment < profile.beneficiary_event:
            reasons.append("event_alignment_below_profile")
        if sample.trend_score < profile.beneficiary_trend:
            reasons.append("trend_score_below_profile")
        if sample.volume_score < profile.beneficiary_volume:
            reasons.append("volume_score_below_profile")
        if sample.capital_recognition < profile.beneficiary_capital:
            reasons.append("capital_recognition_below_profile")
        if sample.beneficiary_quality_score < profile.beneficiary_quality_min:
            reasons.append("beneficiary_quality_score_below_profile")
        if sample.risk_score > profile.beneficiary_risk_max:
            reasons.append("risk_score_above_profile")
        if sample.sector_impact_score < profile.beneficiary_sector_impact:
            reasons.append("sector_impact_score_below_profile")
        if sample.sector_price_volume < profile.beneficiary_sector_price_volume:
            reasons.append("sector_price_volume_below_profile")
        if sample.sector_liquidity < profile.beneficiary_sector_liquidity:
            reasons.append("sector_liquidity_below_profile")
        if sample.retail_sentiment >= 4.5 and (sample.capital_recognition < 3.8 or sample.volume_score < 3.4):
            reasons.append("retail_crowding_without_capital_or_volume_confirmation")
        if sample.is_resource and sample.trend_score < profile.resource_trend:
            reasons.append("resource_trend_below_profile")
        if sample.is_resource and sample.volume_score < profile.resource_volume:
            reasons.append("resource_volume_below_profile")
        if sample.is_resource and sample.capital_recognition < profile.resource_capital:
            reasons.append("resource_capital_below_profile")
        return reasons
    if sample.role == "pressure":
        if sample.event_alignment < 3.5:
            reasons.append("event_alignment_below_profile")
        if sample.trend_score > profile.pressure_trend_max:
            reasons.append("pressure_trend_score_above_profile")
        if sample.capital_recognition > profile.pressure_capital_max:
            reasons.append("pressure_capital_recognition_above_profile")
        if sample.volume_score < profile.pressure_volume_min and sample.risk_score < 3.8:
            reasons.append("pressure_volume_and_risk_confirmation_below_profile")
        if sample.is_observation_pressure and sample.trend_score > profile.observation_pressure_trend_max:
            reasons.append("observation_pressure_trend_score_above_profile")
        if sample.is_observation_pressure and sample.capital_recognition > profile.observation_pressure_capital_max:
            reasons.append("observation_pressure_capital_recognition_above_profile")
        return reasons
    return ["role_out_of_profile_scope"]


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
    return ThresholdProfile(
        name="current_production_gate",
        beneficiary_trend=3.0,
        beneficiary_volume=3.4,
        beneficiary_capital=3.6,
        beneficiary_event=3.5,
        beneficiary_quality_min=0.0,
        beneficiary_risk_max=3.8,
        resource_trend=3.6,
        resource_volume=3.6,
        resource_capital=3.6,
        beneficiary_sector_impact=4.0,
        beneficiary_sector_price_volume=4.0,
        beneficiary_sector_liquidity=4.0,
        pressure_trend_max=2.4,
        pressure_capital_max=2.6,
        pressure_volume_min=3.2,
        observation_pressure_trend_max=2.2,
        observation_pressure_capital_max=2.5,
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
    if args.min_market_cap_billion <= 0:
        raise ValueError("`min_market_cap_billion` must be positive")
    if args.max_market_cap_billion < args.min_market_cap_billion:
        raise ValueError("`max_market_cap_billion` must be greater than or equal to `min_market_cap_billion`")
    if args.role_scope not in VALID_ROLE_SCOPES:
        raise ValueError("`role_scope` must be all, beneficiary, or pressure")

    outcomes = load_outcomes(Path(args.backtest))
    all_samples = load_samples(Path(args.output_root), outcomes)
    market_cap_samples = [
        sample
        for sample in all_samples
        if market_cap_in_range(sample, args.min_market_cap_billion, args.max_market_cap_billion)
    ]
    samples = [sample for sample in market_cap_samples if role_in_scope(sample, args.role_scope)]
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
        "market_cap_filter": {
            "min_billion": args.min_market_cap_billion,
            "max_billion": args.max_market_cap_billion,
        },
        "role_scope": args.role_scope,
        "raw_sample_count": len(all_samples),
        "market_cap_sample_count": len(market_cap_samples),
        "sample_count": len(samples),
        "excluded_by_market_cap_count": len(all_samples) - len(market_cap_samples),
        "excluded_by_role_count": len(market_cap_samples) - len(samples),
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
    write_json(payload)


def write_json(payload: object) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scan archived A-share selection thresholds against market-cap-aligned backtest labels."
    )
    parser.add_argument("--output-root", default=str(DEFAULT_ROOT), help="Archive root containing input bundles.")
    parser.add_argument("--backtest", required=True, help="Backtest JSON containing evaluated rows.")
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
        help="Minimum market cap in CNY billions for calibration samples.",
    )
    parser.add_argument(
        "--max-market-cap-billion",
        type=float,
        default=DEFAULT_MAX_MARKET_CAP_BILLION,
        help="Maximum market cap in CNY billions for calibration samples.",
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
