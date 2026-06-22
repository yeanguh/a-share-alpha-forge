# Fund Flow And Stock Scoring

Use this guide to add whole-market capital direction and stock-level
risk/opportunity analysis. Keep all outputs informational and non-personalized.
Do not provide specific buy/sell prices, position sizes, stop-loss lines, or
personalized portfolio instructions.

## Whole-Market Fund-Flow Direction

Summarize A-share market funding direction before the Top 10 tables.

Check:

- Broad-market turnover: total A-share turnover, turnover change versus the
  prior session and recent average.
- Index fund flow: SSE Composite, SZSE Component, ChiNext, STAR 50, CSI 300,
  CSI 500, and CSI 1000 when available.
- Main capital net flow: broad market and major sectors.
- Sector flow: top inflow and outflow sectors, concentration, and whether flow
  supports the news ranking.
- Northbound/foreign flow when available; otherwise state unavailable.
- ETF flow: broad-index, sector, dividend, technology, medicine, and brokerage
  ETFs when available.
- Margin financing and securities lending changes when available.
- Breadth: rising/falling stock counts, limit-up/limit-down counts, and whether
  money is broadening or crowding into a narrow theme.

Classify fund-flow direction:

- `净流入扩散`: broad inflow, rising turnover, improving breadth.
- `结构性流入`: inflow concentrated in a few sectors or themes.
- `缩量观望`: turnover contracts and no clear sector leadership.
- `净流出扩散`: broad outflow with weakening breadth.
- `拥挤分化`: money crowds into high-beta themes while most stocks weaken.

## Stock-Level Scores

Score every stock from 0 to 5 on these dimensions:

| Dimension | Meaning |
| --- | --- |
| `trend_score` | Latest 14-trading-day K-line trend and relative strength. |
| `volume_score` | Volume/turnover confirmation versus recent averages. |
| `retail_sentiment` | Retail crowding intensity inferred from public or authorized VOC proxies, watchlist heat, discussion heat, small-order behavior, limit-up chasing, or panic selling. Higher means more one-sided retail crowding, not necessarily better opportunity. |
| `retail_voc_quality_score` | Derived by `scripts/score_stocks.py`; balanced VOC scores better than extreme chasing or panic. |
| `capital_recognition` | Institutional/main-money recognition inferred from main capital flow, block trades, ETF/foreign/margin flow, and sustained volume quality. |
| `event_alignment` | Whether the event's impact channel is directly tied to the company. |
| `institutional_trend_score` | Trend-following institutional setup score. Use 14-day K-line structure, MA5/MA10/MA20/MA50 alignment, small-candle grind-up behavior, healthy pullback volume, and broad-market institutional trend context. |
| `risk_score` | Valuation, event uncertainty, crowded trade, disclosure risk, liquidity risk, or sharp abnormal volatility. Higher means higher risk. |

Use `scripts/score_stocks.py` to calculate `research_score`,
`beneficiary_quality_score`, `research_rating`, and `operation_tendency` when
structured observations are available. `research_score` is a general research
score for both opportunity and pressure rows. `beneficiary_quality_score`
prioritizes 14-day trend, volume, main-capital recognition, institutional trend
setup, event alignment, and risk control; use it to rank stocks that already
passed the opportunity gate.

## Institutional Trend Setup

Use `institutional_trend_score` as an internal confirmation factor for the
so-called trend-following slow-grind setup. This is not an independent trading
strategy and must not bypass sector-first or main-capital gates. It is an
auxiliary ranking and annotation field, not a hard recommendation gate.

Score higher when:

- Recent K-line shows a controlled launch or continuation pattern, such as at
  least 3 positive closes in 5 sessions, or a positive 10-session trend with
  closes above short moving averages.
- Price is above MA5 and MA10, MA20 is flat or rising, and strong setups also
  have MA50 rising or recovering.
- The rise is mostly small positive and small negative candles rather than
  consecutive limit-ups, one-word boards, or single-day speculative spikes.
- Pullbacks hold MA10 or MA20 with lower volume than breakout/uptrend days.
- Volume expands on valid breakouts and contracts normally on pullbacks, without
  three consecutive sessions below about 65% of 20-day average turnover.
- Whole-market context supports institutional trend trading: turnover is in the
  recent high percentile or above the configured absolute threshold, active
  sectors keep rotating, and broad risk appetite has not entered a clear
  retreat phase.

Score lower when the move is driven mainly by hot-money limit-up chains,
sharp gap-up-and-fade candles, persistent volume starvation, a break below MA20
without repair, or when market turnover and sector relay have weakened.

## Company Recommendation Gate

Apply this gate before a stock can appear in the report columns
`可能受益A股公司` or `可能承压A股公司`.

Before applying the stock-level gate, the stock must belong to a sector selected
from news-driven `sector_candidates` with the same direction. A technically
strong stock from an unselected sector remains in observation notes only.

For the positive beneficiary list, the selected sector must also pass the
strong-mainline gate before any stock from that sector can enter the opportunity
column:

- `sector impact_score >= 4.0`.
- `sector price_volume >= 4.0`.
- `sector liquidity >= 4.0`.

This gate intentionally excludes technically acceptable stocks from weak,
secondary, or merely defensive themes. Those stocks can still appear in the
mainline readout or observation list, but not in the opportunity column.

For a positive beneficiary list, require all conditions:

- `directional_role` is `beneficiary`.
- The stock is not STAR Market（科创板）, Beijing Stock Exchange（北交所）, ST,
  `*ST`, or delisting-risk.
- `event_alignment >= 3.5`.
- `trend_score >= 3.0`.
- `volume_score >= 3.4`.
- `capital_recognition >= 3.6`.
- If `retail_sentiment >= 4.5`, require `capital_recognition >= 3.8` and
  `volume_score >= 3.4`; otherwise treat it as retail crowding and exclude the
  stock from the beneficiary column.
- `risk_score <= 3.8`.
- `research_rating` is not `风险回避`.

For cyclical resource sectors whose names include `有色`, `金属`, `稀土`, `钨`,
`锡`, `铝`, `煤`, or `钢铁`, apply a stricter beneficiary confirmation gate:
`trend_score >= 3.6`, `volume_score >= 3.6`, and
`capital_recognition >= 3.6`. These sectors are more vulnerable to commodity
price reversals and macro-demand noise, so moderate trend or event alignment is
not enough for the opportunity table.

For a negative pressure-company list, require all conditions:

- `directional_role` is `pressure`.
- The stock is not STAR Market（科创板）, Beijing Stock Exchange（北交所）, ST,
  `*ST`, or delisting-risk.
- `event_alignment >= 3.5`.
- `trend_score <= 2.4`.
- `capital_recognition <= 2.6`.
- Either `volume_score >= 3.2` or `risk_score >= 3.8`.
- `research_rating` is `风险回避`, `谨慎观察`, or `中性观察`.

Post-review calibration: archived candidate-pool scans from 2026-06-01 to
2026-06-05 favored a stricter opportunity gate: stronger main-capital
recognition, capped risk, and no relaxation for moderate resource-price
themes. A follow-up sector-gated replay over the same window favored requiring
positive opportunities to come from sectors with strong impact, price-volume,
and liquidity confirmation. Treat this as a minimum evidence threshold, not a
guarantee. Keep raising confidence only when later daily or weekly reviews show
the same pattern.

Post-review calibration: do not place a stock in the pressure-company column
only because its theme is crowded, valuation is high, or a macro/industry item
is negative. If a stock still has `trend_score >= 3.2` and
`capital_recognition >= 3.0`, treat the negative thesis as a watch-list risk
unless price and capital data later confirm deterioration. This rule prevents
strong mainline reversals from being mislabeled as pressure candidates.

Crowding-only sectors or concepts whose names are built around `高位`, `拥挤`,
`过热`, or `追涨` are risk-observation themes by default. They can produce a
pressure-company row only when deterioration is already clear:
`trend_score <= 2.2` and `capital_recognition <= 2.5`. Otherwise, keep the stock
in the mainline leader or observation table with a crowding-risk note.

Disconfirmation-only sectors or concepts whose names are built around `证伪`,
`传闻落空`, `澄清`, or `辟谣` follow the same rule. A debunked theme is not
enough by itself: require visible price deterioration and weak capital
recognition before listing a pressure company. Otherwise, keep it as an
observation risk.

For both lists, prefer main capital recognition and 14-day price/volume
confirmation over retail VOC. Retail VOC is a contrarian or crowding signal, not
the primary reason to include a stock. The practical rule is: do not stand with
crowded retail opinion unless main capital and volume already confirm it; follow
main capital first when the two conflict.

When retail VOC is hot but main capital and 14-day volume confirm the same
positive direction, keep the stock eligible but mark the risk as crowding or
high-positioning risk. Do not mechanically turn high retail heat into a
negative signal.

If a company fails the gate:

- Do not list it in the positive or negative Top 10 company column.
- Put it in the stock detail section as `未入选推荐列`.
- Explain the exclusion reason, such as `量能不足`, `散户情绪过热`,
  `资金认可度不足`, `量能确认不足`, `风险过高`, or `事件关联不足`.

## Research Rating

Use these non-personalized research labels:

- `高关注`: strong catalyst, strong capital recognition, trend/volume
  confirmation, manageable risk.
- `关注`: catalyst and capital recognition are positive, but confirmation or
  risk is mixed.
- `中性观察`: opportunity and risk are balanced, or data is incomplete.
- `谨慎观察`: risk, crowding, or weak capital recognition offsets the catalyst.
- `风险回避`: event risk, trend deterioration, or heavy outflow dominates.

## Operation Tendency

Use these informational operation tendencies only:

- `等待放量确认`: catalyst is promising but volume/price confirmation is not
  enough.
- `趋势跟踪观察`: trend and capital recognition are supportive; continue
  monitoring confirmation.
- `回撤后再评估`: catalyst is valid but short-term crowding or overheating is
  high.
- `事件落地后再评估`: key uncertainty has not been resolved.
- `风险回避观察`: downside or event uncertainty dominates.
- `仅作主题跟踪`: company linkage is indirect or data confidence is low.
- `仅作风险跟踪`: negative catalyst is relevant, but the stock fails the
  pressure-company recommendation gate.

Never write direct personalized actions such as buy, sell, hold, add, reduce,
full position, half position, target price, or stop-loss price.
