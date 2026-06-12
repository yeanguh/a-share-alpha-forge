# A股选股策略收益质量复盘

区间：2026-06-01 至 2026-06-05
目标：不仅提高命中率，也控制尾部亏损和盈亏比。

## 收益质量对比

| 版本 | 样本数 | 命中率 | 平均收益 | 中位收益 | 平均盈利 | 平均亏损 | 盈亏比 | 最大负偏差 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 原始归档 | 49 | 46.9% | +0.79% | +0.17% | NA | NA | NA | NA |
| v4收益质量回测 | 32 | 62.5% | -0.05% | -0.65% | +3.78% | -3.21% | 1.18 | -6.24% |

## 机会列质量

| 版本 | 样本数 | 命中率 | 平均收益 | 盈亏比 | 最大负偏差 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 原始归档 | 17 | 52.9% | +0.49% | NA | NA |
| v4收益质量回测 | 7 | 85.7% | +4.16% | 2.86 | -1.80% |

## 收益质量扫描最优组合

| 参数 | 值 |
| --- | --- |
| name | profile_0003 |
| beneficiary_trend | 3.0 |
| beneficiary_volume | 3.0 |
| beneficiary_capital | 3.0 |
| beneficiary_event | 3.5 |
| beneficiary_risk_max | 4.2 |
| resource_trend | 3.6 |
| resource_volume | 3.6 |
| resource_capital | 3.6 |
| pressure_trend_max | 2.6 |
| pressure_capital_max | 2.8 |
| pressure_volume_min | 3.2 |
| observation_pressure_trend_max | 2.0 |
| observation_pressure_capital_max | 2.5 |

## 结论

- 当前机会列质量明显改善：受益股命中率高，平均收益和盈亏比都显著优于整体。
- watch leader 仍只用于主线热度识别，不纳入“能赚钱”的核心评估。
- 因为小样本扫描中 `volume_score >= 3.0` 与 `3.4` 选股结果接近，继续保留更保守的 `3.4`，防止后续弱量能样本混入。
- 后续优化重点转向承压侧和超市值 leader 的风险隔离，而不是继续放宽机会列。
