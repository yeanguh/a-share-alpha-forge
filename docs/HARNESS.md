# Harness 指南

Harness 是本仓库的统一验证工程，用来回答三个问题：

- 当前能力清单是否完整。
- 核心脚本、测试和报告构建是否还能跑。
- 本地工作台和 web 入口是否能返回健康响应。

## 命令

列出能力和检查项：

```bash
uv run python scripts/run_harness.py --list
```

提交前 smoke：

```bash
uv run python scripts/run_harness.py --mode smoke
```

报告构建和归档相关变更：

```bash
uv run python scripts/run_harness.py --mode full
```

工作台或 web 集成变更：

```bash
uv run python scripts/run_harness.py --mode web
```

只运行单个检查：

```bash
uv run python scripts/run_harness.py --mode smoke --check manifest.paths
```

## 输出

每次运行会写入：

- `tmp/harness/harness_<mode>_<timestamp>.json`
- `tmp/harness/harness_<mode>_<timestamp>.md`
- `tmp/harness/harness_<mode>_latest.json`
- `tmp/harness/harness_<mode>_latest.md`

这些都是运行产物，不提交。

## Manifest

能力和检查定义在 `harness/manifest.json`。

能力字段：

- `id`：稳定标识。
- `type`：`skill`、`skill-web`、`web-app`、`tool` 或 `submodule-web-app`。
- `path`：相对仓库根目录的路径。
- `summary`：能力说明。
- `entrypoints`：可编译或可运行的入口脚本。

检查字段：

- `paths`：检查路径存在。
- `py_compile`：编译 Python 入口。
- `command`：运行命令，例如 `pytest` 或报告构建。
- `workbench`：启动工作台并访问 JSON API。

## 接入新能力

1. 先把 skill、脚本或 web 应用放到正确目录。
2. 在 `harness/manifest.json` 增加 capability。
3. 把 Python 入口加入 `entrypoints`。
4. 如果能力有稳定命令，增加 `command` 类型检查。
5. 运行 `uv run python scripts/run_harness.py --mode smoke`。
