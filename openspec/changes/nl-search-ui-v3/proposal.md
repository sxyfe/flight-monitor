## Why

nl-search 表单依赖 Element Plus，视觉与 AI 工具常见界面不一致；结果区为三 Tab 自研图表，与 flight-monitor-agent 暖色报告模板脱节。用户需要在表单中使用更紧凑的 shadcn 风格组件、用查询字符串替代 JSON 编辑，并将搜索结果对齐 Skill 报告体验。

## What Changes

- 移除 Element Plus，新增 shadcn 风格轻量 Vue 组件层（CDN，无 Vite 构建）
- 国家多选与出发日期范围紧凑布局（同行、限宽）
- SearchIntent JSON 改为可编辑查询字符串，支持「重新解析」
- 结果区复用 flight-monitor-agent `templates/report/` 暖色报告布局与交互
- NL Tab 增加 LLM 解析提示；设置页增加 Key 本地存储隐私说明
- supersede `nl-search-intent-editor-v2` 中 Element Plus 决策（D1）

## Capabilities

### Modified Capabilities

- `nl-search-ui`：组件库、查询字符串、报告布局、文案

## Impact

- `web/nl-search/static/**`
- `web/nl-search/README.md`

## Non-Goals

- 不迁移整站 Vite SPA
- 不修改 `flight_search_engine.py` 搜索算法
- 不修改 Skill 侧 `generate_flight_report.py` 生成逻辑
