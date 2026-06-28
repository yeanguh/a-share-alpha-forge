from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/stock_workbench.py").resolve()


def load_module():
    spec = importlib.util.spec_from_file_location("stock_workbench", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_render_selection_markdown_groups_candidates() -> None:
    module = load_module()
    markdown = module.render_selection_markdown(
        {
            "date": "2026-06-26",
            "generated_at": "2026-06-28T21:26:13",
            "theme": "存储芯片",
            "summary": {"total": 1, "core": 1, "watch": 0, "reject": 0},
            "iwencai": {"status": "generated"},
            "mainlines": [{"title": "存储芯片", "impact_score": 4.46}],
            "candidates": [
                {
                    "code": "603986",
                    "name": "兆易创新",
                    "sector": "存储芯片",
                    "bucket": "core",
                    "score": 74.81,
                    "quote": {"latest": 128.0, "pe_ttm": 88.0},
                    "reasons": ["已通过日报受益股门禁"],
                    "missing_evidence": ["缺少问财趋势承接信号"],
                }
            ],
        }
    )

    assert "# 综合选股报告 2026-06-26" in markdown
    assert "## 核心池" in markdown
    assert "| 603986 | 兆易创新 | 存储芯片 | 74.81 | 价 128.0；PE 88.0 |" in markdown


def test_run_integrated_selection_writes_tmp_report(monkeypatch) -> None:
    module = load_module()
    test_tmp = module.ROOT / "tmp" / "pytest-workbench-selection"
    monkeypatch.setattr(module, "TMP", test_tmp)

    def fake_run_command(command, *, cwd=module.ROOT, timeout=120):  # noqa: ANN001
        output = Path(command[command.index("--output") + 1])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            """
{
  "date": "2026-06-26",
  "generated_at": "2026-06-28T21:26:13",
  "theme": null,
  "summary": {"total": 0, "core": 0, "watch": 0, "reject": 0},
  "iwencai": {"status": "generated"},
  "mainlines": [],
  "candidates": []
}
""".strip(),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout=str(output), stderr="")

    monkeypatch.setattr(module, "run_command", fake_run_command)

    result = module.run_integrated_selection(
        {
            "date": "2026-06-26",
            "max_candidates": 7,
            "refresh_quotes": True,
            "quote_limit": 2,
            "committee_mode": "local",
        }
    )

    assert result["payload"]["summary"]["total"] == 0
    assert result["output"].startswith("tmp/pytest-workbench-selection/integrated_selection_")
    assert result["markdown_output"].endswith(".md")
    assert "--refresh-quotes" in result["command"]
    assert "--quote-limit 2" in result["command"]


def test_vibe_committee_target_formats_a_share_context() -> None:
    module = load_module()
    target = module.vibe_committee_target(
        {
            "code": "603986",
            "name": "兆易创新",
            "sector": "存储芯片",
            "bucket": "core",
            "score": 74.81,
            "quote": {"latest": 367.18, "pe_ttm": 88.2},
            "reasons": ["已通过日报受益股门禁"],
            "missing_evidence": ["缺少产业链/卡口映射"],
        }
    )

    assert target.startswith("603986.SH 兆易创新")
    assert "bucket=core" in target
    assert "selection_evidence=已通过日报受益股门禁" in target
