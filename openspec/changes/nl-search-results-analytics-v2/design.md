## Context

`nl-flight-search-web`（v1）与 `nl-search-intent-editor-v2` 已交付 NL 查票与意图编辑能力。结果区当前实现位于 [`web/nl-search/static/app.js`](web/nl-search/static/app.js)：

- 列表 Tab 仅有 `filterType` + `filterMaxPrice`
- 图表 Tab 使用服务端 `aggregations`，无 hover 明细
- 第三 Tab 命名为「航班分析」，副标题「航变维度分析」，实际为按日期/出发地/航线的**最低价对比**
- `offer` 对象已含 `origin_name`、`out_dest_name`、`ret_dest_name`、`out_date`、`ret_date`、`detail` 等中文字段，但图表未利用

[`web/exhaustive-viz`](web/exhaustive-viz/) 已验证中文路线格式与多维筛选模式，本变更将类似模式迁入 nl-search 结果区。

## Goals / Non-Goals

**Goals:**

- 三结果 Tab 共用筛选栏，选项从当前 `offers` 派生
- 城市筛选：出发城市、去程目的地、返程目的地**任一命中**即保留
- 全部图表 hover 展示中文航班摘要（≤5 条 + 总数）
- NL 解析后 textarea 原文保留，仍自动切表单 Tab
- Tab3 更名为「价格维度分析」，图表标题易懂；日期矩阵支持色阶与 hover
- API 下发 `meta.code_to_country` 供国家筛选

**Non-Goals:**

- 修改 `search()` 查询逻辑与 RollingGo 调用
- 图表点击反向写入筛选（后续迭代）
- Tauri / 生产部署

## Decisions

### D1: 共用筛选状态与 Bridge 模式

**选择**：在 `#results-filter-app` 局部 mount Vue3 + Element Plus（与 `IntentEditorBridge` 对齐），通过 `window.ResultsFilterBridge` 与 IIFE `app.js` 通信。

```javascript
filterState = {
  countries: [],   // 多选国家名
  cities: [],    // 多选城市 code 或展示名
  outDates: [],
  retDates: [],
  tripType: "",  // "" | round_trip | open_jaw
  maxPrice: null,
};
```

`ResultsFilterBridge.getFilteredOffers(offers, meta)` 返回筛选后列表；`onChange` 回调触发三 Tab 重绘。

**理由**：Element Plus `el-select multiple filterable` 已在本项目使用，避免手写大量 chip 逻辑。

### D2: 筛选选项动态派生

| 维度 | 选项来源 | 匹配规则 |
|------|----------|----------|
| 国家 | `meta.code_to_country` 与 offers 中出现的 dest code 交集 | offer 的 `out_dest` 或 `ret_dest` 映射国家命中 |
| 城市 | offers 中 `origin`、`out_dest`、`ret_dest` 去重 | 任一端 code 或中文名命中 |
| 去程日 | `out_date` 去重排序 | `out_date` 命中 |
| 回程日 | `ret_date` 去重排序 | `ret_date` 命中 |

空选表示「不限」（AND 组合：有值的维度才参与过滤）。

### D3: 客户端重聚合

**选择**：`renderCharts()` / `renderPriceDim()` 对 `getFilteredOffers()` 结果调用 `aggregateClient(offers)`，规则镜像 [`scripts/flight_search_engine.py`](scripts/flight_search_engine.py) 的 `aggregate()`。

服务端 `aggregations` 仍随 `completed` 返回，仅作全量基准；筛选后以前端重算为准。

### D4: 维度索引与统一 Tooltip

搜索完成或筛选变更时构建：

```
buildOfferIndexes(offers) → {
  byPriceBucket, byStayDays, byOutDest, byTripType,
  byOutDate, byRetDate, byOrigin, byRouteKey
}
```

Chart.js `plugins.tooltip.callbacks.afterBody` 或 `external`：

- 根据 `dataIndex` + 图表类型查索引
- 渲染最多 5 条 offer 的中文摘要
- 超出显示「还有 N 条」

**单条摘要格式：**

```
[往返] 北京 ⇄ 曼谷 · ¥2481
去程 2026-09-27 · 回程 2026-10-04 · 停留 7 天
去: MU2021 北京→曼谷 …
```

### D5: 中文路线格式

| 类型 | 格式 |
|------|------|
| 往返 | `{origin_name} ⇄ {out_dest_name}` |
| 开口程 | `{origin_name} → {out_dest_name} · {ret_dest_name} → {ret_origin_name}` |

与 [`web/exhaustive-viz/app.js`](web/exhaustive-viz/app.js) `formatRouteLabel` 保持一致。

### D6: 价格维度分析 Tab 文案

| 原文案 | 新文案 |
|--------|--------|
| 航班分析 | 价格维度分析 |
| 航变维度分析（副标题） | 按日期与路线对比最低价 |
| 去程日期 vs 最低价 | 哪天出发最便宜？ |
| 回程日期 vs 最低价 | 哪天返程最便宜？ |
| 出发地 vs 最低价 | 从哪出发最便宜？ |
| 航线 vs 最低价 | 哪条路线最便宜？ |
| 日期组合价格矩阵 | 出发日 × 返程日 最低价热力表 |

日期矩阵：最便宜格加深 teal 背景；hover 展示该格对应 offer 明细。

### D7: 国家映射 API 扩展

在 `flight_search_engine.py` 新增：

```python
def build_code_to_country(codes: Iterable[str]) -> dict[str, str]:
    """由 DESTINATIONS_BY_COUNTRY 反查城市 code → 国家名。"""
```

`SearchResult` 与 SSE `completed` payload 增加：

```json
{
  "offers": [...],
  "aggregations": {...},
  "meta": {
    "code_to_country": { "MNL": "菲律宾", "BKK": "泰国" }
  }
}
```

`codes` 取自本次 intent 展开后的目的地集合 + offers 中出现的 code。

### D8: NL 原文保留

`btnParse` 处理逻辑：

- **禁止**写入或清空 `#nlQuery`
- 解析成功后 `tabForm.click()` 行为不变
- `parseMsg` 增加提示：「解析成功，原文已保留在「自然语言查询」Tab」

## 架构示意

```
offers[] + meta.code_to_country
        │
        ▼
ResultsFilterBridge.getFilteredOffers()
        │
        ├─► renderTable()
        ├─► aggregateClient() → renderCharts()
        └─► renderPriceDim() + dateMatrix hover
```

## 文件变更清单

| 文件 | 变更 |
|------|------|
| `web/nl-search/static/index.html` | 筛选栏 mount 点、Tab/图表标题 |
| `web/nl-search/static/results-filter.js` | 新建：筛选 Vue 组件 + Bridge |
| `web/nl-search/static/app.js` | 聚合、索引、tooltip、价格维度 Tab |
| `web/nl-search/static/boot.js` | 加载 `results-filter.js` |
| `web/nl-search/server.py` | completed / 同步响应附加 meta |
| `scripts/flight_search_engine.py` | `build_code_to_country()` |
| `web/nl-search/README.md` | 筛选与 hover 说明 |

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 穷举结果 hover 条数过多 | 限制 5 条 + 总数 |
| 前后端聚合不一致 | `aggregateClient` 注释对齐 Python `aggregate()` 规则 |
| Vue 与 IIFE 状态同步 | 单一 Bridge 入口，筛选变更只通过 `onChange` 广播 |
| 国家映射缺 code | 未映射 code 不参与国家筛选，城市筛选仍可用 |

## Open Questions

- 是否在后续迭代支持图表柱/点点击写入筛选（本变更不做）
- `aggregateClient` 是否抽为共享 JS 模块供 exhaustive-viz 复用（非本变更范围）
