# Integrated A-Share Selection Framework

## Signal Stack

Use these layers in order:

| Layer | Source | Purpose |
| --- | --- | --- |
| Event/theme | `daily-a-share-news-impact` archive | Identify active mainlines and avoid stale concepts |
| Industry chain | `industry-chain-analysis` reports | Map the theme to real products, links, and listed companies |
| Bottleneck | `serenity-bottleneck-investing` | Find scarce upstream links with value-capture power |
| Fundamentals | `china-stock-analysis` | Check profitability, solvency, growth, anomalies, and valuation context |
| Quote/valuation | `china-stock-price-analysis` | Confirm price, PE/PB, market cap, and current quote availability |
| News/data expansion | `investment-news`, `a-stock-data`, Vibe-Trading | Add fresh headlines, fund flow, reports, alpha/backtest signals when needed |

## Scoring Dimensions

The bundled script converts 0-5 archive scores to a 0-100 research priority:

- Event alignment and mainline strength
- Beneficiary quality
- Capital recognition
- Trend and volume confirmation
- Institutional trend
- Retail VOC quality
- Risk control
- Industry/bottleneck report match
- Source reliability bonus for `eligible_beneficiaries` and `leading_stocks`

The score is a research-priority score, not a buy rating. Keep the original
evidence beside every score so the user can inspect why a name ranked highly.

## Pool Buckets

| Bucket | Use |
| --- | --- |
| Core pool | Strong archive evidence plus acceptable risk; worth immediate deeper research |
| Watchlist | One or two missing confirmations, high valuation, crowding, or indirect industry exposure |
| Reject/exclusion | Failed gates, ST/delisting risk, missing data, weak relevance, or explicit archive exclusion |

## Evidence Requirements

For each core or watchlist candidate, include:

- Code and name
- Theme/sector and source tags
- Total score and key sub-scores
- Why it entered the pool
- Current missing evidence or invalidation point
- Linked industry report matches, if any

For new themes, do not rank before mapping:

1. Demand driver
2. Value chain links
3. Bottleneck candidates
4. Listed-company exposure proof
5. Stock-level confirmation
6. Risk and invalidation triggers
