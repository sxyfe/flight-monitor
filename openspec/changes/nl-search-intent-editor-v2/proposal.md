## Why

`nl-flight-search-web`（v1）已交付可用的 NL 查票原型，但结构化意图编辑区仍是 MVP 级纯文本表单：原生日期控件、逗号分隔城市/国家、只读 JSON、国庆日期未做 future-aware 解析。用户难以直观修正解析结果，也无法在「说人话」与「填表单」两种路径间顺畅切换。需要在 v1 基础上升级意图编辑体验，降低查票前的确认成本，并统一国庆/国庆前后的日期语义。

## What Changes

- 页面拆为 **双模式 Tab**：「自然语言查询」与「表单查询」；NL 解析成功后自动切至表单 Tab 并预填字段。
- 表单区引入 **Vue3 + Element Plus**（CDN 局部 mount）：日期范围选择器、国家多选、行程类型（往返 / 开口程）独立勾选、可编辑 JSON textarea。
- **出发地**与**目的地**均支持中文机场搜索（RollingGo `airportsearch`），选后以标签展示 IATA 编码。
- 新增 **「确认」按钮**：按 dirty 优先级（JSON dirty 优先于表单）合并为单一 `SearchIntent`，双向刷新表单与 JSON，并触发校验与查询量预估；「开始搜索」仅使用确认后的 Intent。
- 设置面板 API Key 输入增加 **👁 明文切换**。
- NL 解析层更新国庆语义：**「国庆」→ 10-01 ~ 10-07**；**「国庆前后」→ 09-28 ~ 10-10**；窗口须解析为未来有效日期（若当年窗口已过则取次年）。
- 新增后端 API：`GET /api/airport/search`、`POST /api/intent/validate`。
- **不**在本变更中实现：Tauri 集成、整站迁移至 Vite 构建链、替换 v1 结果表格/图表逻辑。

## Capabilities

### New Capabilities

（无独立新 capability；本变更扩展 v1 已有能力。）

### Modified Capabilities

- `nl-query-parser`：国庆/国庆前后 future-aware 日期窗；LLM prompt 同步更新
- `nl-search-ui`：双 Tab 模式、Element Plus 意图编辑器、确认双向同步、机场搜索选择器、Key 明文切换
- `nl-search-api`：机场搜索与 intent 校验端点

## Impact

- **修改代码**：`web/nl-search/static/index.html`（Tab 布局 + Vue mount 点）、新增 `web/nl-search/static/intent-editor/` 或内联 Vue 组件、`web/nl-search/server.py`、`web/nl-search/nl_parser.py`；可选新增 `scripts/holiday_windows.py`
- **新增依赖（前端 CDN）**：Vue 3、Element Plus、Element Plus 中文 locale
- **不受影响**：`scripts/flight_search_engine.py` 核心搜索逻辑、`exhaustive_search.py` 穷举 CLI 硬编码日期窗、Tauri 桌面端
- **用户可见行为变化**：解析「国庆前后」默认日期窗由 v1 的 `09-25~10-07` 改为 `09-28~10-10`；仅说「国庆」时为 `10-01~10-07`
