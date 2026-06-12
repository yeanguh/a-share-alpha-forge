# Persistence And Review

Persist every daily run so later reviews can compare predicted direction,
selected sectors, selected stocks, and post-close outcomes.

## Archive Layout

Default root:

```text
local/
  YYYY-MM-DD/
    input_bundle.json
    assembled.json
    report.md
    close_review.json
    metadata.json
    runs/
      HHMMSSffffff/
        input_bundle.json
        assembled.json
        report.md
        close_review.json
  reviews/
    weekly/
      weekly_review_YYYY-MM-DD_YYYY-MM-DD.{json,md}
    intraday/
      intraday_review_YYYY-MM-DD_HHMM.{json,md}
    backtests/
      backtest_*.json
    threshold_scans/
      threshold_scan_*.json
    summaries/
      *_summary_YYYY-MM-DD_YYYY-MM-DD.md
```

`YYYY-MM-DD` is the report date from `window.end`. The date-level files are the
latest copy for quick reading. Every execution is also stored under `runs/` so
same-day reruns do not overwrite the audit trail. Pass `--run-id` when a stable
run identifier is needed.

Use `local/` because it stores reproducible report and review data that should
remain visible to git. Keep date directories for daily report artifacts only.
Store multi-day review, intraday review, backtest, threshold-scan, and
calibration summary outputs under `reviews/`; do not place periodic review
files in the daily archive root.

## Daily Run Persistence

After `scripts/assemble_report_data.py` and after writing the Markdown report,
persist the artifacts:

```bash
python3 .agents/skills/daily-a-share-news-impact/scripts/persist_report.py \
  --bundle tmp/a-share-brief-bundle.json \
  --assembled tmp/a-share-brief-assembled.json \
  --report tmp/a-share-brief-report.md \
  --run-id 093000
```

When an `input_bundle.json` already exists, the repeatable one-command path is:

```bash
python3 .agents/skills/daily-a-share-news-impact/scripts/run_daily_report.py \
  --bundle tmp/a-share-brief-bundle.json \
  --run-id 093000
```

The helper writes working files under `tmp/daily-a-share-news-impact/<run-id>/`
by default, renders the fixed Markdown report with `render_report.py`, and then
persists the input bundle, assembled JSON, report, and metadata under
`local/YYYY-MM-DD/`.

## Post-Close Review

After 15:00 China time, collect closing data for broad indices, selected sectors,
and selected stocks. Save `close_review.json` into that day's archive, then rerun
`persist_report.py --close-review ...`.

Use this shape:

```json
{
  "review_time": "2026-06-01T15:30:00+08:00",
  "direction_hit": false,
  "average_stock_error": 1.2,
  "sector_hits": [
    {"sector": "AI硬件", "hit": true, "reason": "收盘相对强于全A"}
  ],
  "stock_hits": [
    {"ticker": "300308", "hit": true, "actual_move": "放量上涨"}
  ],
  "lesson": "散户VOC过热但主力确认的AI硬件仍可保留；未放量政策主题应降权。"
}
```

## Weekly Review

Aggregate stored daily reviews:

```bash
python3 .agents/skills/daily-a-share-news-impact/scripts/review_archive.py \
  --frequency weekly \
  --start 2026-06-01 \
  --end 2026-06-05 \
  --output local/reviews/weekly/weekly_review_2026-06-01_2026-06-05.json
```

Use review results to adjust future scoring only when the same pattern repeats
across multiple days. Do not overfit one-day noise. Prefer durable adjustments
such as sector liquidity weights, crowding penalties, price-volume confirmation,
and event-confidence thresholds.

## Realtime Or Post-Close Backtest

Before changing stock-selection thresholds, run the archived-report backtest so
the calibration is grounded in actual selected rows rather than anecdotal
examples:

```bash
python3 .agents/skills/daily-a-share-news-impact/scripts/backtest_archived_reports.py \
  --start 2026-06-01 \
  --end 2026-06-05 \
  --include-leaders \
  --output local/reviews/backtests/backtest_2026-06-01_2026-06-05.json
```

The helper reads each persisted `assembled.json`, fetches free Tencent quote and
K-line data, and reports:

- overall hit rate and average return
- average gain, average loss, payoff ratio, best return, and worst return
- hit rates by role: beneficiary, pressure, and leader
- hit rates by report date
- best hits and worst misses

Use it after market close for more stable results. Intraday runs are useful for
debugging but should not drive permanent threshold changes unless the same
pattern is confirmed across multiple days.

For short-term calibration, prefer a fixed horizon that matches the report's
one-to-three-session framing:

```bash
python3 .agents/skills/daily-a-share-news-impact/scripts/backtest_archived_reports.py \
  --start 2026-06-01 \
  --end 2026-06-05 \
  --horizon-trading-days 1 \
  --min-hit-return-pct 0.5 \
  --output local/reviews/backtests/backtest_horizon1_min_hit_0p5_2026-06-01_2026-06-05.json
```

`--horizon-trading-days 1` evaluates from the report-date open to the same-day
close. `--horizon-trading-days 3` evaluates to the third trading-day close and
marks newer rows as `insufficient_horizon` until enough K-line data exists. Use
horizon `1` for immediate money response and horizon `3` for theme persistence.
`--min-hit-return-pct 0.5` requires a beneficiary row to return at least
`+0.5%`, and a pressure row to return at most `-0.5%`, before counting as an
effective hit. Use this effective-profit threshold when judging whether the
opportunity column is likely to produce tradable returns rather than noise. The
default without a horizon remains latest-quote evaluation; the default without
`--min-hit-return-pct` remains a raw directional hit.

Backtest output includes both raw and directional return metrics:

- `average_return_pct`: raw stock return from report-date open to the evaluated
  exit price.
- `average_directional_return_pct`: beneficiary raw return; pressure return
  multiplied by `-1`, so correct pressure calls contribute positive directional
  return.

Use beneficiary `average_return_pct` and beneficiary effective hit rate as the
primary opportunity-column evidence. Use overall
`average_directional_return_pct` only when intentionally mixing beneficiary and
pressure rows in a strategy-quality readout.

For threshold calibration, evaluate the full archived input candidate pool
rather than only the stocks selected by an older rule set:

```bash
python3 .agents/skills/daily-a-share-news-impact/scripts/backtest_archived_reports.py \
  --start 2026-06-01 \
  --end 2026-06-05 \
  --include-candidates \
  --horizon-trading-days 1 \
  --min-hit-return-pct 0.5 \
  --output local/reviews/backtests/backtest_candidate_pool_horizon1_min_hit_0p5_2026-06-01_2026-06-05.json
```

`--include-candidates` reads every beneficiary or pressure stock observation
from each `input_bundle.json`. Use that output with the threshold scanner to
estimate what a stricter gate would have selected historically.

When calibrating the opportunity pool, scan beneficiary rows only:

```bash
python3 .agents/skills/daily-a-share-news-impact/scripts/scan_selection_thresholds.py \
  --backtest local/reviews/backtests/backtest_candidate_pool_horizon1_min_hit_0p5_2026-06-01_2026-06-05.json \
  --role-scope beneficiary \
  --output local/reviews/threshold_scans/threshold_scan_beneficiary_horizon1_min_hit_0p5_2026-06-01_2026-06-05.json
```

Use `--role-scope all` only for mixed strategy-quality readouts. The
`可能受益A股公司` opportunity thresholds should not be loosened or tightened
because pressure risk-readout rows happened to improve a mixed score.

Scanner output includes `report_count`, `by_report`, and
`worst_report_directional_return_pct`. Treat a profile with strong pooled
metrics but weak report-date coverage as provisional. Do not relax production
opportunity thresholds unless the improvement persists across multiple report
dates or weekly reviews.

Scanner output also includes a promotion gate:

- `promotion_gate`: the minimum evidence requirements for considering a scanned
  profile promotable.
- `passes_promotion_gate`: whether a profile cleared those requirements.
- `promotion_failure_reasons`: why a profile is not promotable.
- `top_promotable_profiles`: highest-scoring profiles that passed the gate.
- `production_baseline_evaluation`: the active production gate evaluated on the
  same filtered sample set.
- `beats_production_baseline`: whether the scanned profile improves on the
  active production gate for report coverage, hit rate, average directional
  return, and worst directional return.
- `production_comparison_failure_reasons`: why a scanned profile failed to beat
  the production baseline.
- `top_deployable_profiles`: highest-scoring profiles that both passed the
  promotion gate and beat the production baseline.
- `production_error_diagnostics`: selected misses, missed winners, and avoided
  losers under the current production gate, with profile-failure reasons for
  each sample.
- `failure_reason_summary`: within `production_error_diagnostics`, aggregated
  hit rate and return statistics by gate-failure reason, plus a conservative
  `gate_action` label.

For the opportunity pool, require at least one `top_deployable_profiles` entry
before changing production thresholds. A merely promotable profile is not enough
if it fails `beats_production_baseline`. If the best pooled profile fails only
because of `report_count_below_gate`, or if it passes the promotion gate but has
`production_comparison_failure_reasons`, keep the current production gate and
wait for more reviewed report dates. Before loosening a gate, inspect
`production_error_diagnostics`: missed winners should have stronger evidence
quality than the avoided losers, not merely a one-day positive return. Use
`failure_reason_summary` to identify whether a specific gate is protective or
overly restrictive. A gate should not be loosened when the samples it excludes
have negative average return or when avoided losers materially outnumber missed
winners. Treat `keep_strict` as the default production decision. Treat
`monitor` as evidence to watch across future reviewed dates, not as permission
to change a threshold. Treat `review_relaxation_candidate` as a prompt for
deeper review, and still require a deployable scanned profile before changing
production gates.

## Threshold Scan

When enough reviewed samples exist, scan threshold combinations before changing
the scoring gate:

```bash
python3 .agents/skills/daily-a-share-news-impact/scripts/scan_selection_thresholds.py \
  --backtest local/reviews/backtests/backtest_recalibrated_v3_2026-06-01_2026-06-05.json \
  --output local/reviews/threshold_scans/threshold_scan_2026-06-01_2026-06-05.json
```

The helper joins archived `input_bundle.json` scoring dimensions with backtest
outcomes after applying the active market-cap range. Use it to compare hit
rate, average return, and sample count. The scanner also evaluates
`beneficiary_quality_min`, which applies the opportunity-specific score that
prioritizes 14-day trend, volume, main-capital recognition, institutional trend
setup, event alignment, and risk control. Treat quality-score floors as
deployable only when they pass the same promotion and production-baseline gates
as every other threshold. The current June 2026 candidate-pool calibration first
filters out samples outside the default `100-2000` billion CNY range, then scans
stock and sector thresholds. Beneficiary-only scans are the primary evidence for
the opportunity pool. The production gate keeps a conservative
`capital_recognition >= 3.6`, `institutional_trend_score >= 3.5`, and
`risk_score <= 3.8` overlay because it controlled average return and
worst-return quality better than the slightly looser best scan on the small June
sample. It also requires a
strong-mainline sector: sector impact, sector price-volume confirmation, and
sector liquidity confirmation should each be at least `4.0/5`. Pressure rows
keep tighter deterioration gates of
`trend_score <= 2.4` and `capital_recognition <= 2.6`. The scan objective also
considers payoff ratio and worst-return tail risk, so a profile that wins only
by excluding most samples, concentrating in too few report dates, or carrying
large drawdowns should not be accepted automatically.
