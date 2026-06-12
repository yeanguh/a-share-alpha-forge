# Minimum Effective Return Backtest 2026-06-01 to 2026-06-05

## Rule Being Tested

- A beneficiary row counts as a hit only when return is at least `+0.5%`.
- A pressure row counts as a hit only when return is at most `-0.5%`.
- Backtest summaries now include `average_directional_return_pct`: beneficiary raw return, pressure return multiplied by `-1`.
- This reduces noise from tiny moves and avoids mixing positive opportunity returns with negative risk-readout returns.

## Current Conservative Rule: 1 Trading Day, 0.5% Effective Hit

- Recommendation rows: 10 across 3 report dates.
- Overall effective hit rate: 0.7; raw average return: 2.258%; directional average return: 1.892%.
- Beneficiary effective hit rate: 0.833; average return: 3.458%; worst return: -0.43%.
- Pressure effective hit rate: 0.5; directional average return: -0.457%.

## Raw Candidate Pool: 1 Trading Day, 0.5% Effective Hit

- Candidate rows: 81.
- Raw overall effective hit rate: 0.358; directional average return: -1.058%.
- Raw beneficiary effective hit rate: 0.372; beneficiary average return: -0.595%.

## Market-Cap-Aligned Threshold Scan

- Scan samples: 56 from 81 raw samples; excluded by market cap: 25.
- Best profile selected 11 rows; overall effective hit rate: 0.727; directional average return: 1.825%.
- Best profile beneficiary effective hit rate: 0.857; beneficiary average return: 3.129%.

## Interpretation

- The current conservative opportunity column remains materially stronger than the raw candidate pool after adding a `0.5%` effective-profit threshold.
- Beneficiary rows remain the highest-quality part of the report and should be the optimization target for the赚钱池.
- Pressure rows have weaker directional-return quality and should stay framed as risk readout rather than as a mirror-image opportunity list.
- Future calibration should report raw hit rate, effective hit rate, and directional average return so tiny moves and mixed role signs do not overstate strategy quality.
