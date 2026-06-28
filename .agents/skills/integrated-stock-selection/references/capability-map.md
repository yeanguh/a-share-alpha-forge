# Capability Map

| Need | Preferred Capability | Notes |
| --- | --- | --- |
| First-pass trend-support stock pool | `iwencai-trend-stock-pool` | Run before integrated evaluation unless explicitly skipped |
| Latest local report or close review | `web-apps/report`, `local/YYYY-MM-DD/` | Use archived facts before web refreshes |
| Daily mainline and candidate gates | `daily-a-share-news-impact` | Primary source for event alignment and stock gates |
| Industry chain and A-share mapping | `industry-chain-analysis` | Use for theme-to-company relevance |
| Bottleneck/chokepoint thesis | `serenity-bottleneck-investing` | Use before promoting upstream scarcity names |
| Quick quote and relative valuation | `china-stock-price-analysis` | Best after narrowing to a small candidate list |
| Fundamental fetch/anomaly check | `china-stock-analysis` | Use for deeper company research |
| Broad public A-share endpoints | `a-stock-data` | Use as code/API reference for data not already wrapped |
| News dashboard | `investment-news` | Refresh only when the user needs fresh news |
| Alpha, factor, backtest, local data | Vibe-Trading | Use local `a-data` where available; LLM/swarm requires provider key |

## Orchestration Preference

Use the cheapest reliable layer first:

1. `iwencai-trend-stock-pool` output, preferably an existing `stock_pools.json`
2. Local archive
3. Local industry report/source data
4. Existing repo scripts
5. Public no-key data endpoints
6. Optional-key or LLM-dependent tools

Write temporary outputs to `tmp/integrated-selection/`.
