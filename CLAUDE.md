# CLAUDE.md

本文件为 Claude Code 在本仓库工作时的指引。

## 交互约定

- **请始终使用简体中文与我对话。**
- 回答保持**专业、简洁**，优先给出结论，再按需展开。
- 本仓库仅用于研究流程与复盘校准，不构成任何买卖、仓位、止损或目标价建议。

## 项目概述

A股复盘（`stock-analysis`）是一个面向低频研究的 A 股日报、收盘复盘、周度校准和产业链分析仓库，把新闻事件、主线板块、资金方向、候选股票、量价确认、复盘回测和行业上下游研究沉淀成可审计的本地归档。

## 目录结构

```text
.
├── .agents/skills/       # 各研究 skill（日报/综合选股/趋势股票池/产业链/基础面/股价）
├── industry-analysis/    # 产业链分析报告、源数据、质量报告和图表资产
├── local/                # 每日归档（YYYY-MM-DD）与 reviews 周报/回测/校准
├── harness/              # 能力清单 manifest.json 与统一验证 runner
├── scripts/              # 跨 skill 复用的公开数据适配与通用工具
├── tests/                # 脚本单元测试（pytest）
├── docs/                 # 架构、开发规范和 harness 指南
├── web-apps/             # report/（网页报告）与 vibe-trading/（外部 submodule）
└── pyproject.toml
```

## 环境与依赖

- Python 版本：`>=3.11`（`.python-version` 固定 3.11）。
- 依赖管理：**uv**（存在 `uv.lock`，请勿手动改锁文件）。
- 环境准备：`uv sync`（按 uv.lock 精确还原环境）。
- 核心依赖：`akshare`、`baostock`、`adata`、`efinance`、`mootdx`（行情数据源），`pandas`、`numpy`（数据处理），`backtrader`、`pyfolio`（回测/绩效），`pdfplumber`、`pypdf`、`cairosvg`（文档/图表）。
- 开发依赖（dev group）：`pytest`、`pyyaml`。

## 常用命令

```bash
uv run pytest                                       # 运行测试
uv run python scripts/run_harness.py --mode smoke   # 冒烟验证
uv run python scripts/run_harness.py --mode full    # 完整验证
uv run python scripts/run_harness.py --mode web     # web 校验
uv run python scripts/stock_workbench.py            # 启动本地统一工作台
```

## 开发约定

- 公开行情适配统一沉淀在 `scripts/a_share_data.py`，供各 skill 复用；新增数据源在此扩展，勿在 skill 内散落实现。
- K 线数据须保持复权口径一致（前复权 qfq 与不复权 day 不可混用于同一回测）。
- 修改脚本后至少运行 `pytest` 与 `run_harness.py --mode smoke` 自测。
- `tmp/` 为临时运行产物，不入库；`local/` 为归档结果。
