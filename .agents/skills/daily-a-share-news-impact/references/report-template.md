# Report Template

Write the final report in Chinese by default. Keep the document focused on a
low-frequency daily readout from free available data sources.

## Header

```markdown
# A股投资资讯影响简报

时间窗：YYYY-MM-DD 09:30 至 YYYY-MM-DD 09:30（北京时间）
结论：短期市场预计【偏强/震荡偏强/震荡/震荡偏弱/偏弱】
核心驱动：一句话概括净影响、主线、最大风险和置信度。
说明：本简报仅作信息研究，不构成个性化投资建议。
数据源：免费可用接口优先；未启用付费行情/终端接口。
```

## 大盘整体情绪

```markdown
## 大盘整体情绪

- 指数状态：上证/深成指/创业板/科创50的方向和相对强弱。
- 市场宽度：上涨/下跌家数、涨停/跌停、强弱板块扩散情况。
- 风险偏好：高位股、低位股、权重、题材、周期、消费之间的风格。
- 情绪结论：【偏热/温和修复/中性/偏弱/恐慌释放】。
```

## 资金方向/热度

```markdown
## 资金方向/热度

- 资金方向：【净流入扩散/结构性流入/缩量观望/净流出扩散/拥挤分化】
- 央行公开市场操作：报告日期当天中国人民银行公开市场业务操作公告；写明操作工具、金额、期限、利率、净投放/净回笼，以及公告未更新或无法访问时的数据缺口。
- 成交额与量能：...
- 主力/ETF/融资/北向：仅使用免费可得数据；缺口要说明。
- 行业流向：...
- 与资讯排序的关系：资金是否支持正面主线，或是否验证负面风险。
```

## 每日主线板块/概念与龙头个股

Always include this module after `资金方向/热度`. Select the top 5 mainline
sectors or concepts from the ranked sector candidates. Prefer positive
mainlines with both news impact and price/volume confirmation; if fewer than 5
positive mainlines exist, fill the table with the strongest remaining sector
candidates and clearly mark their direction. Then list up to 10 leading stocks
from those mainlines.

The leading-stock list is a market-readout module, not a recommendation table.
It may include watch-only leaders that fail the active market-cap gate, but
watch-only leaders must still have confirmed trend, volume, capital
recognition, direct event alignment, and acceptable risk. Do not fill the table
with weakly confirmed stocks just to reach 10 rows. Stocks can enter
`可能受益A股公司` only through the stricter stock opportunity gate in the later
module.

```markdown
## 每日主线板块/概念与龙头个股

### 前五主线板块/概念

| 排名 | 板块/概念 | 方向 | 分数 | 主线依据 | 资金/量价确认 | 风险提示 |
| ---: | --- | --- | ---: | --- | --- | --- |

### 主线龙头个股 Top 10

| 排名 | 股票 | 所属主线 | 市值(亿元) | 龙头依据 | 14日K线/量能 | 散户VOC/情绪 | 资金认可度 | 入选状态 |
| ---: | --- | --- | ---: | --- | --- | --- | --- | --- |
```

## 正向负向事件 Top

Before the positive and negative news tables, include a sector screening table:

```markdown
## 正向负向事件Top

### 资讯筛出的板块候选

| 方向 | 排名 | 板块/主题 | 分数 | 关键资讯 | 资金/量价确认 | 是否进入个股筛选 |
| --- | --- | --- | --- | --- | --- | --- |
```

Only stocks from sectors marked as entering stock screening can appear in the
opportunity or pressure tables. For opportunity rows, the sector must also pass
the strong-mainline gate: sector impact score, price-volume confirmation, and
liquidity confirmation should each be at least `4.0/5`. Stocks from weaker
positive sectors belong in the observation list even when their individual
scores are acceptable.

### 正向事件 Top 10

| 排名 | 分数 | 资讯 | 对应板块 | 影响逻辑 | 可能受益A股公司 | K线/量能参考 | 短期影响 | 来源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

### 负向事件 Top 10

| 排名 | 分数 | 资讯 | 对应板块 | 影响逻辑 | 可能承压A股公司 | K线/量能参考 | 短期影响 | 来源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

Column guidance:

- `分数`: numeric score such as `4.4/5`, with optional `高/中高`.
- `资讯`: concise event statement and publication or announcement time.
- `对应板块`: use only sectors selected from the sector screening table.
- `影响逻辑`: one to three direct transmission channels.
- `可能受益A股公司` / `可能承压A股公司`: include ticker, company name, factor,
  and confidence only after the stock passes the company recommendation gate.
- `K线/量能参考`: summarize recent trend, volume or turnover confirmation, and
  whether price action confirms or diverges from the news.
- `短期影响`: expected one-to-three-session sector or index reaction.
- `来源`: cite the sources used by the agent. Keep citations close to the row or
  immediately after the table when the renderer cannot place citations inside
  tables.

## 个股机会的筛选结果

Only list stocks inside the configured market-cap range. The default range is
100 to 2000 billion CNY, and a run can override it with
`--min-market-cap-billion` and `--max-market-cap-billion`. Stocks outside the
active range must be placed under excluded/observation notes.

```markdown
## 个股机会的筛选结果

### 可能受益A股公司

| 股票 | 市值(亿元) | 板块 | 入选状态 | 14日K线 | 14日量能 | 散户VOC/情绪 | 资金认可度 | 机会 | 风险 | 综合评级 | 操作倾向 |
| --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

### 可能承压A股公司

| 股票 | 市值(亿元) | 板块 | 入选状态 | 14日K线 | 14日量能 | 散户VOC/情绪 | 资金认可度 | 承压因素 | 风险 | 综合评级 | 操作倾向 |
| --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

### 未入选/观察列表

| 股票 | 原因 |
| --- | --- |
```

Add `入选状态` or explanatory wording when a stock fails the gate, such as
`未入选推荐列：市值不在当前参数区间`, `未入选推荐列：未通过资讯板块筛选`,
or `未入选推荐列：散户情绪过热且风险高`. When retail VOC is unavailable, write
`VOC数据不足` and lower the confidence of the retail sentiment score.

Use `高关注`, `关注`, `中性观察`, `谨慎观察`, or `风险回避` for `综合评级`.
Use non-personalized tendencies such as `等待放量确认`, `趋势跟踪观察`,
`回撤后再评估`, `事件落地后再评估`, `风险回避观察`, or `仅作主题跟踪`.
For pressure candidates that fail the gate, use `仅作风险跟踪`.

## 短期市场判断

```markdown
## 短期市场判断

- 方向：震荡偏强/震荡/震荡偏弱等。
- 理由：列出 3-5 条最高权重因素。
- 多空结构：概括正面 Top 10 与负面 Top 10 的净影响差异。
- 资金方向：结合免费可得的全A资金流向、主力资金、ETF/北向/融资和行业流向。
- 个股结论：概括评分最高和风险最高的代表股票。
- 主要上行风险：...
- 主要下行风险：...
- 观察指标：成交额/汇率/利率/商品/关键政策发布时间等。
```

Keep the conclusion actionable but not advisory. Do not tell the user to buy,
sell, hold, add, reduce, set target prices, set stop-loss prices, or use a
specific position size.

## 数据留痕与复盘

End with a brief note:

```markdown
## 数据留痕与复盘

- 日报归档：.local/daily-a-share-news-impact/YYYY-MM-DD/
- 收盘复盘：15:00后补充 close_review.json，校准板块命中、个股命中和策略偏差。
- 周复盘：聚合本周日复盘，不因单日噪音调整策略。
```
