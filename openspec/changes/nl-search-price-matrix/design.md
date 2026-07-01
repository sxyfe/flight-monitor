## Context

nl-search v3 使用查询区 NL/表单双 Tab + 暖色报告结果区。`results-analytics.js` 含 `byDatePair` 索引但未挂载。现有 `SearchIntent` 仅支持单一 `date_start~date_end` 日期窗。

## Goals / Non-Goals

**Goals:**

- 第三查询 Tab「价格矩阵」，多出发地 × 多目的地往返查价
- 独立去程/返程日期窗（横轴=返程、纵轴=出发）
- 总览页：双汇总表 + 3 列矩阵卡 + 全局绿→红色阶
- SSE 进度、可取消、软提示阈值

**Non-Goals:**

- NL 解析矩阵意图、开口程、Skill 报告同步、Tauri 集成

## Decisions

### D1: MatrixSearchIntent 独立 dataclass

与 `SearchIntent` 并列，避免污染 NL/表单意图 JSON。

### D2: search_type 扩展

`POST /api/search` 增加 `search_type: "standard" | "matrix"`，矩阵走 `search_matrix()`。

### D3: 全局色阶

跨所有路线有效价格取 min/max，无价格 cell 不参与色阶。

### D4: HTML table 渲染

单元格显示具体价格数字，CSS 背景色映射；大矩阵卡片内横向滚动 + sticky 表头。

### D5: 日期窗上限

每轴最多 14 天（validate 阻断），防止单次查询爆炸。

## Risks

| 风险 | 缓解 |
|------|------|
| API 调用量大 | 软提示 + 取消 + 进度 |
| 查价失败误判无票 | 页顶「查价服务异常」banner |
| 页面过长 | 汇总表 + 3 列 grid |
