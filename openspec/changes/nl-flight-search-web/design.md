## Context

`flight-monitor` 仓库已有：

- **Tauri 桌面端**：结构化监控规则、Keychain 存 RollingGo Key、hourly 轮询 + 飞书通知
- **`scripts/exhaustive_search.py`**：京津出发、39 目的地、21 组日期、RT + 开口程穷举，结果写 `exhaustive_results.json`
- **`output/rollinggo-xhs-cards/`**：静态结果展示页（1080×1440 卡片）

用户希望增加**独立 Web 原型**：自然语言输入 → 配置 RollingGo + LLM → 校验拆分诉求 → 查票 → 可视化分析。探索阶段已确认：LLM 只做意图结构化，查票由确定性 Python 执行；不宜每次默认全量 2574 次查询。

## Goals / Non-Goals

**Goals:**

- 本机 `localhost` 可运行的独立 Web 原型（浏览器访问）
- 自然语言 → `SearchIntent` → RollingGo 查询 → 表格 + 多维图表
- 配置 RollingGo Base URL、Bearer Token、LLM Base URL、Model、API Key
- 搜索前展示结构化诉求预览、查询量预估、校验警告
- 支持 `smart` / `exhaustive` 查询模式与 SSE 进度
- 结果按价格、停留天数、目的地、行程类型等维度聚合

**Non-Goals:**

- Tauri 内嵌或替换现有监控 UI
- 多用户、云端部署、凭据服务端持久化（MVP 仅本机 session / localStorage）
- 订票、支付、舱位余票实时锁定
- 浏览器内直接调用 RollingGo / LLM（避免 Key 暴露与 CORS）

## Decisions

### D1: 独立 Web = FastAPI + 静态 HTML

**选择**：`web/nl-search/server.py` + `web/nl-search/static/index.html`

**理由**：快速验证 NL + 可视化；Key 存后端内存或加密本地文件，不暴露给前端 JS 直调外部 API。

**备选**：扩展现有 Vue/Tauri — 工作量大，与「独立原型」目标不符。

### D2: LLM 只产出 SearchIntent，查票不走 MCP

**选择**：后端用 OpenAI 兼容 Chat Completions + JSON Schema / function calling，输出 `SearchIntent`；RollingGo 走现有 REST（`/api/mcp/flightsearch`、`/api/mcp/airportsearch`）。

**理由**：与 `exhaustive_search.py`、`RollingGoClient` 一致；浏览器无需嵌 MCP Server。

**备选**：Cursor MCP 代理 — 绑定 IDE，不适合独立网页。

### D3: 查询引擎自 exhaustive_search 抽取

**选择**：`scripts/flight_search_engine.py` 提供：

```python
class SearchIntent(TypedDict): ...
class FlightOffer(TypedDict): ...

def validate_intent(intent) -> ValidationResult: ...
def estimate_query_count(intent, mode) -> int: ...
def search(intent, mode, on_progress) -> SearchResult: ...
```

`exhaustive_search.py` 的 `main()` 改为薄 CLI 包装。

### D4: 默认 smart 模式，exhaustive 需显式确认

| 模式 | 行为 | 典型查询量 |
|------|------|-----------|
| `smart` | 按国家/用户指定城市缩小目的地；日期对按窗口生成 | 数十～数百 |
| `exhaustive` | 等同当前穷举逻辑 | ~2500+ |

UI 在 `estimate_query_count > 500` 时必须二次确认。

### D5: 凭据存储（MVP）

- 前端：设置面板写入 `POST /api/config`（仅本机）
- 后端：进程内存 + 可选 `web/nl-search/.credentials.local.json`（gitignore）
- **不**复用 Tauri Keychain（独立原型）

### D6: 可视化技术栈

- 表格：原生 HTML + 轻量排序/filter（或 Alpine.js）
- 图表：Chart.js 或纯 CSS/SVG 柱状图（与 xhs-cards 风格一致）
- 风格：延续 `rollinggo-xhs-cards` 暖色编辑风，但布局为**工具型仪表盘**

## API 设计

Base URL: `http://127.0.0.1:8765/api`

### 配置

#### `POST /api/config`

保存运行时配置（本机）。

```json
{
  "rollinggo": {
    "base_url": "https://mcp.rollinggo.cn",
    "api_key": "mcp_xxx"
  },
  "llm": {
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-xxx",
    "model": "gpt-4o-mini"
  }
}
```

Response: `{ "ok": true }`

#### `GET /api/config/status`

```json
{
  "rollinggo_configured": true,
  "llm_configured": true,
  "rollinggo_base_url": "https://mcp.rollinggo.cn",
  "llm_base_url": "https://api.openai.com/v1",
  "llm_model": "gpt-4o-mini"
}
```

（不返回完整 Key。）

#### `POST /api/config/test-rollinggo`

验证 RollingGo 连接（调用 `airportsearch` keyword=`BJS`）。

#### `POST /api/config/test-llm`

发送极简 ping 请求验证 LLM。

---

### 自然语言解析

#### `POST /api/intent/parse`

Request:

```json
{
  "query": "天津或北京出发，国庆去泰国菲律宾，至少玩7天，2500以内，可以开口程",
  "locale": "zh-CN"
}
```

Response:

```json
{
  "intent": {
    "origins": ["BJS", "TSN"],
    "destinations": ["BKK", "HKT", "MNL", "CEB"],
    "countries": ["泰国", "菲律宾"],
    "date_start": "2026-09-25",
    "date_end": "2026-10-07",
    "min_stay_days": 7,
    "max_price": 2500,
    "trip_modes": ["round_trip", "open_jaw"],
    "cabin": "ECONOMY",
    "adults": 1,
    "children": 0
  },
  "validation": {
    "valid": true,
    "warnings": ["日本未包含在目的地中"],
    "errors": [],
    "clarifications": [],
    "estimated_queries_smart": 186,
    "estimated_queries_exhaustive": 2574
  }
}
```

当 `validation.valid === false` 且 `clarifications` 非空时，前端展示追问，不自动搜索。

---

### 搜索

#### `POST /api/search`

Request:

```json
{
  "intent": { "...": "同上" },
  "mode": "smart",
  "confirmed_high_cost": false
}
```

Response（同步，smart 模式）:

```json
{
  "search_id": "srch_abc123",
  "status": "completed",
  "stats": {
    "total_queries": 186,
    "errors": 0,
    "rt_count": 12,
    "oj_count": 45,
    "duration_ms": 42000
  },
  "offers": [ "..." ],
  "aggregations": { "..." }
}
```

#### `GET /api/search/{id}/stream` (SSE)

事件类型：

- `progress` — `{ "done": 120, "total": 186 }`
- `offer` — 单条命中（增量，可选）
- `completed` — 完整 `SearchResult`
- `error`

exhaustive 模式默认走 SSE。

---

### 结果与聚合

#### `GET /api/search/{id}`

返回完整 `SearchResult`（offers + aggregations）。

#### `FlightOffer` 结构

```json
{
  "id": "offer_001",
  "trip_type": "round_trip",
  "price": 2381,
  "currency": "CNY",
  "origin": "TSN",
  "origin_name": "天津",
  "out_dest": "MNL",
  "out_dest_name": "马尼拉",
  "ret_dest": "MNL",
  "ret_dest_name": "马尼拉",
  "ret_origin": "TSN",
  "ret_origin_name": "天津",
  "out_date": "2026-09-26",
  "ret_date": "2026-10-03",
  "stay_days": 7,
  "bookable": true,
  "segments_out": [
    { "flight": "CA2861", "from": "TSN", "to": "CKG", "dep": "2026-09-26T07:50:00" }
  ],
  "segments_ret": []
}
```

`bookable`: RT 为 `true`；开口程为 `false`（分段最低价相加）。

#### `aggregations` 结构

```json
{
  "by_price_bucket": [{ "bucket": "2300-2400", "count": 8 }],
  "by_stay_days": [{ "days": 7, "count": 20, "min_price": 2381 }],
  "by_destination": [{ "code": "MNL", "name": "马尼拉", "count": 15, "min_price": 2381 }],
  "by_origin": [{ "code": "TSN", "name": "天津", "count": 10, "min_price": 2381 }],
  "by_trip_type": [{ "type": "round_trip", "count": 3 }, { "type": "open_jaw", "count": 94 }],
  "recommendations": {
    "cheapest": "offer_001",
    "longest_stay": "offer_042",
    "best_round_trip": "offer_001"
  }
}
```

---

## 页面线框

### 页面 1：设置（可折叠侧栏或 Modal）

```
┌─────────────────────────────────────────────────────────────┐
│ ⚙️ 连接设置                                                  │
├─────────────────────────────────────────────────────────────┤
│ RollingGo                                                    │
│   Base URL  [ https://mcp.rollinggo.cn          ]           │
│   API Key   [ ••••••••••••••••••               ] [测试连接] │
├─────────────────────────────────────────────────────────────┤
│ 大模型（OpenAI 兼容）                                         │
│   Base URL  [ https://api.openai.com/v1         ]           │
│   Model     [ gpt-4o-mini                       ]           │
│   API Key   [ ••••••••••••••••••               ] [测试连接] │
├─────────────────────────────────────────────────────────────┤
│ [保存配置]  状态：RollingGo ✅  LLM ✅                         │
└─────────────────────────────────────────────────────────────┘
```

### 页面 2：主工作台（默认视图）

```
┌─────────────────────────────────────────────────────────────┐
│ Flight NL Search          [⚙️设置]  rollinggo.store 文档链接   │
├─────────────────────────────────────────────────────────────┤
│ 用一句话描述你的机票需求：                                    │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 京津出发，9/25-10/7，东南亚+日本，至少玩7天，2500以内，    │ │
│ │ 可以开口程                                               │ │
│ └─────────────────────────────────────────────────────────┘ │
│ [解析诉求]  模式：◉ 智能  ○ 全量穷举                         │
├─────────────────────────────────────────────────────────────┤
│ 📋 解析结果（可编辑）                                        │
│  出发：北京/天津  目的地：泰菲马印日(39城)  预算：≤¥2500       │
│  日期：2026-09-25~10-07  最少停留：7天  类型：往返+开口程      │
│  ⚠️ 预估智能模式 186 次查询 (~2min)  全量 2574 次 (~35min)    │
│  [开始搜索]                                                  │
├─────────────────────────────────────────────────────────────┤
│ 进度 ████████████░░░░░░  120/186                             │
└─────────────────────────────────────────────────────────────┘
```

### 页面 3：结果区（搜索完成后）

```
┌──────────────────────────┬──────────────────────────────────┐
│ 筛选                      │  🏆 推荐                          │
│ 价格 ≤ [2500]            │  最便宜 ¥2381 天津↔马尼拉 联票     │
│ 停留 ≥ [7] 天            │  玩最久 10天  北京↔普吉 ¥2510*    │
│ 出发地 ☑京 ☑津           │  *略超预算                        │
│ 类型 ☑联票 ☑开口程       ├──────────────────────────────────┤
│ 国家 ▼ 东南亚…           │  [价格分布] [停留天数] [目的地] [类型]│
│                          │   ▂▃▅▇ 柱状图 / 可切换 Tab         │
├──────────────────────────┴──────────────────────────────────┤
│ 结果表格  排序：价格▲  |  共 97 条                            │
│ ┌────┬────┬────┬────┬────┬────┬────┬──────────────────────┐ │
│ │价格│类型│出发│目的地│去 │回 │天数│ 航班摘要               │ │
│ ├────┼────┼────┼────┼────┼────┼────┼──────────────────────┤ │
│ │2381│联票│天津│马尼拉│926│1003│ 7 │ CA2861/CA481 …        │ │
│ │2002│开口│天津│马尼拉│925│1002│ 7 │ 分段价·需核实联订      │ │
│ └────┴────┴────┴────┴────┴────┴────┴──────────────────────┘ │
│ ⚠️ 开口程为两段单程最低价相加，不代表可订联票。                  │
└─────────────────────────────────────────────────────────────┘
```

### 交互要点

- 解析后 `SearchIntent` 各字段可手动改（下拉城市、日期选择器）
- 开口程行使用不同背景色 + `bookable: false` 徽章
- 点击表格行展开航段明细
- 图表与表格筛选联动

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| LLM 解析城市/日期错误 | JSON Schema + 代码校验 + `airportsearch` 消歧 |
| 全量穷举超时 | 默认 smart；高成本需确认；SSE + 可取消 |
| 开口程误导用户 | `bookable` 字段 + UI 强提示 |
| API Key 泄露 | 仅本机服务；`.credentials.local.json` gitignore；文档警示 |
| 与 Tauri 逻辑重复 | 引擎单文件抽取；未来可共享 Rust/Python 边界清晰 |
| LLM 成本 | 每次搜索仅 1 次 parse 调用；可缓存同句解析 |

## Migration Plan

1. 新增 `web/nl-search/`，不改动 Tauri 构建
2. `npm` 脚本可选：`npm run nl-search:dev` → `uvicorn`
3. 文档写入 `web/nl-search/README.md` 启动说明
4. 回滚：删除 `web/nl-search/` 目录即可，无数据库迁移

## Open Questions

- LLM 默认模型是否写死 `gpt-4o-mini` 还是仅文档推荐？
- smart 模式目的地缩小规则：按「国家 → 热门 6 城」还是按 LLM 显式列城市？
- 是否需要在 MVP 支持导出 CSV / 复用 `exhaustive_results.json` 格式？
