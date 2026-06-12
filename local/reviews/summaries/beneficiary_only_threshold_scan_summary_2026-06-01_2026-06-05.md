# Beneficiary-Only Threshold Scan 2026-06-01 to 2026-06-05

## Purpose

The opportunity pool is the `可能受益A股公司` list. This scan filters calibration samples to beneficiary rows only, after applying the active market-cap range and the `0.5%` effective-hit threshold. The latest scan also tests `beneficiary_quality_score` floors so the new trend/volume/main-capital opportunity score is evaluated from archived outcomes rather than intuition.

## Scan Scope

- Role scope: `beneficiary`.
- Raw samples: 81; market-cap-aligned samples: 56; beneficiary scan samples: 28.
- Excluded by market cap: 25; excluded by role: 28.

## Promotion Gate

- Gate: `{"min_report_count": 3, "min_hit_rate": 0.8, "min_average_directional_return_pct": 2.0, "min_worst_directional_return_pct": -1.0, "min_worst_report_directional_return_pct": 0.0}`.
- Promotable profiles: 0 / 419904.
- Deployable profiles: 0 / 419904. A deployable profile must pass the promotion gate and beat the current production baseline.

## Current Production Baseline Comparison

- Baseline profile: `current_production_gate`.
- Baseline selected count: 6; effective hit rate: 0.833; average return: 3.447%; worst return: -0.54%.
- Baseline promotion status: False; failure reasons: ['report_count_below_gate'].
- Best scanned profile beats production baseline: False; production comparison failure reasons: ['average_directional_return_below_production'].

## Best Beneficiary-Only Profile

- Score: 1.1827 (base score 1.2227; includes report-coverage penalty).
- Passes promotion gate: False; failure reasons: ['report_count_below_gate'].
- Beats production baseline: False; failure reasons: ['average_directional_return_below_production'].
- `beneficiary_quality_score` floor: 0.0.
- Report-date coverage: 2 dates; worst report-date directional return: 1.85%.
- Profile: `{"name": "profile_0973", "beneficiary_trend": 3.0, "beneficiary_volume": 3.2, "beneficiary_capital": 3.0, "beneficiary_event": 3.5, "beneficiary_quality_min": 0.0, "beneficiary_risk_max": 4.0, "resource_trend": 3.6, "resource_volume": 3.6, "resource_capital": 3.6, "beneficiary_sector_impact": 3.6, "beneficiary_sector_price_volume": 3.6, "beneficiary_sector_liquidity": 3.6, "pressure_trend_max": 2.4, "pressure_capital_max": 2.6, "pressure_volume_min": 3.2, "observation_pressure_trend_max": 2.0, "observation_pressure_capital_max": 2.5}`.
- Selected count: 7; effective hit rate: 0.857; average return: 3.129%; worst return: -0.54%.

## Beneficiary Quality Floor Check

| `beneficiary_quality_score` floor | Selected count | Report dates | Hit rate | Average return | Worst return | Decision |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 0.0 | 7 | 2 | 0.857 | 3.129% | -0.54% | Not deployable: fails coverage and baseline return comparison |
| 3.0 | 7 | 2 | 0.857 | 3.129% | -0.54% | Same as 0.0 on current sample |
| 3.2 | 7 | 2 | 0.857 | 3.129% | -0.54% | Same as 0.0 on current sample |
| 3.4 | 1 | 1 | 1.0 | 3.89% | 3.89% | Too concentrated; fails report-count and production coverage comparison |

## Production Error Diagnostics

The current production gate selected 6 beneficiary rows from the market-cap-aligned candidate pool.

- Selected misses: 1. The only miss is 2026-06-05 `300620 光库科技`, with `-0.54%` same-day return and `beneficiary_quality_score 3.20`; this is a small miss near the effective-hit threshold, not a large drawdown.
- Missed winners: 8. The largest missed winners were `002126 银轮股份` on 2026-06-04 (`+3.97%`, quality `2.28`), `688072 拓荆科技` on 2026-06-04 (`+3.66%`, quality `2.76`), and `002792 通宇通讯` on 2026-06-05 (`+3.49%`, quality `2.24`). These mostly failed trend, volume, capital-recognition, and sector-strength gates.
- Avoided losers: 14. The largest avoided losers included `300456 赛微电子` (`-8.53%`), `000960 锡业股份` (`-4.91%`), `000657 中钨高新` (`-4.52%`), and `688180 君实生物-U` (`-3.71%`). These failures support keeping the current hard gates for weak trend, weak capital recognition, high risk, and weak sector confirmation.

Interpretation: the current gate is conservative and does miss some short-lived rebounds, but the missed winners have weaker evidence quality than the avoided losers. Do not loosen the opportunity gate until missed winners repeat with stronger quality scores and cross-date stability.

### Failure Reason Summary

| Failure reason | Samples | Missed winners | Avoided losers | Hit rate | Average return | Gate action | Interpretation |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `sector_impact_score_below_profile` | 20 | 6 | 14 | 0.300 | -1.251% | `keep_strict` | Strong sector gate is protective; do not loosen on current evidence. |
| `sector_price_volume_below_profile` | 20 | 6 | 14 | 0.300 | -1.251% | `keep_strict` | Sector price/volume confirmation remains useful. |
| `sector_liquidity_below_profile` | 20 | 6 | 14 | 0.300 | -1.251% | `keep_strict` | Sector liquidity gate filters more losers than winners. |
| `capital_recognition_below_profile` | 21 | 7 | 14 | 0.333 | -1.025% | `keep_strict` | Main-capital gate is protective and should stay strict. |
| `trend_score_below_profile` | 10 | 2 | 8 | 0.200 | -1.587% | `keep_strict` | 14-day trend gate strongly protects against weak setups. |
| `risk_score_above_profile` | 6 | 1 | 5 | 0.167 | -3.868% | `keep_strict` | Risk ceiling prevents large drawdowns. |
| `volume_score_below_profile` | 16 | 7 | 9 | 0.438 | -0.188% | `keep_strict` | Volume gate is less decisive than sector/trend/risk, but still excludes a negative-return group. |

Takeaway: the strongest evidence supports keeping sector-strength, main-capital,
trend, and risk gates strict. Volume is the least decisive `keep_strict` gate,
but it still has negative average return on the current sample and should not be
relaxed without more reviewed dates.

## Best Profile By Report Date

- 2026-06-03: count 2; hit rate 1.0; average return 1.85%; directional average 1.85%.
- 2026-06-05: count 5; hit rate 0.8; average return 3.64%; directional average 3.64%.

## Current Conservative Production Gate

- Beneficiary selected count: 6.
- Beneficiary effective hit rate: 0.833; average return: 3.447%; worst return: -0.54%.

## Decision

- Do not relax production thresholds from the current conservative gate yet.
- The best beneficiary-only scan fails the promotion gate because report-date coverage is below the required minimum.
- Future threshold changes should require at least one deployable profile, not just a better pooled score or a promotable profile.
- A deployable profile must both pass the promotion gate and beat the production baseline on report coverage, hit rate, average directional return, and worst directional return.
- Do not add a hard `beneficiary_quality_score` floor yet. Use it for ranking and continue collecting reviewed samples until a non-concentrated floor profile becomes deployable.
- Use `production_error_diagnostics` before changing gates: selected misses should reveal actual failure modes, and missed winners should only drive loosening when their evidence quality is stronger than the avoided losers.
- Use `--role-scope beneficiary` for future opportunity-pool calibration so pressure risk rows do not steer the赚钱池 thresholds.
