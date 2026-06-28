# A股复盘

A股复盘是一个面向低频研究的 A 股日报、收盘复盘、周度校准和产业链分析仓库。它把新闻事件、主线板块、资金方向、候选股票、量价确认、复盘回测和行业上下游研究沉淀成可审计的本地归档。

> 仅用于研究流程和复盘校准，不构成买卖、仓位、止损或目标价建议。

## 主要能力

- 生成每日 A 股新闻影响简报，按板块优先筛选主线和候选股。
- 通过 `integrated-stock-selection` 把日报主线、产业链卡口、基本面估值、量价资金和风险排除整合成研究股票池。
- 通过 `iwencai-trend-stock-pool` 将 `scripts/supermind` 的三日趋势承接策略转换成问财风格语句，并用公开数据生成分策略股票池。
- 在收盘后生成 `close_review.json`，复核大盘方向、板块命中、股票表现和偏差原因。
- 聚合周度复盘，输出有效信号、失效信号和下周筛选校准建议。
- 对归档日报做固定窗口回测和阈值扫描，辅助判断筛选条件是否需要调整。
- 生成行业上下游产业链分析，覆盖核心价值分布、上游材料/部件/制程挖掘、A股公司映射、交易跟踪和质量门禁。
- 通过 `web-apps/report/` 浏览日报、复盘、周报和产业链报告；产业链图表资源会同步到网页静态资源目录。
- 在 `scripts/a_share_data.py` 统一沉淀 A 股代码规范化、腾讯公开行情和东方财富公开行情适配，供自研 skill 复用。
- 通过 `scripts/stock_workbench.py` 一键启动统一工作台，集中访问综合选股、报告、股票分析、产业链报告、新闻看板和外部 web 应用。
- 通过 `harness/` 统一描述能力清单、运行 smoke/full/web 验证，并把报告输出到 `tmp/harness/`。

## 目录结构

```text
.
├── .agents/skills/
│   ├── daily-a-share-news-impact/      # 日报、复盘、回测和阈值扫描主流程
│   ├── integrated-stock-selection/     # 综合选股总控 skill
│   ├── iwencai-trend-stock-pool/       # Supermind/问财趋势承接股票池
│   ├── industry-chain-analysis/        # 行业上下游产业链分析 skill
│   ├── china-stock-analysis/           # A 股基础面、估值和公开行情补充
│   └── china-stock-price-analysis/     # 股价和相对估值分析辅助脚本
├── industry-analysis/                  # 产业链分析报告、源数据、质量报告和图表资产
├── local/
│   ├── YYYY-MM-DD/                     # 每日归档：input_bundle/assembled/report/close_review
│   └── reviews/                        # 周报、回测、阈值扫描和校准摘要
├── harness/                            # 能力清单和统一验证 runner
├── scripts/                            # 跨 skill 复用的公开数据适配和通用工具
│   ├── run_harness.py                  # harness 命令行入口
│   └── stock_workbench.py              # 一键启动本地统一工作台
├── tests/                              # 脚本单元测试
├── docs/                               # 架构、开发规范和 harness 指南
├── web-apps/
│   ├── report/                         # 可交互网页报告
│   └── vibe-trading/                   # 外部 web 应用 submodule
├── tmp/                                # 临时运行文件，不入库
└── pyproject.toml
```

## 环境准备

```bash
uv sync
```

或使用已有 Python 环境安装核心依赖：

```bash
pip install akshare baostock pandas numpy pytest
```

建议使用 Python 3.11+。部分公开行情接口可能受网络或证书环境影响；如遇 HTTPS 证书校验失败，可为命令临时设置 `SSL_CERT_FILE` 指向 `certifi` 的证书文件。

## 常用命令

统一验证：

```bash
uv run python scripts/run_harness.py --mode smoke
```

常用模式：

- `smoke`：提交前默认检查，覆盖能力路径、Python 入口编译和单元测试。
- `full`：在 smoke 基础上重建报告数据，适合报告/归档/产业链变更。
- `web`：在 smoke 基础上启动统一工作台并检查 API，适合 web 集成变更。

更多说明见 `docs/HARNESS.md`、`docs/DEVELOPMENT.md`、`docs/ARCHITECTURE.md` 和 `docs/CAPABILITY_GUIDE.md`。

启动统一工作台：

```bash
uv run python scripts/stock_workbench.py --open
```

后台启动和停止：

```bash
uv run python scripts/stock_workbench.py --daemon
uv run python scripts/stock_workbench.py --stop
```

默认会启动：

- `http://127.0.0.1:8788/`：统一工作台入口。
- `http://127.0.0.1:8788/api/health`：统一工作台与依赖服务健康检查。
- `http://127.0.0.1:8765/report/`：交互报告页。
- `http://127.0.0.1:8793/index.html`：投资资讯看板。
- `http://127.0.0.1:8088/home/`：Vibe-Trading Wiki 本地预览。
- `http://127.0.0.1:8899/health`：Vibe-Trading FastAPI 后端健康检查。
- `http://127.0.0.1:4173/`：Vibe-Trading 前端预览（需要该 submodule 已执行前后端依赖安装和前端构建）。

工作台运行股票分析或数据抓取时，输出文件写入 `tmp/workbench/`，不入库。

工作台里的“综合选股”页支持一键触发 `integrated-stock-selection`：先运行 `iwencai-trend-stock-pool` 生成趋势承接候选，再叠加本地日报、产业链、估值和风险证据，最后在网页上展示核心池、观察池、排除项和证据缺口。结果会先经过本地投委会规则初审；如果选择“Vibe 优先”且 Vibe-Trading 后端已配置 LLM API key，还会调用 `investment_committee` swarm 对前排候选做多智能体评审。选股 JSON 和 Markdown 报告会写入 `tmp/workbench/integrated_selection_*.json|md`，不入库。

生成综合选股池：

```bash
uv run python .agents/skills/integrated-stock-selection/scripts/run_integrated_selection.py \
  --date 2026-06-26 \
  --theme 存储芯片 \
  --format markdown \
  --output tmp/integrated-selection/storage-2026-06-26.md
```

默认会先运行 `iwencai-trend-stock-pool` 生成趋势承接候选，再叠加本地归档、产业链源数据和可选行情估值复核；需要当前行情/估值复核时再显式添加 `--refresh-quotes`。调试时可以用 `--iwencai-json <stock_pools.json>` 复用已有问财趋势池，或用 `--skip-iwencai` 只评估本地归档。

生成问财趋势承接股票池：

```bash
uv run python .agents/skills/iwencai-trend-stock-pool/scripts/build_stock_pools.py \
  --strategies main_theme,fund_flow,quality_trend \
  --max-stocks 300 \
  --output-dir tmp/stock_pools_smoke
```

该 skill 基于 `scripts/supermind/supermind_trend_support_3day.py` 的核心/卫星主题、趋势承接买点和高置信度三日上涨过滤；本地脚本用 AkShare 公开行情近似问财条件，运行缓存默认留在 `tmp/` 或被 `local/stock_pools/*/cache/` 忽略。

Vibe-Trading 首次使用建议用 Python 3.11 初始化后端环境：

```bash
cd web-apps/vibe-trading
/usr/local/bin/python3.11 -m venv .venv
.venv/bin/python -m pip install -U pip setuptools wheel
.venv/bin/python -m pip install -e .
cd frontend
npm ci
npm run build
```

`/health`、`/sessions` 和基础页面不需要 LLM API key；运行 Vibe 的 agent、swarm 或聊天研究任务时，需要按 `web-apps/vibe-trading/agent/.env.example` 创建 `agent/.env` 并配置 `LANGCHAIN_PROVIDER` 及对应密钥。

Vibe-Trading 的 Alpha Zoo 使用 `csi300` 时会优先读取本机 `a-data/` 缓存；当前默认识别仓库同级目录 `../a-data`。如果数据放在别处，可以启动前设置：

```bash
export VIBE_TRADING_A_DATA_DIR=/path/to/a-data
```

只有本地 `a-data` 不存在或缺历史行情时，才需要配置 `TUSHARE_TOKEN`。

生成日报：

```bash
python3 .agents/skills/daily-a-share-news-impact/scripts/run_daily_report.py \
  --bundle tmp/a-share-brief-bundle.json \
  --run-id 093000
```

聚合周度复盘：

```bash
python3 .agents/skills/daily-a-share-news-impact/scripts/review_archive.py \
  --frequency weekly \
  --start 2026-06-15 \
  --end 2026-06-18 \
  --output local/reviews/weekly/weekly_review_2026-06-15_2026-06-18.json
```

回测已归档报告：

```bash
python3 .agents/skills/daily-a-share-news-impact/scripts/backtest_archived_reports.py \
  --start 2026-06-15 \
  --end 2026-06-18 \
  --include-leaders \
  --horizon-trading-days 1 \
  --min-hit-return-pct 0.5 \
  --output local/reviews/backtests/backtest_2026-06-15_2026-06-18.json
```

扫描受益股筛选阈值：

```bash
python3 .agents/skills/daily-a-share-news-impact/scripts/scan_selection_thresholds.py \
  --backtest local/reviews/backtests/backtest_candidate_pool_horizon1_min_hit_0p5_2026-06-15_2026-06-18.json \
  --role-scope beneficiary \
  --output local/reviews/threshold_scans/threshold_scan_beneficiary_2026-06-15_2026-06-18.json
```

生成交互网页报告数据：

```bash
uv run python web-apps/report/build_data.py
```

该命令会读取 `local/` 和 `industry-analysis/`，并把产业链报告图片复制到 `web-apps/report/industry-assets/`，确保按 `web-apps/report` 目录启动服务时图片也能显示。

启动本地网页服务：

```bash
python3 -m http.server 8765 --directory web-apps/report
```

访问报告页：

```text
http://localhost:8765/report/
```

根路径 `http://localhost:8765/` 只显示入口页，不直接进入报告。报告页左侧可切换“日报 / 复盘 / 周报 / 产业链”。

运行测试：

```bash
pytest
```

## 归档口径

- `local/YYYY-MM-DD/` 保存每日最新归档。
- `local/YYYY-MM-DD/runs/<run-id>/` 保存同一日期多次运行的审计记录。
- `local/reviews/weekly/` 保存周度复盘。
- `local/reviews/backtests/` 保存回测结果。
- `local/reviews/threshold_scans/` 保存阈值扫描结果。
- `industry-analysis/<topic>-<date>/` 保存产业链报告；静态图片统一在该目录的 `assets/` 下，报告内使用相对路径引用。

生产阈值调整应基于多日或多周回测证据，不应只根据单日偏差修改。
