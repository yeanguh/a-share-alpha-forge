---
name: daily-a-share-news-impact
description: Create a daily low-frequency A-share investment-news impact brief for the prior trading-day 09:30 to current trading-day 09:30 China-time window, using Friday 09:30 to Monday 09:30 for Monday runs. Use free available data sources by default, screen sectors first, map sector-qualified stocks, always list the daily top 5 mainline sectors or concepts and up to 10 quality-gated leading stocks, rank top 10 positive and top 10 negative catalysts, screen A-share stocks after 14-trading-day K-line, volume, retail sentiment, capital recognition, and risk scoring, exclude STAR Market, Beijing Stock Exchange, ST, and delisting-risk stocks from opportunity and pressure columns, incorporate whole-market fund-flow direction, persist daily reports by date, and support daily or weekly post-close reviews.
---

# Daily A-Share News Impact

## Overview

Create a source-grounded, auditable A-share market impact brief for low-frequency
daily research. Keep the skill single-purpose: daily investment news collection,
sector-first screening, positive and negative Top 10 filtering,
sector-qualified affected-company mapping, daily top 5 mainline sector or
concept selection, up to 10 quality-gated leading-stock selections from those
mainlines, recent K-line and volume confirmation, whole-market fund-flow
direction, stock-level risk/opportunity scoring, persistence, post-close review,
and short-term direction judgment.
Default to free available data sources; do not use paid interfaces unless the
user explicitly asks for them.

## Required Workflow

1. Establish the reporting window in `Asia/Shanghai` time. Use
   `scripts/rank_news.py window` when exact dates are useful. The standard
   window is prior trading-day 09:30 to current trading-day 09:30; Monday uses
   the prior Friday 09:30 to Monday 09:30.
2. Before broad news collection, check the People's Bank of China open market
   operations page for the report-date operation notice:
   `https://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/index.html`.
   Record reverse repo/MLF/OMO operation amount, maturity, rate, net injection
   or withdrawal, and whether the current report-date notice is unavailable
   before the cutoff time. Use this as liquidity context in `资金方向/热度`; only
   promote it into the positive/negative event ranking when the operation is
   materially market-moving versus recent expectations.
3. Search current sources for market-moving news published, announced, or first
   confirmed inside the window. Always verify with fresh sources because this
   task is time-sensitive. Include the required authority checks from
   `references/information-sources.md`, especially Cailian Press（财联社）,
   Caixin（财新）, and Reuters（路透社） for policy, macro, cross-border,
   commodity, geopolitical, and major industry-supply-chain events.
4. Build a candidate set from the expanded source map in
   `references/information-sources.md`. Deduplicate repeated coverage into one
   event and keep the strongest original source plus confirming sources.
5. Apply the hard filters and score dimensions in
   `references/impact-rubric.md`. Reject weakly sourced, stale, routine, or
   low-breadth items.
6. Split mixed events into separate positive and negative legs when both sides
   are material. Do not hide negative catalysts inside a mixed label.
7. Map retained news to sector/theme candidates first. Rank positive and
   negative `sector_candidates` before generating stock candidates. Follow
   `references/sector-first-screening.md`.
8. Generate affected-company candidates only from ranked sectors when the
   transmission path is explainable. Exclude STAR Market（科创板）, Beijing Stock
   Exchange（北交所）, ST, `*ST`, and delisting-risk stocks from opportunity and
   pressure columns. Market cap is a display/context field only and must not be
   used as a hard eligibility gate. For beneficiary opportunities, require the
   source sector to pass the strong-mainline gate in
   `references/fund-flow-and-stock-scoring.md`; weaker positive sectors are
   observation-only even when individual stock scores look acceptable. Do not
   place any stock in the
   `可能受益A股公司` or `可能承压A股公司` report columns yet.
9. Check recent K-line and volume behavior for representative affected
   companies or sector ETFs using `references/market-data-checklist.md`. Feed
   the result into the `price_volume` score.
10. Determine whole-market fund-flow direction using
   `references/fund-flow-and-stock-scoring.md`: broad-index fund flow, main
   capital net flow, sector flow, northbound/foreign flow when available,
   margin financing, ETF flow, PBOC open market operation context, turnover
   concentration, and up/down breadth.
11. For each affected stock that appears in the report, collect public or
   authorized retail VOC proxies using `references/retail-voc.md`. Treat
   extreme retail enthusiasm as a crowding/contrarian risk unless main capital
   recognition and 14-day volume confirm it. Treat retail panic as a possible
   contrarian opportunity only when main capital stabilizes. When VOC and main
   capital conflict, follow main capital and 14-day price/volume confirmation
   first.
12. For each affected stock that appears in the report, analyze the latest 14
   trading days of K-line and volume. Score retail sentiment, capital
   recognition, trend, volume, institutional trend setup, event alignment, and
   risk. Use
   `scripts/score_stocks.py` when structured stock observations are available;
   rank opportunity rows by `beneficiary_quality_score` after they pass the
   gate so stronger 14-day trend, volume, main-capital recognition,
   institution-led slow-grind setup, event alignment, and risk control appear
   first. Treat the institutional trend setup as an internal confirmation
   factor and report annotation only, not as a strict eligibility gate or
   standalone trading method.
   Only stocks that pass the eligibility gate in
   `references/fund-flow-and-stock-scoring.md` may appear in the
   `可能受益A股公司` or `可能承压A股公司` columns. Stocks must also pass the
   sector-first gate.
13. Enrich selected stocks only with free available data sources using
    `references/optional-stock-analysis-skills.md`. Treat valuation and
    fundamental outputs as supporting context only; they must not bypass the
    sector-first, board/ST exclusion, price/volume, retail VOC,
    capital-recognition, or risk gates. Prefer akshare, Sina, Tencent, Eastmoney,
    Baostock, or free-token providers when available. Run
    `scripts/check_optional_data_sources.py` before reporting optional-source
    gaps so the report distinguishes missing dependencies, provider fetch
    failures, demo-only endpoints, and available no-key public quote fallbacks.
    When `market_cap_billion` is missing, run
    `scripts/enrich_stock_observations.py` to fill Tencent no-key quote
    snapshots and total market cap before report assembly.
14. Assemble sector candidates, news candidates, fund-flow observations, and
   stock observations into
   the bundle shape in `references/input-schema.md`. Run
   `scripts/assemble_report_data.py --input bundle.json` to produce ranked
   sector data, the daily top 5 mainline sectors or concepts, up to 10
   quality-gated leading stocks from those mainlines, ranked candidate data,
   scored stock data, and warnings about missing evidence. Production threshold
   defaults live in `config/default_thresholds.json`; pass `--threshold-config`
   only when testing an explicit alternative profile. Do not fill weakly
   confirmed stocks into the leader table just to reach 10 rows.
15. Rank positive and negative candidates separately. Keep top 10 positive and
   top 10 negative items. Use
   `scripts/rank_news.py rank --input candidates.json --by-direction` when
   candidates have been structured as JSON.
16. Write the final report in Chinese by default using
    `references/report-template.md`. Use research ratings and operation
    tendencies only; use the fixed module structure in the report template:
    `大盘整体情绪`, `资金方向/热度`, `每日主线板块/概念与龙头个股`,
    `正向负向事件Top`, `个股机会的筛选结果`, and `短期市场判断`. Avoid direct
    buy, sell, hold, add, reduce, price-target, stop-loss, or position-size
    instructions.
    Stocks that fail eligibility must be listed under excluded/observation notes,
    not in the recommended beneficiary or pressure company columns. Use
    `scripts/render_report.py --assembled assembled.json` when the structured
    assembled output is available and a deterministic Markdown skeleton is
    preferred.
17. Persist every daily run using `references/persistence-and-review.md` and
    `scripts/persist_report.py`. Save the input bundle, assembled scoring data,
    and final Markdown report under `local/YYYY-MM-DD/`. Do not create an
    extra skill-name directory below `local/`. When starting from an existing
    `input_bundle.json`, use `scripts/run_daily_report.py --bundle ...` to run
    assemble, render, and persist in one repeatable command.
18. After 15:00 China time, use closing broad-index, sector, and selected-stock
    data to create `close_review.json`. Use `scripts/review_archive.py` for
    daily or weekly review aggregation. Store weekly, intraday, backtest,
    threshold-scan, and calibration summary outputs under
    `local/reviews/`, not in the daily archive root.
    Adjust future strategy notes only from repeated review evidence, not
    one-day noise.
    Current post-review calibration: require stricter evidence before placing a
    strong mainline stock into the pressure list. Crowded positioning, high
    retail heat, or valuation risk alone should usually become a leader-table
    risk note unless 14-day trend and capital recognition have both weakened.
    The latest candidate-pool calibration also requires beneficiary stocks to
    show main-capital recognition at or above the stricter gate before entering
    the opportunity column; moderate news fit plus ordinary trend is not enough.
    Use `scripts/backtest_archived_reports.py` to run a repeatable realtime or
    post-close backtest over archived reports before changing thresholds. Treat
    beneficiary hit rate, leader positive rate, pressure hit rate, and worst
    misses as the minimum evidence set for calibration. For short-term strategy
    calibration, prefer fixed horizons with `--horizon-trading-days 1` and
    `--horizon-trading-days 3` so the evidence matches the report's
    one-to-three-session framing. Add `--min-hit-return-pct 0.5` when judging
    whether selected rows cleared a minimal effective-profit threshold rather
    than merely moving by market noise. For opportunity-column optimization,
    prioritize beneficiary hit rate, beneficiary raw average return, and
    beneficiary worst return. Use directional return only when deliberately
    mixing beneficiary rows with pressure risk-readout rows. Use
    `scan_selection_thresholds.py --role-scope beneficiary` for opportunity-pool
    calibration so pressure risk-readout rows do not steer the
    `可能受益A股公司` thresholds. Treat pooled scan improvements as provisional
    unless `report_count`, `by_report`, and worst report-date return show
    cross-date stability. Do not change production thresholds unless a scanned
    profile both passes the scanner's promotion gate and beats the current
    production baseline in `top_deployable_profiles`.
19. When the user asks to test or run the skill, still return the report in the
    document format from `references/report-template.md`. Include script output
    only as a brief verification note after the formatted report.

## Source Priority

- Prefer primary sources for policy, regulation, exchange notices, company
  filings, macro data, and official speeches.
- Use reputable financial media for market interpretation, cross-source
  confirmation, and facts not available in primary-source form.
- Treat Cailian Press（财联社）, Caixin（财新）, and Reuters（路透社） as
  required authority checks for daily scheduled reports when available; record
  access gaps explicitly instead of substituting unsupported commentary.
- Use the broader source checklist in `references/information-sources.md` before
  ranking. Cover at least official, exchange/filing, financial-media,
  cross-market, commodity/FX/rates, and sector-specific channels when relevant.
- Use market-data tools for current prices, K-line, volume, turnover, futures,
  FX, index moves, and cross-market leads when available.
- Use only free available data sources for routine daily runs. Exclude QVeris,
  paid Tushare Pro tiers, paid terminal feeds, and other paid interfaces unless
  the user explicitly enables paid sources for a special run.
- Use fund-flow data from market data vendors, exchange summaries, financial
  terminals, or reputable financial media. Prefer direct data over commentary.
- Cite every retained news item and every non-obvious company mapping.
- Record skill-design sources in `sources.md`; do not cite `sources.md` as
  evidence for live market facts.

## Candidate Scope

- Include policy, macro, rates, FX, commodities, geopolitics, global markets,
  industry regulation, earnings guidance, M&A, sanctions or export controls,
  supply-chain shocks, and major technology or demand shifts.
- Exclude single-stock rumors, unsourced social-media claims, pure technical
  analysis, routine analyst opinions, and news outside the window unless it
  materially changed inside the window.
- Treat `positive` and `negative` as directional impact on affected A-share
  equities or sectors. Split `mixed` items into two scored directional entries
  when they can affect both winners and losers.
- Exclude STAR Market（科创板）, Beijing Stock Exchange（北交所）, ST, `*ST`, and
  delisting-risk stocks from opportunity or pressure tables. Market cap can be
  displayed as context but is not a hard eligibility gate.
- State uncertainty explicitly when company exposure is indirect or estimated.

## Resources

- `references/impact-rubric.md`: scoring dimensions, filters, and ranking rules.
- `references/information-sources.md`: expanded source map for news collection.
- `references/sector-first-screening.md`: news-to-sector-to-stock gating rules.
- `references/fund-flow-and-stock-scoring.md`: whole-market fund-flow direction,
  retail sentiment, capital recognition, risk/opportunity, and rating rules.
- `references/input-schema.md`: structured input bundle for repeatable report
  assembly and quality checks.
- `references/market-data-checklist.md`: K-line and volume confirmation rules.
- `references/optional-stock-analysis-skills.md`: optional bridge to installed
  stock price, public quote, and fundamental analysis sources.
- `references/persistence-and-review.md`: dated archive layout, dedicated
  `reviews/` directory, and post-close daily/weekly review loop.
- `references/report-template.md`: Chinese output structure and table columns.
- `references/retail-voc.md`: public or authorized retail VOC collection,
  scoring, and contrarian interpretation rules.
- `config/default_thresholds.json`: production threshold defaults for market-cap
  range, sector gates, stock gates, score weights, and default Top-N limits.
- `scripts/assemble_report_data.py`: helper that validates the report input
  bundle, ranks sectors and candidates, scores stocks, applies sector-first
  gating, reads threshold config, and emits evidence-gap warnings.
- `scripts/backtest_archived_reports.py`: helper that reads persisted
  `assembled.json` files and compares selected beneficiaries, pressure
  candidates, and optional mainline leaders with free realtime Tencent quote and
  K-line data.
- `scripts/check_optional_data_sources.py`: helper that checks free-source
  health by default: akshare installation/fetch health, Sina/Tencent/Eastmoney
  public quote endpoints, iTick/Zhitu token availability, and Baostock
  readiness. Paid or quasi-paid sources are probed only with `--include-paid`.
- `scripts/enrich_stock_observations.py`: helper that enriches report bundles
  with Tencent no-key quote snapshots and total market cap when akshare or
  Eastmoney is unavailable.
- `scripts/persist_report.py`: helper that persists daily inputs, assembled
  output, reports, and post-close review files by date.
- `scripts/rank_news.py`: deterministic helper for China-time windows and
  structured candidate ranking.
- `scripts/render_report.py`: deterministic helper that renders assembled
  scoring JSON into the fixed Chinese Markdown report structure.
- `scripts/review_archive.py`: helper that aggregates persisted post-close
  daily or weekly review records.
- `scripts/run_daily_report.py`: one-command helper for existing input bundles;
  assembles scoring data, renders Markdown, and persists the run.
- `scripts/score_stocks.py`: deterministic helper for stock-level research
  scoring, threshold-configured gates, and non-personalized operation tendencies.
- `sources.md`: audit trail for the skill-design references.

## Candidate JSON

Use this shape when ranking candidates with the script:

```json
[
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
]
```

## Sector Candidate JSON

Use the same shape for `sector_candidates`; set `title` to the sector or theme
name, such as `AI硬件`, `创新药`, or `国资改革`.

## Stock Observation JSON

Use `directional_role` to indicate whether the stock is being screened for a
beneficiary or pressure-company column:

```json
[
  {
    "ticker": "300750",
    "name": "宁德时代",
    "sector": "钠离子电池",
    "directional_role": "beneficiary",
    "market_cap_billion": 1050,
    "trend_score": 4,
    "volume_score": 4,
    "retail_sentiment": 4.2,
    "capital_recognition": 4,
    "retail_voc_summary": "股吧/评论热度高，追涨情绪升温",
    "event_alignment": 4.2,
    "institutional_trend_score": 3.8,
    "risk_score": 3.2
  }
]
```

## Script Examples

```bash
python3 .agents/skills/daily-a-share-news-impact/scripts/rank_news.py window
  # Optional: --trading-calendar tmp/a-share-trading-calendar.json

python3 .agents/skills/daily-a-share-news-impact/scripts/rank_news.py rank \
  --input tmp/a-share-news-candidates.json \
  --by-direction \
  --top-positive 10 \
  --top-negative 10

python3 .agents/skills/daily-a-share-news-impact/scripts/score_stocks.py \
  --input tmp/a-share-stock-observations.json

python3 .agents/skills/daily-a-share-news-impact/scripts/assemble_report_data.py \
  --input tmp/a-share-brief-bundle.json \
  --output tmp/a-share-brief-assembled.json

python3 .agents/skills/daily-a-share-news-impact/scripts/render_report.py \
  --assembled tmp/a-share-brief-assembled.json \
  --output tmp/a-share-brief-report.md

python3 .agents/skills/daily-a-share-news-impact/scripts/run_daily_report.py \
  --bundle tmp/a-share-brief-bundle.json \
  --run-id 093000

python3 .agents/skills/daily-a-share-news-impact/scripts/check_optional_data_sources.py \
  --akshare-code 300750 \
  --akshare-data-type basic \
  --quote-code 300750
  # Optional: --data-fetcher /path/to/data_fetcher.py or ASHARE_DATA_FETCHER=/path/to/data_fetcher.py

python3 .agents/skills/daily-a-share-news-impact/scripts/enrich_stock_observations.py \
  --input tmp/a-share-brief-bundle.json \
  --output tmp/a-share-brief-bundle-enriched.json

python3 .agents/skills/daily-a-share-news-impact/scripts/persist_report.py \
  --bundle tmp/a-share-brief-bundle.json \
  --assembled tmp/a-share-brief-assembled.json \
  --report tmp/a-share-brief-report.md \
  --run-id 093000

python3 .agents/skills/daily-a-share-news-impact/scripts/review_archive.py \
  --frequency weekly \
  --output local/reviews/weekly/weekly_review_YYYY-MM-DD_YYYY-MM-DD.json
```
