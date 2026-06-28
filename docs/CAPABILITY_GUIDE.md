# 能力使用指南

这份指南用于选择仓库里的能力入口。所有输出都只用于研究和复盘，不构成买卖、仓位、止损或目标价建议。

## 快速选择

| 需求 | 首选能力 | 入口 |
| --- | --- | --- |
| 看某天日报、复盘、周报 | 交互报告 | `uv run python scripts/stock_workbench.py --open` |
| 跑统一网页入口 | 工作台 | `uv run python scripts/stock_workbench.py --open` |
| 生成综合选股池 | `integrated-stock-selection` | `.agents/skills/integrated-stock-selection/scripts/run_integrated_selection.py` |
| 生成或复核 A 股日报 | `daily-a-share-news-impact` | `.agents/skills/daily-a-share-news-impact/` |
| 分析某只股票价格和估值 | `china-stock-price-analysis` | 工作台“股票分析”或 `stock_analyze.py` |
| 抓基础面、财务、估值数据 | `china-stock-analysis` | `.agents/skills/china-stock-analysis/scripts/` |
| 做产业链上下游分析 | `industry-chain-analysis` | `.agents/skills/industry-chain-analysis/` |
| 找上游瓶颈、卡口、隐形供应商 | `serenity-bottleneck-investing` | `.agents/skills/serenity-bottleneck-investing/` |
| 看赛道新闻 | `investment-news` | 工作台“新闻搜索”或 `http://127.0.0.1:8793/index.html` |
| 使用开源全栈数据方法 | `a-stock-data` | `.agents/skills/a-stock-data/SKILL.md` |
| 使用 Vibe-Trading 外部应用 | `vibe-trading` | 工作台或 `web-apps/vibe-trading/` submodule |

## 推荐工作流

### 每日复盘

1. 打开工作台：`uv run python scripts/stock_workbench.py --open`。
2. 在“新闻搜索”刷新资讯，看赛道热度。
3. 在“日期报告”查看最新日报和收盘复盘。
4. 如需生成新日报，按 `daily-a-share-news-impact` 的 `SKILL.md` 准备 bundle 并运行脚本。
5. 运行 `uv run python scripts/run_harness.py --mode smoke` 确认核心能力没有被改坏。

### 综合选股

1. 先用 `integrated-stock-selection` 从最新日报归档生成候选池。
2. 如果用户给了主题，用 `--theme` 限定主线，并自动叠加已有产业链报告映射。
3. 核心池只保留已通过日报门禁、量价/资金确认较强且风险未触发排除的股票；观察池保留缺产业链证据、估值过高或趋势确认不足的股票。
4. 需要当前行情时再加 `--refresh-quotes`，临时快照会写到 `tmp/integrated-selection/`。

示例：

```bash
uv run python .agents/skills/integrated-stock-selection/scripts/run_integrated_selection.py \
  --date 2026-06-26 \
  --theme 存储芯片 \
  --format markdown \
  --output tmp/integrated-selection/storage-2026-06-26.md
```

### 个股研究

1. 先用工作台“股票分析”做实时股价和估值快跑。
2. 需要更完整基础面时，运行 `china-stock-analysis/scripts/data_fetcher.py`。
3. 若个股来自某个主题，先用日报或产业链报告确认板块强度和事件传导，不把单股估值孤立使用。
4. 运行产物写入 `tmp/`，正式结论再归档到合适目录。

### 产业链研究

1. 用 `industry-chain-analysis` 先做通用上下游和 A 股映射。
2. 如果问题是“谁在供给瓶颈上最稀缺”，再叠加 `serenity-bottleneck-investing`。
3. 报告必须保留来源、置信度、质量检查和图片资源。
4. 生成后的报告放入 `industry-analysis/<topic>-<date>/`。
5. 跑 `uv run python scripts/run_harness.py --mode full` 确认报告静态数据能重建。

## 质量门禁

- 能力入口必须记录在 `harness/manifest.json`。
- 新脚本必须能被 `python -m py_compile` 编译。
- 涉及数据抓取必须有超时、降级和错误说明。
- 真实数据接口不稳定时，不要把失败包装成确定结论。
- 运行输出默认放 `tmp/`，除非是明确的归档产物。

## 常见问题

### 什么时候用 full？

改了报告构建、归档结构、产业链报告格式、质量检查或会影响 `web-apps/report/data.js` 的逻辑时，用 `full`。

### 什么时候用 web？

改了 `scripts/stock_workbench.py`、web 应用集成、端口、API 或工作台页面时，用 `web`。

### 如何后台运行统一入口？

用 `uv run python scripts/stock_workbench.py --daemon` 启动，用 `uv run python scripts/stock_workbench.py --stop` 停止。运行状态看 `http://127.0.0.1:8788/api/health`。

### Vibe-Trading 500 怎么判断？

先看 `http://127.0.0.1:8899/health`。如果后端没起来，前端 `/sessions` 会通过 Vite/preview 代理失败并表现为 500；这通常是后端 venv 缺依赖或没有启动，不是 `/sessions` 本身要求 API key。只有聊天、agent、swarm 等 LLM 研究任务需要在 `web-apps/vibe-trading/agent/.env` 配置 provider/key。

### Vibe-Trading 为什么还要 Tushare？

Alpha Zoo 的 `csi300` 以前默认走 Tushare。当前集成已改为先读本机 `a-data/`，默认位置是 `stock-analysis` 同级的 `a-data`。如果你的数据目录不在默认位置，设置 `VIBE_TRADING_A_DATA_DIR=/path/to/a-data` 后重启 Vibe 后端即可；只有本地数据不可用时才需要 `TUSHARE_TOKEN`。

### 开源 skill 和自研 skill 重合怎么办？

开源 skill 优先作为数据源和方法参考；自研 skill 负责本仓库的归档、质量门禁、报告模板和可审计流程。不要直接把开源仓库的运行缓存或生成数据提交进主仓库。
