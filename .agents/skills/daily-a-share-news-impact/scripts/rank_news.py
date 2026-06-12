#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

CHINA_TZ = ZoneInfo("Asia/Shanghai")
Direction = Literal["positive", "negative", "mixed"]


@dataclass(frozen=True)
class Window:
    start: datetime
    end: datetime

    def to_dict(self) -> dict[str, str]:
        return {
            "timezone": "Asia/Shanghai",
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
        }


@dataclass(frozen=True)
class Candidate:
    title: str
    direction: Direction
    magnitude: float
    breadth: float
    immediacy: float
    confidence: float
    novelty: float
    liquidity: float
    price_volume: float

    @property
    def impact_score(self) -> float:
        return round(
            0.30 * self.magnitude
            + 0.18 * self.breadth
            + 0.12 * self.immediacy
            + 0.15 * self.confidence
            + 0.08 * self.novelty
            + 0.07 * self.liquidity
            + 0.10 * self.price_volume,
            2,
        )

    def to_ranked_dict(self, rank: int) -> dict[str, float | int | str]:
        return {
            "rank": rank,
            "title": self.title,
            "direction": self.direction,
            "impact_score": self.impact_score,
            "magnitude": self.magnitude,
            "breadth": self.breadth,
            "immediacy": self.immediacy,
            "confidence": self.confidence,
            "novelty": self.novelty,
            "liquidity": self.liquidity,
            "price_volume": self.price_volume,
        }


def previous_trading_date(current: date) -> date:
    if current.weekday() == 0:
        return current - timedelta(days=3)
    if current.weekday() == 6:
        return current - timedelta(days=2)
    if current.weekday() == 5:
        return current - timedelta(days=1)
    return current - timedelta(days=1)


def latest_report_anchor(now: datetime | None = None) -> datetime:
    current = now.astimezone(CHINA_TZ) if now else datetime.now(CHINA_TZ)
    report_time = time(hour=9, minute=30)
    today_anchor = datetime.combine(current.date(), report_time, CHINA_TZ)
    if current.weekday() >= 5:
        anchor_date = previous_trading_date(current.date())
    elif current >= today_anchor:
        anchor_date = current.date()
    else:
        anchor_date = previous_trading_date(current.date())
    return datetime.combine(anchor_date, report_time, CHINA_TZ)


def latest_completed_window(now: datetime | None = None) -> Window:
    end = latest_report_anchor(now)
    start = datetime.combine(previous_trading_date(end.date()), time(hour=9, minute=30), CHINA_TZ)
    return Window(start=start, end=end)


def parse_now(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=CHINA_TZ)
    return parsed


def require_score(value: object, field_name: str) -> float:
    if not isinstance(value, int | float):
        raise ValueError(f"`{field_name}` must be a number from 0 to 5")
    score = float(value)
    if score < 0 or score > 5:
        raise ValueError(f"`{field_name}` must be from 0 to 5")
    return score


def require_direction(value: object) -> Direction:
    if value not in {"positive", "negative", "mixed"}:
        raise ValueError("`direction` must be positive, negative, or mixed")
    return value


def load_candidates(path: Path) -> list[Candidate]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Candidate file must contain a JSON array")

    candidates: list[Candidate] = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Candidate #{index} must be an object")
        title = item.get("title")
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"Candidate #{index} must include non-empty `title`")
        candidates.append(
            Candidate(
                title=title.strip(),
                direction=require_direction(item.get("direction")),
                magnitude=require_score(item.get("magnitude"), "magnitude"),
                breadth=require_score(item.get("breadth"), "breadth"),
                immediacy=require_score(item.get("immediacy"), "immediacy"),
                confidence=require_score(item.get("confidence"), "confidence"),
                novelty=require_score(item.get("novelty"), "novelty"),
                liquidity=require_score(item.get("liquidity"), "liquidity"),
                price_volume=require_score(item.get("price_volume"), "price_volume"),
            )
        )
    return candidates


def window_command(args: argparse.Namespace) -> None:
    window = latest_completed_window(parse_now(args.now))
    write_json(window.to_dict())


def rank_command(args: argparse.Namespace) -> None:
    candidates = load_candidates(Path(args.input))
    if args.by_direction:
        write_json(
            {
                "positive": rank_candidates(candidates, "positive", args.top_positive),
                "negative": rank_candidates(candidates, "negative", args.top_negative),
            }
        )
        return

    if args.direction:
        write_json(rank_candidates(candidates, args.direction, args.top))
        return

    write_json(rank_candidates(candidates, None, args.top))


def rank_candidates(
    candidates: list[Candidate],
    direction: Direction | None,
    limit: int,
) -> list[dict[str, float | int | str]]:
    filtered = [candidate for candidate in candidates if direction is None or candidate.direction == direction]
    ranked = sorted(filtered, key=lambda candidate: candidate.impact_score, reverse=True)
    return [candidate.to_ranked_dict(rank) for rank, candidate in enumerate(ranked[:limit], start=1)]


def write_json(payload: object) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rank A-share investment news candidates.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    window_parser = subparsers.add_parser("window", help="Print the latest completed 09:30 report window.")
    window_parser.add_argument("--now", help="Optional ISO datetime, interpreted as China time when naive.")
    window_parser.set_defaults(func=window_command)

    rank_parser = subparsers.add_parser("rank", help="Rank structured news candidates.")
    rank_parser.add_argument("--input", required=True, help="Path to a JSON array of candidate objects.")
    rank_parser.add_argument("--top", type=int, default=10, help="Number of ranked candidates to print.")
    rank_parser.add_argument("--direction", choices=["positive", "negative", "mixed"], help="Rank only one direction.")
    rank_parser.add_argument(
        "--by-direction", action="store_true", help="Print separate positive and negative rankings."
    )
    rank_parser.add_argument(
        "--top-positive", type=int, default=10, help="Positive items to print with --by-direction."
    )
    rank_parser.add_argument(
        "--top-negative", type=int, default=10, help="Negative items to print with --by-direction."
    )
    rank_parser.set_defaults(func=rank_command)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
