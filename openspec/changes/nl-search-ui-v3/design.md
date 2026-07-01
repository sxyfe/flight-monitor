## Context

v2 意图编辑器采用 Vue3 + Element Plus CDN。v3 用户反馈组件不美观，并要求结果报告完全对齐 Skill 暖色模板。

## Decisions

### D1: shadcn 风格轻量组件（非 shadcn-vue 构建）

新增 `static/ui/tokens.css` + `components.js`，用 CSS 变量与原生控件实现 Input、MultiSelect、DateRange、Checkbox、Button、Badge。保持 CDN 架构。

### D2: 查询字符串双向流

- 表单变更 → 自动 `intentToQueryString`，清除 queryDirty
- 用户编辑查询句 → queryDirty=true
- 「重新解析」→ POST `/api/intent/parse`
- 「确认意图」→ 以表单合成 Intent；queryDirty 未解析时阻止

### D3: 报告模板 vend

从 `.cursor/skills/flight-monitor-agent/templates/report/` 复制到 `static/report/`，CSS 根选择器改为 `.nl-report`。`report.js` 导出 `window.ReportApp.init(data)`；`report-bridge.js` 归一化 SSE offers 并构建 payload。

### D4: 移除 results-filter / 三 Tab 结果区

筛选由报告侧栏 chip 接管；删除 Element Plus 结果筛选 mount。

## Risks

| 风险 | 缓解 |
|------|------|
| report 与 nl-search offer 字段差异 | report-bridge 复用 `offer_to_client` 规则 |
| 模板分叉 | 文件头注释同步来源 |
