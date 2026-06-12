#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

DEFAULT_ROOT = Path(".local/daily-a-share-news-impact")
ReviewFrequency = Literal["daily", "weekly"]


@dataclass(frozen=True)
class ReviewRecord:
    report_date: date
    direction_hit: bool
    average_stock_error: float
    lesson: str

    def to_dict(self) -> dict[str, bool | float | str]:
        return {
            "report_date": self.report_date.isoformat(),
            "direction_hit": self.direction_hit,
            "average_stock_error": self.average_stock_error,
            "lesson": self.lesson,
        }


def require_bool(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"`{field_name}` must be a boolean")
    return value


def require_number(value: object, field_name: str) -> float:
    if not isinstance(value, int | float):
        raise ValueError(f"`{field_name}` must be a number")
    return float(value)


def require_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"`{field_name}` must be a non-empty string")
    return value.strip()


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def load_review_record(day_dir: Path) -> ReviewRecord | None:
    path = day_dir / "close_review.json"
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"`{path}` must contain a JSON object")
    return ReviewRecord(
        report_date=parse_date(day_dir.name),
        direction_hit=require_bool(payload.get("direction_hit"), "direction_hit"),
        average_stock_error=require_number(payload.get("average_stock_error"), "average_stock_error"),
        lesson=require_text(payload.get("lesson"), "lesson"),
    )


def day_dirs(root: Path, start: date | None, end: date | None) -> list[Path]:
    directories: list[Path] = []
    for child in root.iterdir() if root.exists() else []:
        if not child.is_dir():
            continue
        try:
            current = parse_date(child.name)
        except ValueError:
            continue
        if start and current < start:
            continue
        if end and current > end:
            continue
        directories.append(child)
    return sorted(directories)


def group_key(record: ReviewRecord, frequency: ReviewFrequency) -> str:
    if frequency == "daily":
        return record.report_date.isoformat()
    year, week, _ = record.report_date.isocalendar()
    return f"{year}-W{week:02d}"


def summarize(records: list[ReviewRecord], frequency: ReviewFrequency) -> dict[str, Any]:
    groups: dict[str, list[ReviewRecord]] = {}
    for record in records:
        groups.setdefault(group_key(record, frequency), []).append(record)

    summaries: list[dict[str, Any]] = []
    for key, group in sorted(groups.items()):
        hit_count = sum(1 for record in group if record.direction_hit)
        average_error = sum(record.average_stock_error for record in group) / len(group)
        summaries.append(
            {
                "period": key,
                "review_days": len(group),
                "direction_hit_rate": round(hit_count / len(group), 3),
                "average_stock_error": round(average_error, 3),
                "lessons": [record.lesson for record in group],
            }
        )
    return {"frequency": frequency, "summaries": summaries}


def review_command(args: argparse.Namespace) -> None:
    records = [
        record
        for directory in day_dirs(
            Path(args.output_root),
            parse_date(args.start) if args.start else None,
            parse_date(args.end) if args.end else None,
        )
        if (record := load_review_record(directory)) is not None
    ]
    write_json(summarize(records, args.frequency))


def write_json(payload: object) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize daily or weekly A-share strategy review records.")
    parser.add_argument("--output-root", default=str(DEFAULT_ROOT), help="Archive root directory.")
    parser.add_argument("--frequency", choices=["daily", "weekly"], default="weekly", help="Review frequency.")
    parser.add_argument("--start", help="Start date in YYYY-MM-DD format.")
    parser.add_argument("--end", help="End date in YYYY-MM-DD format.")
    parser.set_defaults(func=review_command)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
