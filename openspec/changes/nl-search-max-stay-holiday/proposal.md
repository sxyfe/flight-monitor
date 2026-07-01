## Why

nl-search 表单目前仅有 `min_stay_days`（最少停留），无法表达「最多玩 N 天」的行程约束；同时 AGENTS.md 要求日历采用 Element UI 风格且国庆核心周需高亮，但 v3 改用原生 `<input type="date">` 后该能力缺失。用户已确认：**新增 max_stay_days**、**不改为 Popover 整框日历**、**国庆高亮必须做**。

## What Changes

- 在 `SearchIntent` 与校验/穷举引擎中新增可选字段 `max_stay_days`（整数，null 表示不限制）
- 表单 Tab 新增「最多停留（天）」输入框，与现有「最少停留」「最高价格」并排展示
- NL 解析（规则 + LLM schema）支持「最多玩 N 天 / 不超过 N 天」等表述
- 查询字符串生成与暖色报告 meta 展示 `max_stay_days`
- 在**不替换**原生日期 input 的前提下，于日期控件下方增加**只读参考月历**，高亮当年 future-valid 国庆核心周（10-01~10-07），并叠加用户已选出发日期范围
- Skill 侧 `flight_search_engine.py`、`nl_parser.py`、`search_intent.schema.json` 与 monorepo `scripts/` 保持同步

## Capabilities

### New Capabilities

- `max-stay-constraint`：`max_stay_days` 字段、校验、日期对过滤、NL 解析与报告 meta

### Modified Capabilities

- `nl-search-ui`：表单新增最多停留输入；日期区增加国庆核心周只读高亮参考月历（原生 date input 不变）
- `flight-search-engine`：`valid_date_pairs` 与 `validate_intent` 支持 max stay
- `nl-query-parser`：schema 与规则回退解析 `max_stay_days`

## Impact

- `scripts/flight_search_engine.py`（及 Skill 镜像）
- `web/nl-search/static/intent-editor.js`、`intent-query.js`、`ui/components.js`、`ui/tokens.css`
- `.cursor/skills/flight-monitor-agent/scripts/nl_parser.py`、`search_intent.schema.json`
- `web/nl-search/static/report/report.js`、`report-bridge.js`（meta 展示）
- 无 API 路径变更；`POST /api/intent/parse|validate|search` 的 intent JSON 多一可选字段
