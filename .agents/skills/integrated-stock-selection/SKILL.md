---
name: integrated-stock-selection
description: 整合本仓库 A 股选股能力的总控 skill。用于用户要求选股、筛选股票、生成股票池/观察池、按日期报告找候选股、按主题或产业链找 A 股标的、把新闻主线/产业链卡口/基本面估值/量价资金/风险排除合并成候选池、复盘股票池质量、或需要调度 daily-a-share-news-impact、industry-chain-analysis、serenity-bottleneck-investing、china-stock-analysis、china-stock-price-analysis、investment-news、a-stock-data、Vibe-Trading 等能力完成研究型选股时。
---

# Integrated Stock Selection

## Core Rule

Use this skill as the orchestration layer. Do not replace the existing skills:
reuse their archived outputs and scripts, then produce a ranked research pool
with evidence, exclusions, and the next verification step. All conclusions are
for research and review only, not trading instructions.

## Default Workflow

1. Run or load `iwencai-trend-stock-pool` first. Treat its
   `high_confidence_recommendations`, `recommendations`, and per-strategy pools
   as the initial technical candidate set.
2. Start from the latest or requested `local/YYYY-MM-DD/assembled.json`.
   Prefer `eligible_beneficiaries`, then `leading_stocks`, then `stocks` as
   cross-check evidence on top of the iWenCai trend pool.
3. Add theme evidence from `daily_mainlines` and `sector_rankings`.
4. Add industry and bottleneck evidence from `industry-analysis/*/source_data.json`.
   If the user asks a new industry question, use `industry-chain-analysis` and
   `serenity-bottleneck-investing` before ranking stocks.
5. Add quote, valuation, financial, and risk context only for the narrowed set.
   Use `china-stock-price-analysis` for quick quote/valuation and
   `china-stock-analysis` for deeper fundamentals.
6. Treat `a-stock-data` and Vibe-Trading as expandable data/factor toolboxes:
   use them when the requested factor, news, fund-flow, alpha, backtest, or
   local `a-data` capability is not already present in the archive.
7. Output four lists: core pool, watchlist, reject/exclusion list, and missing
   evidence. Keep generated files in `tmp/` unless the user explicitly asks to
   archive a report.

## Quick Start

Generate a ranked pool from the latest local report:

```bash
uv run python .agents/skills/integrated-stock-selection/scripts/run_integrated_selection.py
```

This default command first runs `iwencai-trend-stock-pool` into
`tmp/integrated-selection/iwencai-*`, then evaluates the resulting candidates
against archived reports, industry mappings, and optional quote refreshes.

Generate a theme-specific pool and Markdown report:

```bash
uv run python .agents/skills/integrated-stock-selection/scripts/run_integrated_selection.py \
  --date 2026-06-26 \
  --theme 存储芯片 \
  --format markdown \
  --output tmp/integrated-selection/storage-2026-06-26.md
```

Evaluate explicit codes against the latest archive:

```bash
uv run python .agents/skills/integrated-stock-selection/scripts/run_integrated_selection.py \
  --codes 603986,600584,002156 \
  --max-candidates 8
```

Reuse an existing iWenCai run when iterating:

```bash
uv run python .agents/skills/integrated-stock-selection/scripts/run_integrated_selection.py \
  --iwencai-json tmp/iwencai-trend-stock-pool/e2e-full/stock_pools.json \
  --refresh-quotes
```

Use `--refresh-quotes` only when the user asks for current price/valuation
confirmation; it calls the existing `china-stock-price-analysis` script and
writes temporary snapshots under `tmp/integrated-selection/`.

## Decision Rules

- Use iWenCai trend-support candidates as the first pass; then promote or
  demote them with archive, industry, valuation, and risk evidence.
- Prefer names that have both iWenCai trend support and archive-backed evidence
  over single-source concept-only names.
- Promote a stock to the core pool only when event alignment, beneficiary
  quality, institutional trend, and capital/volume confirmation are all present,
  or when it passes iWenCai `high_confidence_v1` and survives valuation/risk
  checks.
- Keep high-retail-heat or extreme-valuation names in the watchlist unless the
  evidence also shows strong capital and trend confirmation.
- Use industry/bottleneck reports to explain why a company belongs to a value
  chain; do not let an industry tag alone override weak stock-level evidence.
- Put ST, delisting-risk, missing-code, no-data, or explicit failed-gate names
  into the reject/exclusion list with the reason.
- For new topics without archived evidence, first build the chain and candidate
  map, then score; do not invent a ranked pool from headlines alone.

## References

- Read `references/selection-framework.md` when building or modifying the
  scoring and evidence framework.
- Read `references/capability-map.md` when deciding which existing skill or web
  tool should provide a missing signal.
