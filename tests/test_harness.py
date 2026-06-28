from __future__ import annotations

from harness.runner import load_manifest, render_markdown, run_harness, selected_checks


def test_manifest_lists_core_capabilities() -> None:
    manifest = load_manifest()
    capability_ids = {capability["id"] for capability in manifest["capabilities"]}
    assert "daily-a-share-news-impact" in capability_ids
    assert "industry-chain-analysis" in capability_ids
    assert "stock-workbench" in capability_ids
    assert "report" in capability_ids


def test_selected_checks_expand_full_mode() -> None:
    manifest = load_manifest()
    ids = {check["id"] for check in selected_checks(manifest, "full")}
    assert "manifest.paths" in ids
    assert "pytest.unit" in ids
    assert "report.build-data" in ids
    assert "workbench.api" not in ids


def test_harness_manifest_path_check_passes() -> None:
    report = run_harness("smoke", checks={"manifest.paths"})
    assert report.ok
    assert report.summary["passed"] == 1
    assert report.results[0].id == "manifest.paths"


def test_markdown_report_contains_capabilities() -> None:
    report = run_harness("smoke", checks={"manifest.paths"})
    markdown = render_markdown(report)
    assert "# Harness Report: smoke" in markdown
    assert "`daily-a-share-news-impact`" in markdown
    assert "`manifest.paths`" in markdown
