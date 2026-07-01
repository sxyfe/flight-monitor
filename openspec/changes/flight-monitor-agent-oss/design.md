## Context

Skill 位于 `.cursor/skills/flight-monitor-agent/`，当前通过 `_project.py` 引用 monorepo 引擎。计划开源为独立仓库，面向国际 MCP 社区，纯查价 + HTML 报告。

## Goals / Non-Goals

**Goals:**

- 独立仓库可 clone 即用，Python 3.8+ 无 monorepo 依赖
- Key 申请统一 rollinggo.store；配置经 `.env` / 环境变量
- smart / exhaustive 双模式 + 预估次数/耗时 + 用户确认
- SKILL 中文、README 中英双语；反滥用声明

**Non-Goals:**

- Flight Monitor 桌面端、监控规则、飞书通知
- 读历史穷举 JSON 作为查价结果

## Decisions

### 1. 配置加载 [`scripts/config.py`]

优先级：环境变量 `ROLLINGGO_API_KEY` > 仓库根 `.env` > `~/.cursor/mcp.json`（开发回退）。

无 Key 时 CLI exit 1，输出 rollinggo.store 链接与 `.env.example` 说明。

### 2. 查价 CLI [`run_search.py`]

- `--mode smart|exhaustive` 传入 `flight_search_engine.search(mode=...)`
- 预估耗时：`ceil(queries / CONCURRENCY) * 1.0` 秒（近似）
- `queries > HIGH_COST_THRESHOLD(500)` 且无 `--confirm` 则拒绝执行

### 3. 开口程

去程 A→B、返程 C→D；A/D ∈ origins，B/C ∈ destinations。引擎逻辑不变。

### 4. 报告

`generate_flight_report.py` 移除 `monitor_suggestion`；保留客户端分页与页码跳转。

### 5. 仓库关系

Phase 1：monorepo 内实现；Phase 2：push 至独立 GitHub repo，monorepo README 链接外部仓库。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 双份 engine 漂移 | vendored 单源；文档注明 sync |
| smart 仍 >500 次 | 按选定模式 queries 判断 confirm |
| API 间歇失败 | check_rollinggo + README Troubleshooting |
