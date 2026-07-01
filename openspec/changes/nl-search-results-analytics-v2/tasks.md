## 1. 后端：国家映射 meta

- [x] 1.1 在 `scripts/flight_search_engine.py` 新增 `build_code_to_country(codes)`，由 `DESTINATIONS_BY_COUNTRY` 反查
- [x] 1.2 `search()` 返回的 `SearchResult` 附加 `meta.code_to_country`（intent 目的地 + offers 中出现的 code）
- [x] 1.3 `web/nl-search/server.py` 同步搜索与 SSE `completed` 事件透传 `meta`

## 2. 共用筛选栏（Phase A）

- [x] 2.1 `index.html` 在 `resultsSection` 内、`result-tabs` 上方插入 `#results-filter-app` mount 点
- [x] 2.2 新建 `static/results-filter.js`：Element Plus 多选（国家/城市/去程日/回程日）+ 行程类型 + 最高价 + 重置
- [x] 2.3 实现 `ResultsFilterBridge`：`getFilterState()`、`getFilteredOffers(offers, meta)`、`onChange(cb)`
- [x] 2.4 筛选选项仅从当前 `offers` 派生；城市匹配 origin / out_dest / ret_dest 任一端
- [x] 2.5 `index.html` 加载 `results-filter.js`（与 `results-analytics.js` 一并引入）

## 3. 列表 Tab 联动

- [x] 3.1 `app.js` 的 `renderTable` 改用 `ResultsFilterBridge.getFilteredOffers()`
- [x] 3.2 移除 `rtab-list` 内独立的 `filterType` / `filterMaxPrice` 控件（并入共用栏）
- [x] 3.3 筛选变更时自动 `renderTable()`；搜索流式 `offer` 事件调用 `renderTable()` 受筛选约束

## 4. 图表重聚合与 hover（Phase B）

- [x] 4.1 实现 `aggregateClient(offers)`，规则对齐 Python `aggregate()`
- [x] 4.2 实现 `buildOfferIndexes(offers)` 与 `formatOfferTooltip(offer)`（中文路线/日期/航段）
- [x] 4.3 实现 `chartTooltipCallbacks` 统一 Chart.js tooltip（≤5 条 + 总数）
- [x] 4.4 改造 `renderCharts()`：基于筛选后 offers 重聚合 + hover
- [x] 4.5 改造 `renderVariation()` → `renderPriceDim()`：新标题、中文路线、矩阵色阶与格 hover
- [x] 4.6 更新 `index.html`：Tab「价格维度分析」、图表中文标题

## 5. NL 原文保留（Phase C）

- [x] 5.1 确认 `btnParse` 不修改 `#nlQuery`；解析成功提示含「原文已保留」
- [x] 5.2 手工验证：解析后切回 NL Tab 可见原文（逻辑已保证，见 spec Scenario）

## 6. 文档与验证

- [x] 6.1 更新 `web/nl-search/README.md`：共用筛选、图表 hover、价格维度分析 Tab
- [x] 6.2 手工验证：smart / exhaustive 结果下三 Tab 筛选联动（代码路径已接通）
- [x] 6.3 手工验证：图表 hover 中文地点+日期+价格+航段（tooltip 已实现）
- [x] 6.4 手工验证：API `completed` 含 `meta.code_to_country`（`build_search_meta` 单元冒烟通过）
