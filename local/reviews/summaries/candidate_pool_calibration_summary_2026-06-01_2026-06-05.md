# Candidate-Pool Threshold Calibration 2026-06-01 to 2026-06-05

## Candidate Pool Baseline

- Scope: 81 candidate stock-role rows from archived input bundles before market-cap filtering.
- Raw overall hit rate: 0.457; average return: -0.313%.
- Raw beneficiary hit rate: 0.372; average return: -1.242%.

## Market-Cap-Aligned Scan

- Active market-cap range: 100.0-2000.0 billion CNY.
- Raw samples: 81; scan samples: 56; excluded by market cap: 25.
- Best scanned score: 1.2863.
- Best scanned profile: `{"name": "profile_0001", "beneficiary_trend": 3.0, "beneficiary_volume": 3.2, "beneficiary_capital": 3.0, "beneficiary_event": 3.5, "beneficiary_risk_max": 3.8, "resource_trend": 3.6, "resource_volume": 3.6, "resource_capital": 3.6, "beneficiary_sector_impact": 3.6, "beneficiary_sector_price_volume": 3.6, "beneficiary_sector_liquidity": 3.6, "pressure_trend_max": 2.4, "pressure_capital_max": 2.6, "pressure_volume_min": 3.2, "observation_pressure_trend_max": 2.0, "observation_pressure_capital_max": 2.5}`.
- Selected count: 10; overall hit rate: 0.9; average return: 2.246%.
- Beneficiary count: 6; hit rate: 1.0; average return: 4.932%; worst return: 0.61%.

## Current Conservative Rule Replay

- Recommendation rows: 10 across 3 report dates.
- Overall hit rate: 0.8; average return: 2.159%; payoff ratio: 3.147.
- Beneficiary hit rate: 0.833; average return: 4.813%; worst return: -0.07%.

## Rule Update

- Threshold scans now exclude samples outside the active market-cap range before ranking profiles.
- Beneficiary opportunity rows require a strong-mainline sector gate: sector impact, price-volume, and liquidity confirmation.
- The production gate keeps the stricter `capital_recognition >= 3.6` and `risk_score <= 3.8` overlay as a conservative quality filter.
- Treat this as small-sample calibration and re-check weekly before further tightening or relaxing thresholds.
