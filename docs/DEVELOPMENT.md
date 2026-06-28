# 开发规范

## 提交流程

1. 先确认工作树：`git status --short`。
2. 开发源码、文档或配置时保持变更批次清晰，不把运行数据混入同一提交。
3. 提交前运行：`uv run python scripts/run_harness.py --mode smoke`。
4. 修改 web 工作台或报告页时追加：`uv run python scripts/run_harness.py --mode web`。
5. 修改报告构建、归档或产业链输出时追加：`uv run python scripts/run_harness.py --mode full`。

## 临时文件

- 允许写入：`tmp/`、`.pytest_cache/`、`.playwright-cli/`、`__pycache__/`。
- 禁止提交：cache、截图、临时报表、真实接口抓取中间文件、`.DS_Store`。
- 如果测试命令更新了 `web-apps/report/data.js` 或开源子仓库的数据文件，除非本次目标就是同步数据，否则提交前恢复。

## 新增 skill

新增 skill 时至少包含：

- `.agents/skills/<skill>/SKILL.md`
- `description` 元数据，说明触发场景和边界
- 脚本入口放在 `.agents/skills/<skill>/scripts/`
- 参考资料放在 `.agents/skills/<skill>/references/`
- 模板放在 `.agents/skills/<skill>/templates/`

完成后更新 `harness/manifest.json` 的 `capabilities`，把可编译脚本放入 `entrypoints`。

## 新增 web 应用

- 自研 web 应用放在 `web-apps/<name>/`。
- 外部 web 应用使用 submodule，避免复制源码。
- 必须在 `README.md` 或 `docs/` 说明启动方式、端口、依赖和已知限制。
- 如需统一入口，把服务加入 `scripts/stock_workbench.py`，把健康检查加入 `harness/manifest.json`。
- 外部 web 应用如果有前后端拆分，工作台必须分别建模前端、后端和健康检查，避免只启动前端导致代理端点 500。

## Python 约定

- 默认 Python 3.11+。
- Vibe-Trading 后端单独使用 `web-apps/vibe-trading/.venv`，优先用 Python 3.11 创建；该目录是本机依赖环境，不入库。
- 首选标准库；已有依赖在 `pyproject.toml` 中声明。
- 脚本必须支持从仓库根目录运行。
- 文件输出必须可配置，默认不要写仓库根目录。
- 对真实网络接口保持超时、降级和清晰错误信息。

## 验证分级

| 等级 | 命令 | 适用场景 |
| --- | --- | --- |
| smoke | `uv run python scripts/run_harness.py --mode smoke` | 常规提交前，覆盖路径、编译和单元测试。 |
| full | `uv run python scripts/run_harness.py --mode full` | 改归档、报告构建、核心脚本时。 |
| web | `uv run python scripts/run_harness.py --mode web` | 改工作台、web 入口或服务集成时。 |

Harness 输出写入 `tmp/harness/`，可以用最新的 Markdown 报告快速查看失败原因。
