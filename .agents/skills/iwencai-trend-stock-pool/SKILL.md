---
name: iwencai-trend-stock-pool
description: 基于同花顺问财风格的A股趋势承接选股技能。每当用户要求“问财选股”“生成选股策略”“三日趋势承接”“按不同策略筛股票池”“提供候选股票池/筛选池”时都应使用本 skill。它会输出可复制到问财的自然语言条件，并可用仓库已有 akshare/pandas 能力生成分策略股票池。
---

# 同花顺问财趋势承接股票池 Skill

这个 skill 把 `supermind_trend_support_3day.py` v20 的三日趋势承接思路拆成多个问财风格策略，并用 `supermind_broad_etf_combo_v73.py` 的宽基 ETF 趋势权重作为市场环境提示。它可以用仓库已有的 Python 数据能力生成候选股票池。

## 何时使用

用户要求以下任一任务时使用：

- 把 SuperMind/趋势承接策略转换成同花顺问财选股条件。
- 按核心主线、卫星主线、宽基、资金承接、质量趋势、突破等不同策略筛选股票。
- 生成股票筛选池、候选池、观察池，并保存为 JSON/CSV/Markdown。
- 基于当前公开行情做低频 A 股趋势选股。

## 数据与限制

优先使用本 skill 附带脚本：

```bash
uv run python .agents/skills/iwencai-trend-stock-pool/scripts/build_stock_pools.py
```

脚本使用 `akshare` 获取全 A 快照、概念板块成分、个股前复权日线和 ETF 日线。它能近似生成策略池，但不能完全替代同花顺问财的专有字段，例如“近3日主力净流入”。遇到这类字段时：

- 在问财语句中保留原始条件；
- 在本地脚本中用成交额、换手率、量能比、趋势、跳空、影线和 K 线承接近似；
- 本地 akshare 概念板块使用可获取的近似名称，例如 `铜缆高速连接`、`半导体概念`、`AI芯片`、`液冷概念`，不强行等同于问财的全部主题标签；
- 在最终回答中说明这是“本地公开数据近似池”，如需精确主力净流入请把问财结果导出后再复核。

## 最新策略口径

- `supermind_trend_support_3day.py`：核心主线优先，卫星主题补充；大盘强/中/弱/退潮决定仓位；单票最多约18%，最多5只；持有满3个交易日仍未上涨会退出，并叠加止损、止盈、移动止盈和支撑破位。
- 核心主题：光模块、CPO、高速铜缆、连接器、PCB、玻璃基板、ABF载板、存储芯片、半导体设备、AI服务器、液冷服务器。
- 卫星主题：半导体材料、光刻胶、电子特气、覆铜板、铜箔、MLCC。
- 关键买点：价格站上20日线，10日线接近或强于20日线，20日线接近或强于60日线；靠近10日线承接或接近20日新高突破；不过度偏离20日线和20日高点；量能温和；今日涨幅、跳空、上影线、下影线都要过滤。
- `supermind_broad_etf_combo_v73.py`：创业板 ETF `159915` 趋势向上给50%，否则15%；中证500 ETF `510500` 趋势向上给30%，否则20%；剩余给沪深300 ETF `510310`。这个结果只作为市场弹性/防守提示，不直接覆盖个股排序。

## 推荐流程

1. 读取 `references/strategies.md`，选取用户需要的策略；若用户问“最新 SuperMind 口径”，优先使用核心/卫星主线和 ETF v73 说明。
2. 如用户只要问财语句，直接给出对应策略的 `text` 块。
3. 如用户要股票池，运行脚本生成结果：

```bash
uv run python .agents/skills/iwencai-trend-stock-pool/scripts/build_stock_pools.py \
  --output-dir tmp/iwencai-trend-stock-pool/$(date +%F)
```

4. 读取输出的 `summary.md` 和 `stock_pools.json`，向用户汇总每个策略的前 10-20 只候选，并说明 `market_overlay` 的 ETF 权重提示。
5. 只有用户明确要求归档时，才把 `--output-dir` 改为 `local/stock_pools/$(date +%F)`；运行缓存保留在输出目录的 `cache/` 下，不要提交。
6. 明确风险提示：结果仅用于研究和复盘，不构成买卖建议。

## 综合推荐顺序

当用户要求“最推荐的股票”“依次推荐”“Top 5”时，使用脚本输出的 `recommendations`，不要只照抄单一策略排名。综合推荐规则是：

1. `main_theme` 主线三日趋势承接是第一优先池，核心主题候选优先于卫星主题候选。
2. `fund_flow` 资金/量能承接近似用于确认流动性、成交承接和近3日主力净流入方向。
3. `broad_trend` 宽基趋势承接用于确认技术形态是否脱离单一主题。
4. `quality_trend` 质量趋势用于给估值不过贵、PE/PB 过滤后的标的加分。
5. `breakout_theme` 主线突破增强用于确认强势主线加速，但不单独覆盖主线承接优先级。
6. `broad_etf_overlay` 只用于解释市场环境：创业板/中证500趋势强时可偏弹性，弱时偏沪深300防守。

脚本会按“核心主线优先 + 多策略共振 + ETF 环境提示”生成 `recommendations.md` 和 `recommendations.csv`。如果 `main_theme` 有候选，综合推荐默认只从主线候选里选，再让其他策略命中提供加分；如果主线池为空，再依次使用资金、宽基、质量和突破池补位。

当目标是提高“买入后三日内上涨概率”时，优先使用 `high_confidence_recommendations`，不要机械买满综合 Top 5。`high_confidence_v1` 是基于 2026-06-01 至 2026-06-23 本地历史样本校准的二次过滤：推荐 Top 5、主线排名不超过 8、score 不低于 3.8、20 日涨幅 8%-35%、5 日涨幅 -6%-3%、量比 0.75-1.90、距 20 日线 0%-28%、上影线不超过 35%、收盘位于当日振幅 60% 以上。该口径历史三日有效命中率为 77.27%，样本 22 个；如果当日为空，应降低出手频率而不是放宽条件。

## 常用参数

```bash
# 只跑部分策略
uv run python .agents/skills/iwencai-trend-stock-pool/scripts/build_stock_pools.py \
  --strategies main_theme,fund_flow,quality_trend \
  --output-dir tmp/iwencai-trend-stock-pool/$(date +%F)

# 限制处理股票数，适合快速试跑
uv run python .agents/skills/iwencai-trend-stock-pool/scripts/build_stock_pools.py \
  --max-stocks 300 \
  --output-dir tmp/stock_pools_smoke

# 放宽科创板过滤
uv run python .agents/skills/iwencai-trend-stock-pool/scripts/build_stock_pools.py \
  --include-star \
  --output-dir local/stock_pools/$(date +%F)
```

## 输出文件

脚本会在输出目录生成：

- `stock_pools.json`：完整结构化结果。
- `summary.md`：分策略摘要和前排候选。
- `recommendations.md`、`recommendations.csv`：按推荐顺序生成的综合 Top 5。
- `high_confidence_recommendations.csv`：面向三日上涨概率目标的高置信度出手池；可能为空。
- `main_theme.csv`、`broad_trend.csv`、`fund_flow.csv`、`quality_trend.csv`、`breakout_theme.csv`：各策略明细。

`stock_pools.json` 还包含 `theme_design` 和 `market_overlay`：

- `theme_design.core`、`theme_design.satellite`：当前主题分层。
- `market_overlay.target_weights`：按 ETF v73 计算的 `159915.SZ`、`510500.SH`、`510310.SH` 参考权重。

## 策略名称

- `main_theme`：主线三日趋势承接。
- `broad_trend`：宽基趋势承接。
- `fund_flow`：资金/量能承接近似。
- `quality_trend`：质量趋势。
- `breakout_theme`：主线突破增强。
- `broad_etf_overlay`：宽基 ETF v73 环境确认，不是脚本 `--strategies` 参数。

## 回答格式

给用户股票池时，优先使用这种结构：

```markdown
已生成分策略股票池：[summary.md](绝对路径)

| 策略 | 候选数 | 前排候选 |
| --- | ---: | --- |
| 主线三日趋势承接 | 8 | 000001.SZ 平安银行；... |

综合推荐：

| 推荐 | 代码 | 名称 | 理由 |
| ---: | --- | --- | --- |
| 1 | 000001.SZ | 平安银行 | 命中主线和资金承接，量能温和，离均线不远 |

说明：本地脚本用公开行情近似问财条件；主力净流入等字段需以问财实盘结果复核。ETF v73 只提示市场弹性/防守环境，不构成买卖建议。
```

如果运行失败，说明失败的接口和可替代路径，例如“先复制问财语句到同花顺导出结果，再用脚本做二次技术过滤”。
