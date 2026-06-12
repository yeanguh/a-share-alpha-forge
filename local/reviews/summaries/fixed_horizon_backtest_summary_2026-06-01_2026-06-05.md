# Fixed-Horizon Backtest Summary 2026-06-01 to 2026-06-05

## Why This Was Added

Earlier backtests compared each report-date open with the latest available quote. That makes older reports carry longer holding periods than newer reports, while the daily brief is framed as a one-to-three-session readout. Fixed-horizon backtests make calibration closer to the intended short-term decision window.

## Current Conservative Rule Replay: 1 Trading Day

- Recommendation rows: 10 across 3 report dates.
- Overall hit rate: 0.7; average return: 2.456%; payoff ratio: 3.846.
- Beneficiary hit rate: 0.833; average return: 3.73%; worst return: -0.35%.
- Pressure hit rate: 0.5; average return: 0.545%.

## Current Conservative Rule Replay: 3 Trading Days

- Evaluated rows: 3 from 10 recommendation rows; later reports were marked `insufficient_horizon` because the third close was unavailable.
- Overall hit rate: 1.0; average return: -0.893%.
- Beneficiary hit rate: 1.0; average return: 5.74%.

## Candidate Pool: 1 Trading Day

- Raw candidate rows: 81; raw overall hit rate: 0.395; beneficiary hit rate: 0.395.
- Market-cap-aligned scan samples: 56 from 81 raw samples; excluded by market cap: 25.
- Best scanned 1-day profile selected 11 rows; overall hit rate: 0.727; beneficiary hit rate: 0.857; beneficiary average return: 3.359%.

## Calibration Takeaways

- Fixed-horizon evidence supports keeping the strong-mainline and strict stock-quality gates for the opportunity column.
- The opportunity column is substantially stronger than the raw candidate pool on one-day outcomes.
- Pressure rows are less reliable at the one-day horizon and should remain risk-readout rows rather than opportunity-style recommendations.
- Use horizon `1` and `3` together in future weekly reviews: horizon `1` measures immediate money response; horizon `3` checks whether the theme persists.
