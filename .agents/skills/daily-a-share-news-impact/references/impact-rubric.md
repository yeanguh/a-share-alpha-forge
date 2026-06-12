# Impact Rubric

Use this rubric to rank candidate investment news by likely short-term impact on
A-share market volatility and direction.

## Hard Filters

Reject an item when any condition applies:

- The event is outside the reporting window and has no new confirmation,
  escalation, or market transmission inside the window.
- The item is only a rumor, unsourced social-media post, or unverifiable quote.
- The item is routine commentary, repeated preview, or a strategy view without a
  concrete new catalyst.
- The market effect is narrow, weak, or already fully digested unless the user
  asks for a broader watchlist.
- The company-impact path cannot be explained at least at sector level.

## Score Dimensions

Score each dimension from 0 to 5.

| Dimension | Meaning |
| --- | --- |
| `magnitude` | Expected price or sentiment effect on affected sectors or indices. |
| `breadth` | Number and market-cap weight of sectors or companies affected. |
| `immediacy` | Likelihood the impact appears within one to three trading sessions. |
| `confidence` | Source quality, confirmation level, and clarity of transmission path. |
| `novelty` | New information versus already expected or previously priced content. |
| `liquidity` | Relevance to liquid A-share names, index weights, or high-turnover sectors. |
| `price_volume` | Recent K-line, volume, turnover, and relative-strength confirmation for representative affected companies or sector ETFs. |

Default weighted score:

```text
impact_score =
  0.30 * magnitude
  + 0.18 * breadth
  + 0.12 * immediacy
  + 0.15 * confidence
  + 0.08 * novelty
  + 0.07 * liquidity
  + 0.10 * price_volume
```

Rank positive and negative candidates separately. Keep `positive` and
`negative` as directional labels. Split material `mixed` events into separate
positive and negative entries before ranking.

## Direction Guide

- `positive`: likely improves earnings, valuation, liquidity, risk appetite, or
  policy expectations for affected A-shares.
- `negative`: likely worsens earnings, valuation, liquidity, risk appetite, or
  regulatory/geopolitical risk for affected A-shares.
- `mixed`: creates clear winners and losers. Split likely affected companies by
  impact direction.

## Market Direction Estimate

Estimate the short-term market direction over the next one to three trading
sessions. Weigh:

- Net positive versus negative score across the positive Top 10 and negative
  Top 10.
- Index-weighted breadth, not just the number of items.
- Whether catalysts affect risk appetite broadly or only one theme.
- K-line and volume confirmation across representative affected companies,
  sector ETFs, and broad indices.
- External-market leads such as US equities, China ADRs, CNH, rates, crude,
  copper, gold, and major commodity futures.
- Calendar constraints such as holidays, policy meetings, earnings clusters,
  expiry dates, and major data releases.

Use cautious language:

- `偏强`: positive catalysts dominate broad market risk appetite.
- `震荡偏强`: positive catalysts dominate but with clear offsetting risks.
- `震荡`: positive and negative catalysts are balanced or narrow.
- `震荡偏弱`: negative catalysts dominate but downside is partly buffered.
- `偏弱`: negative catalysts are broad, high-confidence, and immediate.

## Sector And Affected Company Selection

For each news item, first list affected sectors or themes. Only after a sector
passes the positive or negative ranking gate, list up to five likely affected
A-share companies when evidence supports the exposure. Prefer companies with:

- Direct business exposure to the policy, product, commodity, geography, or
  supply chain.
- High sector representativeness or index weight.
- Recent company disclosures or official business descriptions supporting the
  link.
- Clear direction of impact and a concise causal factor.

If only sector exposure is reliable, state the sector and say company-level
examples need verification.

Do not include a company in `可能受益A股公司` or `可能承压A股公司` only because
it has strong K-line performance. It must first belong to a selected
news-driven sector, then pass stock-level trend, volume, retail VOC, capital
recognition, and risk gates.

## Price And Volume Score

Score `price_volume` from 0 to 5:

- `5`: representative affected names or sector ETFs show a clear trend breakout
  or reversal aligned with the news, with volume materially above the recent
  average.
- `4`: price trend and relative strength align with the news, and volume or
  turnover improves.
- `3`: price action is neutral or mixed, with no strong confirmation or
  contradiction.
- `2`: price action weakly contradicts the news, or volume is fading.
- `1`: price action strongly contradicts the news with heavy opposite volume.
- `0`: no usable market data is available or the candidate cannot be tied to
  tradable A-share names or sector instruments.

## Confidence Labels

Use these labels in the report:

- `高`: primary source or filing confirms the event and the company exposure is
  direct.
- `中`: event is confirmed but company exposure is inferred from business scope,
  sector classification, or representative status.
- `低`: event is confirmed but company exposure is indirect, supply-chain based,
  or requires follow-up verification.
