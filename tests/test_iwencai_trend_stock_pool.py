from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(".agents/skills/iwencai-trend-stock-pool/scripts/build_stock_pools.py").resolve()


def load_module():
    spec = importlib.util.spec_from_file_location("build_stock_pools", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sample_row() -> dict:
    return {
        "code": "002409.SZ",
        "name": "雅克科技",
        "price": 12.0,
        "amount": 200_000_000,
        "turnover": 5.0,
        "pe": 20.0,
        "pb": 2.0,
        "ma5": 11.9,
        "ma10": 11.8,
        "ma20": 11.4,
        "ma60": 11.2,
        "low": 11.7,
        "low5": 11.6,
        "high20": 12.2,
        "day_ret": 2.0,
        "gap": 1.0,
        "momentum20": 12.0,
        "momentum5": 1.5,
        "vol_ratio": 1.1,
        "avg_range20": 5.0,
        "ma10_dist": 1.7,
        "ma20_dist": 5.3,
        "high20_dist": -1.6,
        "upper_shadow": 0.2,
        "lower_shadow": 0.1,
        "close_position": 0.7,
        "is_core_theme": True,
        "is_satellite_theme": False,
    }


def test_supermind_like_main_theme_row_passes_and_scores() -> None:
    module = load_module()
    row = module.score_row(sample_row())

    assert module.passes_strategy(row, module.STRATEGIES["main_theme"])
    assert row["score"] > 0


def test_high_confidence_filter_matches_profile() -> None:
    module = load_module()
    row = sample_row()
    row.update({"recommend_rank": 1, "rank": 3, "score": 4.0})

    assert module.is_high_confidence_recommendation(row)


def test_not_allowed_excludes_bj_and_star_by_default() -> None:
    module = load_module()

    assert not module.is_allowed_code("430001.BJ", include_star=False)
    assert not module.is_allowed_code("688001.SH", include_star=False)
    assert module.is_allowed_code("688001.SH", include_star=True)
