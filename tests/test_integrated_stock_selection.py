from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(".agents/skills/integrated-stock-selection/scripts/run_integrated_selection.py").resolve()


def load_module():
    spec = importlib.util.spec_from_file_location("run_integrated_selection", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_theme_selection_uses_archive_and_scores_candidates() -> None:
    module = load_module()
    date, archive = module.load_archive("2026-06-26")
    candidates = module.collect_candidates(archive, [], "存储芯片")
    rows = [module.render_candidate(candidate) for candidate in candidates.values()]
    rows.sort(key=lambda row: row["score"], reverse=True)

    assert date == "2026-06-26"
    assert rows
    assert rows[0]["code"] == "603986"
    assert rows[0]["bucket"] == "core"
    assert "eligible_beneficiaries" in rows[0]["source_tags"]


def test_explicit_codes_do_not_pull_all_industry_companies() -> None:
    module = load_module()
    _, archive = module.load_archive("2026-06-26")
    candidates = module.collect_candidates(archive, ["603986"], None)

    assert "603986" in candidates
    assert "601138" not in candidates
