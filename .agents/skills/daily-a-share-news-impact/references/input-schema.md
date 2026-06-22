# Input Schema

Use this JSON shape when assembling a repeatable report. The bundle keeps live
facts, scoring inputs, and data-quality notes in one place.

```json
{
  "window": {
    "start": "2026-05-29T09:30:00+08:00",
    "end": "2026-06-01T09:30:00+08:00",
    "timezone": "Asia/Shanghai"
  },
  "fund_flow": {
    "direction": "拥挤分化",
    "pbc_open_market_operation_summary": "央行当日7天期逆回购操作金额、利率、到期量和净投放/净回笼",
    "turnover_summary": "两市成交额放大但个股分化",
    "main_flow_summary": "科技方向活跃，非科技方向承接不足",
    "sector_flow_summary": "AI硬件、电池较强；周期和出口链偏弱",
    "breadth_summary": "上涨家数少于下跌家数",
    "data_quality": "partial"
  },
  "candidates": [
    {
      "title": "政策或市场事件标题",
      "direction": "positive",
      "magnitude": 4.5,
      "breadth": 4,
      "immediacy": 4,
      "confidence": 5,
      "novelty": 3.5,
      "liquidity": 4,
      "price_volume": 3.5
    }
  ],
  "sector_candidates": [
    {
      "title": "钠离子电池",
      "direction": "positive",
      "magnitude": 4,
      "breadth": 3.5,
      "immediacy": 4,
      "confidence": 4,
      "novelty": 3.8,
      "liquidity": 3.8,
      "price_volume": 3.5
    }
  ],
  "stocks": [
    {
      "ticker": "300750",
      "name": "宁德时代",
      "sector": "钠离子电池",
      "directional_role": "beneficiary",
      "market_cap_billion": 1050,
      "trend_score": 4,
      "volume_score": 4,
      "retail_sentiment": 4.2,
      "retail_voc_summary": "公开讨论热度较高，但未出现极端追涨",
      "capital_recognition": 4,
      "event_alignment": 4.2,
      "institutional_trend_score": 3.8,
      "risk_score": 3.2,
      "external_data": {
        "source": "public_free_quote",
        "data_time": "2026-06-01T09:30:00+08:00",
        "quote": {
          "latest": 240,
          "change_pct": 1.25,
          "turnover": 8500000000,
          "market_cap": 1050000000000
        },
        "valuation_context": "PE合理偏低",
        "fundamental_context": "免费数据源部分缺口，未补充完整财务质量",
        "holder_context": "未获取",
        "data_quality": "partial"
      }
    }
  ],
  "evidence_gaps": [
    "未获取到完整北向资金数据"
  ],
  "optional_data_sources": {
    "akshare_dependency": {
      "status": "installed",
      "detail": "akshare=1.18.64, pandas=3.0.3, numpy=1.26.4"
    },
    "akshare_fetch": {
      "status": "fetch_failed",
      "detail": "Provider request failed or returned an error.",
      "output_path": "tmp/a_share_optional_probe_300750_basic.json"
    },
    "sina_quote": {
      "status": "available",
      "detail": "Sina public quote endpoint returned quote text."
    },
    "tencent_quote": {
      "status": "available",
      "detail": "Tencent public quote endpoint returned quote text."
    }
  }
}
```

## Data Quality

Use `data_quality` values:

- `full`: direct numeric market data is available for turnover, major fund-flow
  channels, and stock-level 14-day data.
- `partial`: some direct data is available, but one or more channels rely on
  reputable market summaries.
- `limited`: most values are qualitative because market data access is missing
  or unstable.

When quality is `partial` or `limited`, say so in the final report and lower
confidence where appropriate.

## Fund Flow

Use `fund_flow.pbc_open_market_operation_summary` to preserve the report-date
People's Bank of China open market operation check. Include the operation tool,
amount, maturity, rate, maturity amount if available, and net injection or
withdrawal. If the report-date notice is not yet published or the page cannot be
accessed, record that gap explicitly instead of omitting the field.

## Directional Role

Use `directional_role` for stock recommendation gating:

- `beneficiary`: screen the stock for `可能受益A股公司`.
- `pressure`: screen the stock for `可能承压A股公司`.
- `watch`: stock is relevant but should not enter either recommendation column.

## Security Exclusion Gate

Use `market_cap_billion` for the latest available market cap in CNY billions as
display and context only. Missing or out-of-range market cap must not exclude a
stock from opportunity or pressure tables.

Exclude these stocks from `可能受益A股公司` and `可能承压A股公司`:

- STAR Market / 科创板 tickers, inferred from `688` or `689` prefixes.
- Beijing Stock Exchange / 北交所 tickers, inferred from `4`, `8`, or `920`
  prefixes.
- ST, `*ST`, `SST`, `S*ST`, and delisting-risk names.

## Sector Candidates

Use `sector_candidates` to enforce the news-to-sector-to-stock order. Stocks can
enter beneficiary or pressure columns only when their `sector` exactly matches a
selected sector candidate with the corresponding direction. Stocks without
`sector`, or with sectors not selected from news, must be reported as
`未入选推荐列`.

`scripts/assemble_report_data.py` also emits `daily_mainlines` and
`leading_stocks` from `sector_candidates` and `stocks`. `daily_mainlines`
contains the top 5 mainline sectors or concepts by default. It prefers positive
sector candidates with strong impact and price/volume confirmation, then fills
from the strongest remaining sector candidates when fewer than 5 positive
mainlines are available. `leading_stocks` contains up to 10 beneficiary-role
stocks from those mainlines. These rows are a market-readout list, not the
stricter recommendation list. Watch-only leaders still need confirmed trend,
volume, capital recognition, event alignment, institutional trend setup, and
acceptable risk. Do not fill weakly confirmed stocks into the leader table just
to reach 10 rows. Rows that fail the opportunity gate must keep
`eligible_for_recommendation` as `no` with an explicit `exclusion_reason`.

The assembled output fields have this shape:

```json
{
  "daily_mainlines": [
    {
      "rank": 1,
      "title": "钠离子电池",
      "direction": "positive",
      "impact_score": 4.2,
      "magnitude": 4,
      "breadth": 3.5,
      "immediacy": 4,
      "confidence": 4,
      "novelty": 3.8,
      "liquidity": 3.8,
      "price_volume": 3.5
    }
  ],
  "leading_stocks": [
    {
      "ticker": "300750",
      "name": "宁德时代",
      "sector": "钠离子电池",
      "directional_role": "beneficiary",
      "market_cap_billion": 1050,
      "research_score": 3.8,
      "research_rating": "关注",
      "operation_tendency": "趋势跟踪观察",
      "eligible_for_recommendation": "yes",
      "exclusion_reason": "",
      "leader_role": "eligible_leader",
      "trend_score": 4,
      "volume_score": 4,
      "retail_sentiment": 4.2,
      "retail_voc_quality_score": 2.56,
      "capital_recognition": 4,
      "event_alignment": 4.2,
      "institutional_trend_score": 3.8,
      "risk_score": 3.2
    }
  ]
}
```

## Retail VOC Summary

`retail_voc_summary` is optional but recommended. Use it to record the source
and interpretation of retail VOC proxies, such as stock-forum heat, comment
tone, question frequency, watchlist popularity, or panic/chasing language. Do
not include personal data.

`retail_sentiment` is a crowding-intensity score. A high value means retail
views are one-sided or emotionally crowded, not that the stock is attractive.
`scripts/score_stocks.py` derives `retail_voc_quality_score` from this field and
penalizes extreme retail chasing or panic unless main capital and volume confirm
the same direction.

## External Data

`stocks[].external_data` is optional. Use it to store supporting data acquired
from installed stock-analysis skills:

- `china-stock-analysis`: akshare basic information, financial statements,
  indicators, valuation history, historical daily bars, shareholder data, and
  dividends.
- `public_quote_api`: Sina, Tencent, or Eastmoney no-key spot quote data.
- `itick`: iTick quote or K-line data when `ITICK_API_TOKEN` is configured.
- `zhitu`: Zhitu quote, technical indicator, or fund-flow-style data when
  `ZHITU_API_TOKEN` is configured. Demo-token responses are connectivity checks
  only.
- `baostock`: optional daily bars when the dependency is available.
- `itick` or `zhitu`: optional quote, K-line, indicator, or fund-flow-style data
  when free API tokens are configured.
- Do not add paid-source payloads for routine daily reports.

External data may explain or lower confidence, but it must not bypass the
sector-first gate, 14-trading-day price/volume gate, retail VOC gate, capital
recognition gate, event-alignment gate, or risk gate.

## Institutional Trend Score

Use `institutional_trend_score` for beneficiary candidates only. It measures
whether the stock fits an institution-led trend continuation setup: controlled
positive K-line structure, MA5/MA10/MA20/MA50 alignment, small-candle grind-up
behavior, healthy pullback volume, and no persistent volume starvation.
`scripts/score_stocks.py` keeps this field in `research_score` and
`beneficiary_quality_score`, so it can affect ranking and report annotations,
but it does not by itself exclude a stock from `可能受益A股公司`. Missing values
default to `0` and should be reported as weak institutional-trend confirmation.

## Optional Data Sources

Use `optional_data_sources` to store the output of
`scripts/check_optional_data_sources.py`. This prevents ambiguous report
language:

- `missing_credentials`: a free optional API token is absent.
- `missing_dependency`: akshare or another package is absent.
- `fetch_failed`: the dependency exists but the external data provider failed.
- `available`: the source is ready and may be used.
- `demo_only`: the endpoint responded with a demo token but must not support
  stock-specific conclusions.
- `not_checked`: the probe was skipped because no code or no applicable runtime
  context was supplied.

If a source is `fetch_failed`, preserve the output file path when available so
post-run review can inspect the provider error without rerunning the probe.
