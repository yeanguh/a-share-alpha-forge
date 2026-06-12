# Strong-Mainline Sector Gate Replay 2026-06-01 to 2026-06-05

## Rule Being Tested

- Beneficiary rows must already pass the stricter stock gate.
- The source positive sector must also have `impact_score >= 4.0`, `price_volume >= 4.0`, and `liquidity >= 4.0`.
- The test reassembled historical input bundles with the current scripts, then backtested the resulting recommendation rows with Tencent free quote and K-line data.

## Replay Result

- Recommendation rows: 10 across 3 report dates.
- Overall hit rate: 0.8; average return: 2.159%; payoff ratio: 3.147.
- Beneficiary hit rate: 0.833; average return: 4.813%; worst return: -0.07%.
- Pressure hit rate: 0.75; average return: -1.823%.

## Selected Rows

- 2026-06-03 beneficiary 600522 中天科技 光通信与CPO: 6.24%, hit=True
- 2026-06-03 pressure 600029 南方航空 航空景气偏低: -1.52%, hit=True
- 2026-06-03 pressure 000539 粤电力A 电力板块回撤: -5.56%, hit=True
- 2026-06-04 pressure 300624 万兴科技 AI应用回撤: -0.21%, hit=True
- 2026-06-05 beneficiary 000063 中兴通讯 通信与6G: 4.71%, hit=True
- 2026-06-05 beneficiary 002281 光迅科技 光纤光缆/CPO: 4.56%, hit=True
- 2026-06-05 beneficiary 600522 中天科技 通信与6G: 3.44%, hit=True
- 2026-06-05 beneficiary 600498 烽火通信 通信与6G: 10.0%, hit=True
- 2026-06-05 beneficiary 300620 光库科技 光纤光缆/CPO: -0.07%, hit=False
- 2026-06-05 pressure 600019 宝钢股份 PMI弱需求周期链: 0.0%, hit=False

## Interpretation

- The gate removes weak positive sectors from the opportunity column and leaves mostly AI hardware, optical communication/CPO, and communication/6G rows.
- This improves alignment with the target: selected opportunity stocks should be in an uptrend and attached to the live market mainline.
- Keep the sample-size warning: this replay is useful calibration evidence, not proof of permanent edge.
