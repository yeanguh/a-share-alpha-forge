# Free Data Source Integration

Routine daily reports must use free available sources only. Paid interfaces are
excluded unless the user explicitly requests a paid-source run.

Before each full run, check optional-source health:

```bash
python3 .agents/skills/daily-a-share-news-impact/scripts/check_optional_data_sources.py \
  --akshare-code 300750 \
  --akshare-data-type basic \
  --quote-code 300750
```

Use the result labels consistently:

| Status | Meaning | Report wording |
| --- | --- | --- |
| `available` | Credential/dependency and probe worked. | Use the data and cite freshness. |
| `missing_credentials` | Required free API token is absent. | `免费API凭证缺失，已降级到无密钥公开行情源`. |
| `missing_dependency` | Required Python package is absent. | `免费数据依赖缺失`. |
| `fetch_failed` | Dependency exists but provider/network/API failed. | `数据源已配置但抓数失败`. |
| `demo_only` | Demo endpoint responded but is not safe for stock-specific analysis. | `示例接口可访问，但未配置正式凭证，未用于个股结论`. |
| `not_checked` | Probe was intentionally skipped. | State why it was skipped. |

## Fallback Priority

Use the following data-source order for daily runs:

| Priority | Source | Use | Degrade when |
| --- | --- | --- | --- |
| 1 | `china-stock-analysis` / akshare | A-share basic, valuation, and historical bars. | Dependency missing or provider/API failure. |
| 2 | Sina public quote API | No-key spot quote cross-check. | Endpoint fails or returned text cannot be parsed. |
| 3 | Tencent public quote API | No-key spot quote, total market cap, and float market cap fallback. | Endpoint fails or returned text cannot be parsed. |
| 4 | Eastmoney public quote API | No-key JSON quote cross-check. | Endpoint rejects or closes the request. |
| 5 | Baostock | No-key historical daily K-line fallback if installed. | Dependency missing or login/query failure. |
| 6 | iTick REST API | Real-time quote and K-line when a free `ITICK_API_TOKEN` is set. | Token missing, quota exhausted, or provider failure. |
| 7 | Zhitu API | Real-time quote, technical indicators, and fund-flow style fields when a free `ZHITU_API_TOKEN` is configured. | Only demo token is available, token missing, or provider failure. |

Do not use Yahoo Finance, Alpha Vantage, Tiingo, Polygon, or Google Finance as
primary A-share sources. The referenced articles discuss them as general
quantitative data sources, but they are better suited to US/global assets or
require separate API keys. They may only support cross-market context.

When `market_cap_billion` is missing and akshare or Eastmoney fetches fail, run
`scripts/enrich_stock_observations.py` before assembly. It uses Tencent's
no-key quote endpoint to fill `market_cap_billion` from total market cap and
stores the parsed quote snapshot under
`stocks[].external_data.quote_snapshot`.

## Paid Sources

Do not use `china-stock-price-analysis` / QVeris, paid Tushare Pro tiers,
terminal feeds, or similar paid interfaces for routine reports. If the user
explicitly asks for a paid-source run, use
`scripts/check_optional_data_sources.py --include-paid` and disclose that the
run is no longer free-only.

## `china-stock-analysis`

Path:

```text
/Users/bytedance/.agents/skills/china-stock-analysis
```

Use when the brief needs slower fundamental context for selected stocks,
especially during post-close review or weekly review.

Capabilities:

- Stock screening by valuation, ROE, growth, leverage, dividend, and scope.
- Public financial data fetch through `akshare`.
- Financial health and anomaly checks.
- DCF/DDM/relative valuation calculators.
- Industry comparison and structured Markdown report template.

Runtime requirements:

```bash
pip install akshare pandas numpy
```

Data acquisition commands:

```bash
python /Users/bytedance/.agents/skills/china-stock-analysis/scripts/data_fetcher.py \
  --code "600519" \
  --data-type all \
  --no-cache \
  --years 5 \
  --output /tmp/stock_data_600519.json

python /Users/bytedance/.agents/skills/china-stock-analysis/scripts/data_fetcher.py \
  --codes "600519,000858,002304" \
  --data-type basic \
  --output /tmp/stock_compare_basic.json

python /Users/bytedance/.agents/skills/china-stock-analysis/scripts/data_fetcher.py \
  --scope hs300 \
  --output /tmp/hs300_constituents.json
```

Supported `data_type` values:

| `data_type` | Backing data calls | Use in this daily skill |
| --- | --- | --- |
| `basic` | `ak.stock_individual_info_em` | Name, industry, market cap, float cap, PE, PB, listing date. |
| `financial` | `ak.stock_balance_sheet_by_report_em`, `ak.stock_profit_sheet_by_report_em`, `ak.stock_cash_flow_sheet_by_report_em`, `ak.stock_financial_abstract`, `ak.stock_financial_analysis_indicator` | Financial quality, profitability, growth, leverage, and cash-flow risk. |
| `valuation` | `ak.stock_a_ttm_lyr`, `ak.stock_zh_a_hist` | PE/PB percentile, latest price, turnover, 60-day range, 20-day average volume, latest 30 daily bars. |
| `holder` | `ak.stock_gdfx_top_10_em`, `ak.stock_zh_a_gdhs`, `ak.stock_dividend_cninfo`, `ak.stock_history_dividend_detail` | Holder concentration, shareholder count trend, dividend support, and governance risk. |
| `all` | All of the above | Post-close and weekly review enrichment. |

Scope acquisition:

| Scope | Use |
| --- | --- |
| `hs300` | Large-cap benchmark constituents. |
| `zz500` | Mid-cap benchmark constituents. |
| `zz1000` | Small/mid-cap breadth reference when available in script mapping. |
| `cyb` | ChiNext growth-stock universe. |
| `kcb` | STAR-market technology universe. |
| `all` | Full A-share code list through `ak.stock_zh_a_spot_em`. |

Suggested use:

- Daily 09:30 report: optional only for high-confidence selected stocks because
  the data can be slower and more fundamental than the news window.
- Post-close 15:00 review: use for financial risk and valuation context on
  stocks that repeatedly enter candidate lists.
- Weekly review: use for strategy calibration, such as whether high-scoring
  stocks also have acceptable ROE, leverage, cash-flow quality, and valuation.

Do not use value-investing conclusions as direct trading instructions in the
daily brief. Convert them into non-personalized research context, such as
`估值偏贵`, `财务质量需复核`, `现金流质量支持`, or `基本面风险待排查`.

Integration rules:

- Use `--no-cache` when running from this repository unless the external skill
  directory is writable. The installed script otherwise tries to write
  `.cache` under `/Users/bytedance/.agents/skills/china-stock-analysis/scripts`.
- Use `valuation.price.price_data` as a fallback 30-day daily K-line source
  when direct 14-trading-day market data APIs are unavailable. Derive the latest
  14 trading days from the tail of this array.
- Use `valuation.price.avg_volume_20d`, latest `volume`, and `turnover` as
  volume confirmation references.
- Use `basic_info.industry` to cross-check the daily skill's sector mapping.
  If the sector is inconsistent, lower `event_alignment` or add an evidence gap.
- Use `financial_indicators`, three statements, and cash-flow data to populate
  `fundamental_context` and post-close review, not to override intraday
  news/price-volume gates.
- Use `holder` and `dividend` data as risk context, especially for repeated
  weekly candidates.
- If `akshare` is missing, record `missing_dependency` in `evidence_gaps`; do
  not stop the daily report.
- If `akshare` is installed but a provider call fails, record `fetch_failed`
  with the failing provider summary. Do not report it as an installation issue.

## Daily Skill Field Mapping

When optional data is available, add it to the report bundle under
`stocks[].external_data`:

```json
{
  "source": "china-stock-analysis",
  "data_time": "2026-06-01T15:30:00+08:00",
  "quote": {
    "latest": 240,
    "change_pct": 1.25,
    "turnover": 8500000000,
    "market_cap": 1050000000000
  },
  "valuation_context": "PE合理偏低，PB高于普通制造但符合新能源龙头溢价",
  "fundamental_context": "现金流质量待复核，ROE处于行业较高水平",
  "holder_context": "股东户数变化待复核",
  "data_quality": "partial"
}
```

Use `external_data` only for explanation, confidence adjustment, and post-close
review calibration. The stock must still pass the daily skill's sector,
price-volume, retail VOC, capital-recognition, event-alignment, and risk gates.
