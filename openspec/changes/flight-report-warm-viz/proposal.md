## Why

Skill 现有 HTML 报告仅含 demo-bilibili 风格的分 Tab 分页表格，缺少 exhaustive-viz 的侧栏筛选、Chart.js 五图与排序能力。用户希望合并二者交互控件，采用暖色编辑风，统一表格全量分页。

## What Changes

- `generate_flight_report.py` 重构：模板化输出，内嵌 JSON + 暖色 CSS/JS
- 新增 `templates/report/`（report.html、report.css、report.js）
- 侧栏筛选（行程/国家/目的地/出发地/价格区间/bucket）+ Chart.js 五图 + 排序 + 统一分页（含页码跳转）
- 移除往返/开口程分 Tab 双 pager（由侧栏行程 Tab 替代）
- 更新 SKILL.md、README.md；增量修正 flight-monitor-agent-oss 报告 spec

## Capabilities

### New Capabilities

- `flight-report-warm-viz`：暖色统一报告 UI 规范

### Modified Capabilities

- `flight-monitor-agent-oss`：报告分页 requirement 由「分 Tab」改为「侧栏筛选 + 统一表格分页」

## Impact

- `.cursor/skills/flight-monitor-agent/scripts/generate_flight_report.py`
- `.cursor/skills/flight-monitor-agent/templates/report/`
- Skill 文档

## Non-Goals

- 不修改 `web/exhaustive-viz/` 本体
- 不恢复监控推荐块
- 不采用暗色雷达主题
