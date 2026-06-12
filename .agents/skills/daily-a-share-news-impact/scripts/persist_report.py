#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_ROOT = Path(".local/daily-a-share-news-impact")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"`{path}` must contain a JSON object")
    return payload


def report_date_from_bundle(bundle: dict[str, Any]) -> str:
    window = bundle.get("window")
    if not isinstance(window, dict):
        raise ValueError("Bundle must include object `window`")
    end = window.get("end")
    if not isinstance(end, str):
        raise ValueError("Bundle window must include string `end`")
    return datetime.fromisoformat(end).date().isoformat()


def copy_if_present(source: Path | None, target: Path) -> None:
    if source is None:
        return
    if not source.exists():
        raise FileNotFoundError(source)
    if source.resolve() == target.resolve():
        return
    shutil.copyfile(source, target)


def persist_command(args: argparse.Namespace) -> None:
    bundle_path = Path(args.bundle)
    bundle = load_json(bundle_path)
    report_date = args.date or report_date_from_bundle(bundle)
    output_dir = Path(args.output_root) / report_date
    output_dir.mkdir(parents=True, exist_ok=True)

    copy_if_present(bundle_path, output_dir / "input_bundle.json")
    copy_if_present(Path(args.assembled) if args.assembled else None, output_dir / "assembled.json")
    copy_if_present(Path(args.report) if args.report else None, output_dir / "report.md")
    copy_if_present(Path(args.close_review) if args.close_review else None, output_dir / "close_review.json")

    files = sorted(path.name for path in output_dir.iterdir() if path.is_file())
    if "metadata.json" not in files:
        files.append("metadata.json")
        files.sort()
    metadata = {
        "report_date": report_date,
        "window": bundle.get("window", {}),
        "files": files,
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    write_json({"output_dir": str(output_dir), **metadata})


def write_json(payload: object) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Persist daily A-share brief inputs, outputs, and review data.")
    parser.add_argument("--bundle", required=True, help="Path to the daily input bundle JSON.")
    parser.add_argument("--assembled", help="Path to assembled scoring output JSON.")
    parser.add_argument("--report", help="Path to the final Markdown report.")
    parser.add_argument("--close-review", help="Path to post-close review JSON created after 15:00 China time.")
    parser.add_argument("--date", help="Override report date in YYYY-MM-DD format.")
    parser.add_argument("--output-root", default=str(DEFAULT_ROOT), help="Archive root directory.")
    parser.set_defaults(func=persist_command)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
