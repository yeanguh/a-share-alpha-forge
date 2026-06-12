# A股选股策略阈值扫描摘要

区间：2026-06-01 至 2026-06-05
方法：历史 input_bundle 评分维度 + 已回测收益标签，扫描趋势/量能/资金门槛组合。

## 版本对比

| 版本 | 样本数 | 总命中率 | 受益命中率 | 承压命中率 | 平均收益 | 中位收益 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 原始归档 | 49 | 46.9% | 52.9% | 44.4% | +0.79% | +0.17% |
| 复盘校准v3 | 41 | 56.1% | 69.2% | 55.0% | +0.37% | +0.03% |
| 阈值扫描固化v4 | 32 | 59.4% | 85.7% | 58.8% | +0.02% | -0.47% |

## 扫描最优门槛

| 参数 | 值 |
| --- | --- |
| name | profile_0099 |
| beneficiary_trend | 3.0 |
| beneficiary_volume | 3.4 |
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

## 采用结论

- 受益股机会列更重视量能确认：`volume_score >= 3.4`。
- 承压股趋势门槛更严格：`trend_score <= 2.6`。
- 周期资源股继续使用更强确认：趋势、量能、资金均不低于 `3.6`。
- 主线龙头表保留 watch leader，但赚钱准确率评估以 `eligible_beneficiaries` 为主。

## 剩余偏差

- 超市值 watch leader 仍不适合作为收益目标，只能辅助判断主线热度。
- PMI弱需求链中的工程机械承压仍有反向上涨样本，后续需要加入相对强弱或指数/板块对冲过滤。
- 连续样本仍少，后续应每天收盘后自动追加 backtest 和 close_review。
