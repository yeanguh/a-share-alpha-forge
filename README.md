# A股复盘

A股复盘是一个面向低频研究的 A 股日报、收盘复盘、周度校准和产业链分析仓库。它把新闻事件、主线板块、资金方向、候选股票、量价确认、复盘回测和行业上下游研究沉淀成可审计的本地归档。

> 仅用于研究流程和复盘校准，不构成买卖、仓位、止损或目标价建议。

## 主要能力

- 生成每日 A 股新闻影响简报，按板块优先筛选主线和候选股。
- 在收盘后生成 `close_review.json`，复核大盘方向、板块命中、股票表现和偏差原因。
- 聚合周度复盘，输出有效信号、失效信号和下周筛选校准建议。
- 对归档日报做固定窗口回测和阈值扫描，辅助判断筛选条件是否需要调整。
- 生成行业上下游产业链分析，覆盖核心价值分布、上游材料/部件/制程挖掘、A股公司映射、交易跟踪和质量门禁。
- 通过 `web-report/` 浏览日报、复盘、周报和产业链报告；产业链图表资源会同步到网页静态资源目录。

## 目录结构

```text
.
├── .agents/skills/
│   ├── daily-a-share-news-impact/      # 日报、复盘、回测和阈值扫描主流程
│   ├── industry-chain-analysis/        # 行业上下游产业链分析 skill
│   ├── china-stock-analysis/           # A 股基础面、估值和公开行情补充
│   └── china-stock-price-analysis/     # 股价和相对估值分析辅助脚本
├── industry-analysis/                  # 产业链分析报告、源数据、质量报告和图表资产
├── local/
│   ├── YYYY-MM-DD/                     # 每日归档：input_bundle/assembled/report/close_review
│   └── reviews/                        # 周报、回测、阈值扫描和校准摘要
├── tests/                              # 脚本单元测试
├── web-report/                         # 可交互网页报告
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
python3 web-report/build_data.py
```

该命令会读取 `local/` 和 `industry-analysis/`，并把产业链报告图片复制到 `web-report/industry-assets/`，确保按 `web-report` 目录启动服务时图片也能显示。

启动本地网页服务：

```bash
python3 -m http.server 8765 --directory web-report
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
