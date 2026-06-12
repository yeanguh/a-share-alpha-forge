# Sector-First Screening

Use this sequence before any stock appears in a beneficiary or pressure column.

## Sequence

1. Collect and score investment news inside the report window.
2. Map each retained news item to affected sectors or themes. Reject news that
   cannot reach at least one A-share sector.
3. Rank positive and negative `sector_candidates` separately.
4. Build stock candidates only from the selected sector list. The stock's
   `sector` field must match one selected sector candidate.
5. For each stock, validate direct exposure, 14-trading-day K-line trend,
   volume, retail VOC, capital recognition, and risk.
6. Add a stock to `可能受益A股公司` or `可能承压A股公司` only after both the
   sector gate and stock gate pass.

## Sector Candidate JSON

Use the same scoring fields as news candidates:

```json
{
  "title": "AI硬件",
  "direction": "positive",
  "magnitude": 4.2,
  "breadth": 3.8,
  "immediacy": 4,
  "confidence": 4,
  "novelty": 3.6,
  "liquidity": 4.5,
  "price_volume": 3.7
}
```

## Stock Candidate JSON

Set `sector` to one selected sector candidate title:

```json
{
  "ticker": "300308",
  "name": "中际旭创",
  "sector": "AI硬件",
  "directional_role": "beneficiary",
  "trend_score": 3.6,
  "volume_score": 3.8,
  "retail_sentiment": 4.4,
  "capital_recognition": 3.9,
  "event_alignment": 4.3,
  "risk_score": 3.8
}
```

If a stock has good price action but its sector was not selected from news, keep
it in `未入选推荐列` and explain `未通过资讯板块筛选`.

If there is no selected sector for the stock's direction, no stock can enter the
corresponding beneficiary or pressure column. Treat missing sector data as a
data-quality gap, not as permission to bypass the sector gate.
