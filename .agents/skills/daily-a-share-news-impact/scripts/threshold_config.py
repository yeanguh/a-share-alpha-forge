#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_THRESHOLD_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "default_thresholds.json"


def load_thresholds(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else DEFAULT_THRESHOLD_CONFIG_PATH
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"`{config_path}` must contain a JSON object")
    return payload


def threshold_version(config: dict[str, Any]) -> str:
    value = config.get("version")
    return value if isinstance(value, str) and value.strip() else "unknown"


def get_value(config: dict[str, Any], *path: str) -> Any:
    value: Any = config
    for key in path:
        if not isinstance(value, dict) or key not in value:
            raise KeyError(".".join(path))
        value = value[key]
    return value


def get_number(config: dict[str, Any], *path: str) -> float:
    value = get_value(config, *path)
    if not isinstance(value, (int, float)):
        raise ValueError(f"`{'.'.join(path)}` must be numeric")
    return float(value)


def get_int(config: dict[str, Any], *path: str) -> int:
    value = get_value(config, *path)
    if not isinstance(value, int):
        raise ValueError(f"`{'.'.join(path)}` must be an integer")
    return value
