# Market Data Checklist

Use recent price and volume behavior as confirmation, not as a standalone
recommendation signal.

## Required Checks

For every stock included in the final affected-company tables, check the latest
14 trading days. If a full 14-day series is unavailable, state the data gap and
lower the confidence label.

- Latest close, one-day change, and intraday direction when available.
- Fourteen-day K-line structure: higher highs/lows, lower highs/lows,
  consolidation range, gap, long upper/lower shadows, breakout, breakdown, or
  reversal.
- Five-, ten-, and fourteen-trading-day trend relative to moving averages.
- Volume or turnover versus the recent five- and fourteen-day average.
- Relative strength versus CSI 300, CSI 500, STAR 50, ChiNext, or the relevant
  sector index.
- Main capital net flow, large-order flow, retail participation proxies, and
  margin financing changes when available.
- Whether price and volume confirm, lag, or contradict the news direction.

## Free-Only Daily Data Sources

Use free available sources for routine daily runs before falling back to
qualitative summaries:

- `china-stock-analysis`: akshare `stock_zh_a_hist` through
  `scripts/data_fetcher.py --data-type valuation` for latest price, latest
  change, volume, turnover, 60-day high/low, 20-day average volume, and the
  latest 30 daily bars. Use the latest 14 bars from this output for the daily
  K-line check.
- `china-stock-analysis`: akshare `stock_individual_info_em` through
  `--data-type basic` for industry, market cap, float cap, PE, PB, listing
  date, and sector-mapping cross-checks.
- `iTick`: REST quote/K-line endpoints when a free `ITICK_API_TOKEN` is
  configured.
- `Zhitu`: REST real-time quote, technical indicator, and fund-flow-style
  endpoints when a free `ZHITU_API_TOKEN` is configured. Treat the public demo
  token as connectivity evidence only; do not use demo responses for stock
  conclusions.
- Sina public quote API: no-key real-time quote text for spot-price and one-day
  direction cross-checks.
- Tencent public quote API: no-key quote text as the second public quote
  cross-check.
- Eastmoney public quote API: no-key JSON quote source when reachable.
- Baostock: no-key daily historical K-line fallback when installed.

Paid interfaces such as QVeris, paid Tushare Pro tiers, terminal feeds, or
similar commercial APIs are excluded from routine daily runs. Use them only if
the user explicitly requests a paid-source run.

If these optional tools are unavailable because a free API token is missing, a
package is missing, or a provider fetch fails, write the exact health-check
status into `evidence_gaps` and lower data quality to `partial` or `limited`.

## Source Priority

For stock-level quote and K-line data, use this order:

1. akshare through `china-stock-analysis`.
2. Sina public quote API.
3. Tencent public quote API.
4. Eastmoney public quote API.
5. Baostock when installed.
6. iTick when a free `ITICK_API_TOKEN` is set.
7. Zhitu when a free `ZHITU_API_TOKEN` is set.

For a final report, prefer at least two available sources for price and volume
confirmation. If only no-key public quote APIs are available, use them for spot
quote direction only and keep 14-trading-day K-line confidence limited.

## Security Exclusion Gate

Market cap is displayed as context only and must not exclude a stock from the
opportunity or pressure table. Every stock in those tables must still pass the
sector-first, price/volume, retail VOC, capital-recognition, event-alignment,
and risk gates.

Exclude STAR Market（科创板）, Beijing Stock Exchange（北交所）, ST, `*ST`, and
delisting-risk stocks from opportunity and pressure tables. List them under
excluded/observation notes when they are otherwise relevant to the theme.

## Interpreting Positive News

- Strong confirmation: price breaks above recent range or moving average with
  expanding volume.
- Weak confirmation: price rises but volume fades, `volume_score < 3.4`, or
  only one representative name reacts.
- Divergence: price falls on heavy volume despite positive news. Lower the
  `price_volume` score and mention possible profit-taking or skepticism.
- Cyclical resource confirmation: for `有色`, `金属`, `稀土`, `钨`, `锡`, `铝`,
  `煤`, or `钢铁` themes, require stronger trend, volume, and capital
  confirmation than for policy-driven technology themes. Commodity-linked
  equities can reverse quickly when price expectations or macro demand weaken.

## Interpreting Negative News

- Strong confirmation: affected names break down or underperform with expanding
  volume.
- Weak confirmation: affected names drift lower without volume expansion.
- Divergence: affected names resist declines or rebound on volume. Lower the
  negative item confidence or explain that the risk may be partly priced in.
- Strong-mainline override: if a negative or crowding thesis applies to a stock
  whose 14-day trend and main-capital recognition remain positive, keep the
  stock in observation or the mainline leader table until price/volume
  deterioration is visible. Do not place it in the pressure-company column from
  valuation, crowded positioning, or macro weakness alone.
- For sectors or concepts framed mainly as `高位`, `拥挤`, `过热`, or `追涨`,
  require a visible breakdown before pressure inclusion. Without that
  breakdown, report them as risk notes attached to the mainline leader table.
- For sectors or concepts framed mainly as `证伪`, `传闻落空`, `澄清`, or
  `辟谣`, also require a visible breakdown before pressure inclusion. A failed
  story can become a short squeeze or speculative rebound if price and capital
  have not confirmed deterioration.

## Reporting

- Summarize K-line and volume evidence in one short phrase per item.
- Do not overfit one-day moves. Prefer fourteen-day trend plus volume
  confirmation.
- If data is unavailable, state `量价数据不足` and set `price_volume` to `0`.
