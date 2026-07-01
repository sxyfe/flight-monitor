## Why

`web/nl-search` 结果区虽已具备列表与基础图表，但三个 Tab 筛选割裂、图表无法 hover 下钻到具体航班，且「航变维度分析」命名与实际「按维度对比最低价」不符，用户难以基于搜索结果做决策。需在不动查询引擎核心的前提下，升级结果分析与筛选体验。

## What Changes

- 结果区新增**共用筛选栏**（国家 / 城市 / 去程日 / 回程日，Element Plus 多选 + 可搜索）；选项仅从当前 `offers` 动态派生
- 航班列表、图表分析、价格维度分析三 Tab **共享 `getFilteredOffers()`**，筛选变更后联动刷新
- 全部 Chart.js 图表 hover 展示中文航班摘要（地点、日期、价格、航段，最多 5 条 + 总数提示）
- NL 解析成功后**保留**自然语言 textarea 原文，仍自动切换至「表单查询」Tab
- 将原「航班分析 / 航变维度分析」Tab 重命名为**「价格维度分析」**，优化图表标题与日期组合矩阵（色阶 + hover 明细）
- 搜索完成响应（同步与 SSE `completed`）增加 `meta.code_to_country`，供国家筛选使用
- 开口程路线统一中文展示格式：`天津 → 马尼拉 · 棉兰 → 天津`

## Capabilities

### New Capabilities

（无独立新 capability；本变更扩展已有能力。）

### Modified Capabilities

- `nl-search-ui`：共用结果筛选、图表 hover 中文明细、价格维度分析 Tab、NL 原文保留
- `nl-search-api`：搜索完成 payload 增加 `meta.code_to_country`（非破坏性扩展）

## Impact

- **修改代码**：[`web/nl-search/static/index.html`](web/nl-search/static/index.html)、[`web/nl-search/static/app.js`](web/nl-search/static/app.js)、新增 [`web/nl-search/static/results-filter.js`](web/nl-search/static/results-filter.js)、[`web/nl-search/server.py`](web/nl-search/server.py)、[`scripts/flight_search_engine.py`](scripts/flight_search_engine.py)（辅助函数）
- **文档**：更新 [`web/nl-search/README.md`](web/nl-search/README.md)
- **不受影响**：Tauri 桌面端、Intent 编辑器 v2 表单逻辑、`exhaustive_search.py` CLI 参数
- **与 `nl-search-intent-editor-v2` 关系**：正交；本变更专门升级结果区，不替换意图编辑流程

## Non-Goals

- 不修改 RollingGo 查询计划与 RT/开口程计价逻辑
- 不做 Tauri 集成或生产部署
- 不做图表点击与筛选栏双向联动（后续迭代）
- 不实现 CSV 导出
