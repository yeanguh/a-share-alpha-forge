# Capability Map

| Need | Preferred Capability | Notes |
| --- | --- | --- |
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

1. Local archive
2. Local industry report/source data
3. Existing repo scripts
4. Public no-key data endpoints
5. Optional-key or LLM-dependent tools

Write temporary outputs to `tmp/integrated-selection/`.
