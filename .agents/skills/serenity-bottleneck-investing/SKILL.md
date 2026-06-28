---
name: serenity-bottleneck-investing
description: >-
  Use this skill for Serenity（白毛股神）style bottleneck/chokepoint investing,
  supply-chain drilling, AI/hardware/robotics/semiconductor upstream scarcity
  research, 产业链卡口挖掘, 供给瓶颈投资, 隐形冠军筛选, or when the user asks to
  apply Serenity's methodology to find overlooked stocks. It turns a large
  secular theme into a verified industry-chain map, identifies links with
  hard supply constraints, scores listed companies by bottleneck value,
  validates mispricing and catalysts, and outputs a research memo or watchlist.
  Trigger even when the user does not mention Serenity if the task is about
  finding non-obvious upstream suppliers, unavoidable scarce inputs, or
  "who benefits most when downstream demand explodes but supply cannot expand".
---

# Serenity Bottleneck Investing

## Purpose

Apply the Serenity（白毛股神）style "瓶颈卡口" framework to investment research.
The skill is for finding investable bottlenecks in a supply chain, not for
copying social-media trades or making unsupported performance claims.

Core idea:

> Start from a high-certainty demand cycle, drill upstream from the obvious
> leader, and find the narrow link that the whole chain cannot bypass. The best
> candidate is where demand is elastic upward but supply is physically,
> technically, or institutionally constrained.

## Important Caveat

Treat Serenity's public identity, performance claims, and viral case studies as
context, not audited evidence. Do not repeat "2026年收益4502%" or similar claims
as fact unless a reliable primary source is supplied and verified. The reusable
asset is the research method:

**大趋势 -> 供应链 -> 物理约束 -> 瓶颈卡口 -> 稀缺供应商 -> 低配误定价 -> 催化跟踪 -> 反证退出。**

## When To Use

Use this skill when the user asks for:

- Serenity/白毛股神投资方法论、瓶颈卡口投资法、chokepoint investing.
- 从 AI 算力、人形机器人、半导体、光通信、先进封装、储能、军工、医疗器械等赛道挖上游机会.
- "不要直接买龙头，帮我找上游最受益/最卡脖子的环节".
- 产业链里谁最不可替代、谁最难扩产、谁最容易涨价.
- 小盘隐形冠军、寡头供应商、机构低配机会的研究框架.
- 把一个热门主题拆成可跟踪的供需缺口模型或自动化监控清单.

If the user wants broad industry mapping first, use `industry-chain-analysis`
before or alongside this skill. If the user then needs A-share fundamentals,
valuation, or buy points, hand off to `china-stock-analysis` and
`china-stock-price-analysis` after bottleneck candidates are narrowed.

## The Four Hard Standards

A qualified bottleneck should satisfy most of these standards. If fewer than
three are met, classify it as "普通受益环节" rather than "卡口".

| Standard | Question | Strong Evidence |
| --- | --- | --- |
| 不可替代 | 下游是否没有成熟替代技术、材料、设备或供应商? | 客户认证周期长、可靠性要求高、设计绑定、专利/工艺壁垒 |
| 供给刚性 | 产能是否无法在短期快速释放? | 扩产周期长、设备交期长、良率爬坡慢、原材料/许可证/人才约束 |
| 寡头垄断 | 全球供给是否由少数企业控制? | CR2/CR3 高、核心客户集中采购、供应商名单稳定 |
| 机构低配 | 市场是否还没充分定价这个卡口价值? | 旧业务标签、卖方覆盖少、估值未反映新需求、持仓拥挤度低 |

## Six-Step Workflow

### 1. Lock The Secular Cycle

Start with a demand wave that is large, durable, and measurable. Examples:
AI data centers, high-speed optical interconnect, HBM/advanced packaging,
humanoid robots, power semiconductors, solid-state batteries, aerospace engines.

Verify:

- Who is the visible downstream winner or anchor customer?
- What concrete demand metric is growing: capex, shipments, compute clusters,
  robot units, wafers, racks, bandwidth, modules, equipment orders?
- What is the expected time window: 6-12 months, 1-3 years, or 3-5 years?
- Is this a real capacity cycle or only a concept-market narrative?

### 2. Drill Upstream Layer By Layer

Build the chain from the visible leader backward:

`终端/系统 -> 核心模组 -> 芯片/部件 -> 制造工艺 -> 设备 -> 材料 -> 原料/能源/许可证/数据/IP`

At each layer, name:

- Main products and process steps.
- Key suppliers and customers.
- Value share or cost share if available.
- Lead time, certification time, and capacity expansion time.
- Alternative technologies or substitute suppliers.

Do not stop at the first investable company. Continue upward until the chain
starts to hit physical, technical, regulatory, or oligopoly constraints.

### 3. Ask The Four Physical Constraint Questions

For every material link, answer:

1. 当前供给寡头是谁?
2. 产能扩张周期多久，卡在哪里?
3. 是否存在成熟替代方案，替代成本多高?
4. 下游是否刚需采购，能否把涨价传导出去?

Only promote a link to "candidate chokepoint" when the answers show structural
scarcity, not temporary popularity.

### 4. Locate The Narrowest Link

Filter out:

- Links with many suppliers and easy expansion.
- Links where downstream can dual-source quickly.
- Links where the claimed barrier is only brand or concept.
- Links where demand is strong but value capture sits elsewhere.

Keep links where the chain would slow down, fail to scale, or suffer margin
pressure without that input. This is the "河道收窄点".

### 5. Validate And De-Risk

Run a hard validation pass before naming investable candidates:

- Capacity: current capacity, expansion plan, capex, equipment delivery,
  utilization, yield, ramp schedule.
- Customer validation: signed customers, design wins, certification,
  qualification cycle, customer concentration.
- Economics: gross margin, pricing power, cost pass-through, revenue elasticity.
- Market pricing: valuation, liquidity, sell-side coverage, institutional
  ownership, recent rerating, short interest if relevant.
- Governance: related-party risk, dilution, debt, audit quality, regulatory
  risk, sanctions/export-control exposure.
- Technical route risk: whether a competing architecture can bypass the link.

### 6. Build The Tracking Model

Turn the thesis into repeatable monitoring:

- Weekly demand indicators: downstream capex, orders, shipment guidance,
  utilization, inventory, end-market pricing.
- Supply indicators: announced capacity, construction progress, equipment
  delivery, hiring, production permits, yield commentary.
- Price/margin indicators: ASP, spot price, contract pricing, gross margin,
  backlog, lead time.
- Customer/catalyst indicators: new certifications, design wins, volume ramps,
  earnings calls, filings, export-control changes.
- Invalidating signals: alternative technology adoption, new entrants, customer
  switching, margin compression, capex overbuild, insider selling, dilution.

## Scoring Rubric

Score each candidate link/company from 0 to 5. Prefer ranges when evidence is
thin; mark "待验证" rather than inventing precision.

| Dimension | 0-1 | 2-3 | 4-5 |
| --- | --- | --- | --- |
| Demand Certainty | Hype only | Early demand or mixed visibility | Capex/order/customer data supports growth |
| Bottleneck Severity | Many substitutes | Some constraint, partial substitutes | Chain cannot scale without it |
| Supply Rigidity | Easy expansion | Medium lead time | Long expansion, yield, equipment, permit or material constraint |
| Oligopoly Power | Fragmented | Several credible suppliers | 2-3 dominant suppliers or unique capability |
| Value Capture | Low margin/pass-through | Some pricing power | Clear ASP/margin/revenue elasticity |
| Market Mispricing | Fully crowded | Partly recognized | Old label/low coverage/under-owned |
| Catalyst Visibility | None | Possible but vague | Dated catalyst within 3-12 months |
| Evidence Quality | Social-media only | Mixed secondary sources | Filings, primary docs, customer data, hard numbers |
| Downside/Route Risk | High and near-term | Manageable | Clear invalidation triggers and favorable asymmetry |

Priority formula:

`卡口优先级 = bottleneck severity + supply rigidity + oligopoly power + value capture + mispricing + catalyst visibility - route/governance risk`

Do not use the score mechanically as a buy recommendation. Use it to rank where
to spend research time.

## Required Output Templates

### Quick Answer

Use this for short user questions.

```markdown
## 结论
[一句话判断：这个主题的潜在卡口在哪里，为什么]

## 产业链下钻
| 层级 | 环节 | 关键供应商 | 供给约束 | 替代风险 | 初判 |
| --- | --- | --- | --- | --- | --- |

## 候选卡口
| 排名 | 卡口环节 | 代表公司 | 符合的4条标准 | 催化剂 | 反证条件 |
| --- | --- | --- | --- | --- | --- |

## 下一步验证
[最需要补的3-5条证据]
```

### Full Research Memo

Use this for "完整分析/报告/帮我找标的/建立跟踪模型".

```markdown
# [主题] Serenity瓶颈卡口投研备忘录

## 1. 核心结论
- 最可能的卡口:
- 最值得跟踪的公司:
- 暂不构成卡口的热门环节:
- 最大反证风险:

## 2. 超级周期与需求证据
| 指标 | 当前证据 | 对上游的传导 | 置信度 |
| --- | --- | --- | --- |

## 3. 产业链逐层下钻
| 层级 | 产品/工艺 | 龙头/供应商 | 价值占比 | 供给约束 | 替代路线 | 结论 |
| --- | --- | --- | --- | --- | --- | --- |

## 4. 四层物理约束校验
| 候选环节 | 寡头是谁 | 扩产周期 | 替代方案 | 下游刚需 | 是否卡口 |
| --- | --- | --- | --- | --- | --- |

## 5. 卡口公司评分
| 公司 | 代码 | 环节 | 卡口分 | 需求证据 | 供给刚性 | 误定价逻辑 | 催化剂 | 反证条件 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

## 6. 供需缺口模型
- 需求端变量:
- 供给端变量:
- 关键假设:
- 敏感性:
- 数据更新频率:

## 7. 跟踪清单
| 指标 | 来源 | 更新频率 | 多头信号 | 空头/反证信号 |
| --- | --- | --- | --- | --- |

## 8. 风险与仓位纪律
- 技术路线风险:
- 扩产超预期:
- 客户集中/认证失败:
- 估值透支:
- 流动性和小盘股波动:

## 9. 待核验事项
[列出不能确认、需要继续查证的事实]
```

## Evidence Rules

- Prefer primary sources: annual reports, prospectuses, exchange filings,
  earnings-call transcripts, investor-relations records, customer disclosures,
  regulator/industry-association documents, patents, product datasheets, and
  credible market-data providers.
- Use news, social posts, blogs, and community writeups only as discovery leads.
  Do not treat them as decisive evidence for capacity, customer relationships,
  or performance.
- For A-share exposure, verify with filings, official product pages, customer
  announcements, capacity disclosures, investor Q&A, patents/certifications, or
  credible third-party reports.
- For overseas stocks, use company filings, investor presentations, transcripts,
  SEC/SEDAR/EDINET/Companies House style filings where applicable.
- Time-sensitive facts require current verification: capacity, prices, market
  share, ownership, customer lists, sanctions, export controls, financials,
  stock prices, and valuation multiples.
- Explicitly label weak evidence as "待验证", "间接相关", or "概念关联".

## Risk Discipline

- Do not give personalized financial advice. Frame outputs as research,
  watchlists, and scenario analysis.
- Do not recommend buying because a name matches a hot concept. The company must
  have direct exposure to the bottleneck link and evidence of value capture.
- Separate "卡口资产", "重要配套", "普通受益", "间接概念", and "需排除".
- Always include thesis invalidation conditions. A bottleneck thesis without
  invalidation triggers is incomplete.
- Be especially cautious with small caps, low liquidity, OTC names, companies
  with frequent dilution, customer concentration, or governance concerns.
- If the user asks for buy points, valuation, target prices, or operations, run
  stock-level analysis after the bottleneck memo and mark it as a separate
  follow-through section.

## Automation With Codex/Claude Code

When the user asks to automate the method:

1. Create a `chain_map.json` with layers, suppliers, metrics, sources, and
   evidence strength.
2. Create a `tracking_config.yaml` with indicators, source URLs/APIs, update
   frequency, and alert thresholds.
3. Write scripts only after the research schema is clear. Avoid scraping
   websites aggressively; respect rate limits and terms.
4. Store outputs as dated reports: `serenity-research/<topic>-YYYY-MM-DD/`.
5. Generate:
   - `report.md` for human reading.
   - `source_data.json` for raw evidence and source trail.
   - `watchlist.csv` for companies and scores.
   - `tracking_config.yaml` for recurring updates.

Minimal data schema:

```json
{
  "theme": "AI optical interconnect",
  "as_of": "YYYY-MM-DD",
  "layers": [
    {
      "layer": "material",
      "link": "example bottleneck",
      "suppliers": [],
      "demand_driver": "",
      "supply_constraint": "",
      "substitution_risk": "",
      "evidence": []
    }
  ],
  "candidates": [
    {
      "company": "",
      "ticker": "",
      "link": "",
      "scores": {},
      "catalysts": [],
      "invalidation": []
    }
  ]
}
```

## Example Prompts This Skill Should Handle

- "按白毛股神的方法，帮我拆 AI 光模块上游还有哪些卡口。"
- "不要直接分析英伟达，沿 AI 算力产业链往上游找最难扩产的环节。"
- "用 Serenity 框架看人形机器人，哪些 A 股公司是真卡口不是概念股?"
- "把这个瓶颈卡口方法写成可每周自动更新的投研监控模型。"
- "我有一批供应链公司，帮我按不可替代、供给刚性、寡头、机构低配打分。"

