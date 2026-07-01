## Why

B 站推广视频需要演示「自然语言 → 查价/读缓存 → HTML 报告 → 桌面监控」闭环，但 Agent 缺少固化工作流与域知识。需新增**操作型** Skill 与报告生成脚本，与视频分镜/旁白严格分离。

## What Changes

- 新增 `.cursor/skills/flight-monitor-agent/SKILL.md`：查价、读 JSON 缓存、穷举/MCP 决策、监控规则建议
- 新增 `scripts/generate_flight_report.py`：从 `exhaustive_results.json` 生成 `output/reports/<run-id>/report.html`
- 新增 `docs/video-bilibili-monitor.md`：旁白与 Agent 演示台词（**不**写入 Skill）
- 报告页复用 `flight_search_engine.aggregate()` 与中文路线格式；轻量 CSS，无 shadcn/React 构建链

## Capabilities

### New Capabilities

- `flight-monitor-agent`：Agent 查价/缓存/报告/监控建议工作流

### Modified Capabilities

（无）

## Impact

- **新增**：`.cursor/skills/flight-monitor-agent/`、`scripts/generate_flight_report.py`、`docs/video-bilibili-monitor.md`、`output/reports/`
- **复用**：`scripts/flight_search_engine.py`、`scripts/exhaustive_results.json`
- **不受影响**：Tauri 桌面端核心、nl-search、xhs-cards 营销资产

## Non-Goals

- Skill 内嵌视频分镜、旁白、slides、storyboard
- shadcn 推广站或 16:9 slides
- 将 xhs-cards 生成逻辑并入本 Skill
- 分析缓存场景无谓调用 RollingGo API
