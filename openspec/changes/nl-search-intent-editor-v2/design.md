## Context

`nl-flight-search-web`（v1）已在 `web/nl-search/` 交付 FastAPI + 静态 HTML 原型：NL 解析、smart/exhaustive 搜索、结果表格与图表。意图编辑区仍为 MVP：

- 原生 `<input type="date">`、逗号文本框
- JSON 只读展示，表单与 JSON 无显式同步
- 国庆解析用 `date.today().year` 固定 `09-25~10-07`，未区分「国庆」与「国庆前后」，未做 future-aware
- 出发地/目的地不支持中文机场搜索 UI
- 无 NL / 表单双模式 Tab

用户已确认 v2 方向：Vue3 + Element Plus 局部 mount、双 Tab、确认按钮 dirty 合并、机场搜索、国庆新语义。

## Goals / Non-Goals

**Goals:**

- 双模式 Tab：自然语言查询 → 解析 → 自动切表单 Tab 预填
- 表单 Tab：Element Plus 意图编辑器（日期 range、国家多选、行程 checkbox、机场标签）
- 「确认」：dirty 优先合并 → 双向刷新表单 + JSON → validate 预估
- 出发地、目的地均支持中文 `airportsearch` 选择
- 设置 API Key 👁 明文切换
- 国庆 / 国庆前后 future-aware 解析（10-01~10-07 / 09-28~10-10）
- 新增 `GET /api/airport/search`、`POST /api/intent/validate`

**Non-Goals:**

- 整站迁 Vite/Vue SPA 或替换 Tauri 前端
- 修改 `flight_search_engine.py` 搜索算法
- 修改 `exhaustive_search.py` CLI 硬编码日期窗
- 生产公网部署、多用户凭据

## Decisions

### D1: Vue3 + Element Plus CDN 局部 mount

**选择**：在 `static/index.html` 保留结果/设置/进度；新增 `#intent-editor-app`，用 Vue3 + Element Plus（unpkg/jsdelivr CDN + zh-CN locale）mount 表单 Tab 内容。

**理由**：用户明确要求 Element UI 风格；局部 mount 避免引入 Vite 构建链，与 v1 独立原型目标一致。

**备选**：Flatpickr 仿 Element 皮 — 无法满足 Tag/Select/Checkbox 全套需求。

### D2: 双 Tab 与 NL → 表单流

```
┌─────────────────┐     解析成功      ┌─────────────────┐
│  Tab: 自然语言   │ ───────────────▶ │  Tab: 表单查询   │
│  textarea+解析   │   自动切换+预填   │  IntentEditor   │
└─────────────────┘                   └────────┬────────┘
                                               │ [确认]
                                               ▼
                                        confirmedIntent
                                               │
                                               ▼
                                         [开始搜索]
```

**选择**：NL Tab 仅含 textarea +「解析意图」；解析成功后 `activeTab = 'form'`，将 `intent` 传入 IntentEditor。表单 Tab 可独立进入（空表单或上次 confirmedIntent）。

**搜索门禁**：`开始搜索` 仅当 `confirmedIntent !== null` 且最近一次「确认」校验 `valid === true`。

### D3: 确认按钮 dirty 合并

**选择**：

| 状态 | 行为 |
|------|------|
| `jsonDirty && formDirty` | 阻止确认，提示「请只编辑表单或 JSON 一处」 |
| 仅 `jsonDirty` | `JSON.parse` → Intent → 反写表单 |
| 仅 `formDirty` 或均不 dirty | 表单 → Intent → 写 JSON |
| 确认后 | 清除 dirty 标记；`POST /api/intent/validate`；更新预估与 warnings |

**理由**：避免半行无效 JSON 破坏表单；单一 truth 为 confirmedIntent。

### D4: AirportPicker 复用组件

**选择**：单一 Vue 组件（或 composable）`AirportPicker`，props: `modelValue: string[]`（IATA codes）、`labels: Record<string,string>`。内部调用 `GET /api/airport/search?q=` debounce 300ms。出发地、目的地各一实例。

**后端**：`server.py` 包装 `RollingGoClient.search_airports(q)`，返回 `{ items: [{ cityCode, cityName, ... }] }`。

**国家与目的地关系**（不变）：

- `destinations` 非空 → 精确城市
- `destinations` 空 + `countries` 非空 → 引擎按国家扩城
- 均空 → validation error

### D5: 国庆日期窗（future-aware）

**选择**：新增 `scripts/holiday_windows.py`（或 `web/nl-search/holiday_windows.py`）：

| 关键词 | date_start | date_end |
|--------|------------|----------|
| 国庆前后 | MM-DD 09-28 | MM-DD 10-10 |
| 国庆（且不含「前后」） | MM-DD 10-01 | MM-DD 10-07 |

**Future 规则**：以 `ref_date = date.today()`，取 `ref_date.year` 构造窗口；若 `date_end < ref_date`，年份 +1。

**LLM prompt** 注入 `today=YYYY-MM-DD` 与上表；规则回退 `parse_with_rules()` 调用同一函数。

**与穷举 CLI 关系**：`exhaustive_search.py` 仍用 9/25~10/7 实验窗；NL 默认窗独立，以用户 confirmed Intent 为准。

### D6: Element Plus 日期选择器

**选择**：`el-date-picker` `type="daterange"`，`disabledDate` 禁用 `< today`。解析为「国庆」时默认 range 10-01~10-07；「国庆前后」默认 09-28~10-10。可选：在日历 cell 上对 10-01~10-07 加 CSS 高亮（非阻塞 MVP）。

### D7: 行程类型 UI

**选择**：两个独立 `el-checkbox`：「往返联票」「开口程」，映射 `trip_modes` 数组；至少勾选一项。

### D8: API Key 明文切换

**选择**：设置面板 RollingGo Key、LLM Key 各配 `el-input` `show-password` 或自定义 👁 toggle（`type` password/text 切换）。保存后输入框恢复 password 态。

### D9: POST /api/intent/validate

**选择**：接受 `{ "intent": SearchIntent }`，返回与 parse 相同的 `validation` 结构（无 LLM 调用）。确认按钮专用；parse 端点行为不变。

## API 补充

Base: `http://127.0.0.1:8765/api`

#### `GET /api/airport/search?q=北京`

```json
{
  "items": [
    { "cityCode": "BJS", "cityName": "北京", "airportCode": "PEK", "airportName": "首都" }
  ]
}
```

#### `POST /api/intent/validate`

```json
// Request
{ "intent": { "origins": ["BJS"], ... } }

// Response
{
  "validation": {
    "valid": true,
    "warnings": [],
    "errors": [],
    "clarifications": [],
    "estimated_queries_smart": 42,
    "estimated_queries_exhaustive": 891
  }
}
```

## 文件结构（预期）

```
web/nl-search/
  static/
    index.html              # Tab 壳 + 结果区 + mount 点
    intent-editor.js        # Vue SFC-less 单文件组件（或 intent-editor/）
  server.py                 # +airport search, +validate
  nl_parser.py              # +holiday_windows 调用
scripts/
  holiday_windows.py        # resolve_national_day_window(q, ref_date)
```

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| CDN 依赖离线不可用 | README 注明需网络；后续可 vendoring |
| Vue 与 vanilla JS 状态分裂 | `confirmedIntent` 由 Vue emit 至父层全局变量或 custom event |
| JSON 手改引入非法结构 | 确认时 JSON.parse + schema 校验，失败不更新 |
| v1 国庆窗行为变更 | proposal 已标注；仅影响 NL 默认解析 |

## Migration Plan

1. 实现后端 holiday + API 端点（向后兼容）
2. 新增 IntentEditor Vue mount，保留 v1 结果区
3. 重构 index.html 为 Tab 布局；NL 流接 parse → 切 Tab
4. 手动验证：国庆/国庆前后日期、确认同步、机场搜索、搜索门禁

回滚：git revert；v1 HTML 仍可独立运行（无新 API 时机场搜索降级为手动输入）。

## Open Questions

- （已关闭）JSON 是否反写表单 → **是，经确认按钮**
- （已关闭）目的地是否 airport 搜索 → **是**
- 日历是否高亮 10-01~10-07 核心周 → MVP 可选 CSS，不阻塞 apply
