# A股数据源模块矩阵

这份矩阵是 `.agents` 下股票相关 skill 的统一口径。原则是：可通的数据源不删除，按模块降级；不可用、缺凭证或付费源不进入默认链路，只在用户明确启用或补齐凭证后使用。

## 模块优先级

| 模块 | 主渠道 | 备用/降级渠道 | 当前处理 |
| --- | --- | --- | --- |
| 实时行情、成交、盘口、K线 | 通达讯 `mootdx` | 腾讯公开行情、东方财富公开行情、Sina公开行情、Baostock历史K线 | `mootdx` 优先；腾讯用于无密钥兜底和市值字段；东方财富补 PE/PB/市值；Sina 只做低优先级交叉校验。 |
| 估值指标 PE/PB/市值 | 腾讯财经、东方财富公开行情 | AKShare估值/财务接口、通达讯行情字段 | 估值用腾讯/东方财富互补；行情脚本先填通达讯价格，再用腾讯/东方财富补估值。 |
| 研报 | AKShare东财研报接口 | 艾问财/iwencai API Key配置后做自然语言跨主题搜索；用户手工导出的问财结果 | 默认 AKShare；`IWENCAI_API_KEY` 未配置时不阻塞，只保留问财语句和本地二次过滤。 |
| 新闻 | AKShare个股新闻、财联社快讯、全球资讯 | 财联社/财新/路透/交易所/部委等权威网页核验 | AKShare做批量入口；重大事件必须用权威来源交叉确认。 |
| 基础数据/财务快照/公司资料 | 通达讯、AKShare CNINFO/东财接口 | 腾讯/东方财富行情快照、Baostock股票基础信息 | 公司资料以巨潮/CNINFO为准；通达讯补行情和基础快照；AKShare schema变化时降级到 CNINFO+腾讯。 |
| 公告 | 巨潮/CNINFO（AKShare封装） | AKShare东方财富个股公告、通达讯公告摘要 | 巨潮为原始权威；AKShare封装优先；通达讯摘要只做发现线索。 |
| 产业链/A股映射 | 公司公告、年报、招股书、官网/IR、协会/监管 | AKShare板块成分、概念成分、efinance/baostock/adata、SEC EDGAR | 板块/概念只用于发现候选，不能直接证明业务暴露。 |

## 运行降级规则

1. 每次完整报告前运行健康检查：

```bash
uv run python .agents/skills/daily-a-share-news-impact/scripts/check_optional_data_sources.py \
  --akshare-code 600519 \
  --akshare-data-type basic \
  --quote-code 600519
```

2. 查看输出里的 `module_health`，按模块选第一个 `available` 渠道。模块 `usable=false` 时，报告必须把该模块标为 `limited`，不要伪造定量结论。
3. 同一模块有两个以上可用源时，重要字段要交叉校验；如果数值冲突，优先使用更贴近该模块主职责的源，并在 `evidence_gaps` 里记录差异。
4. 缺凭证源（例如 `IWENCAI_API_KEY`、`ITICK_API_TOKEN`、`ZHITU_API_TOKEN`）保留在低优先级备用链路，不进入默认结论。
5. 付费源（QVeris、Tushare Pro、终端行情等）不进入默认链路；用户明确要求后再用 `--include-paid` 探测并披露。

## 当前目标链路

- 行情：`mootdx` -> 腾讯 -> 东方财富 -> Sina/Baostock。
- 研报：AKShare -> iwencai（需 Key）-> 手工问财导出二次过滤。
- 新闻：AKShare -> 财联社/财新/路透/官方来源核验。
- 基础数据：通达讯+AKShare CNINFO -> 腾讯/东方财富补估值和市值。
- 公告：巨潮/CNINFO（AKShare封装）-> 东方财富公告 -> 通达讯公告摘要。
