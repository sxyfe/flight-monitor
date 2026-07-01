## Why

用户在固定去程/返程日期窗内，需要对比多条路线（多出发地 × 多目的地）的「出发日 × 返程日」组合低价。现有 NL/表单查询 + 暖色报告以列表与一维图表为主，无法直观呈现二维价格分布。

## What Changes

- 查询区新增第三 Tab「价格矩阵」，含独立表单（多选出发/目的地、去程日期窗、返程日期窗、停留约束）
- 搜索引擎新增 `MatrixSearchIntent` 与 `search_matrix()`，独立去程/返程日期窗生成日期对并逐格 ROUND_TRIP 查价
- 结果区新增矩阵总览页：路线汇总表 + 每路线热力矩阵卡 + 全局色阶图例
- `POST /api/search` 扩展 `search_type=matrix`；新增 `POST /api/matrix/validate`

## Capabilities

### New Capabilities

- `nl-search-matrix`：矩阵查询 Tab、校验、查价、可视化

### Modified Capabilities

- `flight-search-engine`：矩阵意图、日期对、矩阵搜索函数

## Impact

- `scripts/flight_search_engine.py`
- `web/nl-search/server.py`
- `web/nl-search/static/index.html`、`app.js`、新增 matrix 前端模块
- 不影响 Tauri、flight-watch、Skill 暖色报告模板
