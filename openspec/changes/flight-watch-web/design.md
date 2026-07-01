## Context

- `web/nl-search`：FastAPI + Vue、本地凭据、SSE 搜索、暖色报告；**定位一次性查价**
- Tauri 桌面：hourly 单规则监控；用户 **明确不要** 扩展桌面
- `country_city_codes.json` 现仅 5 国（泰菲印马日）；全球监控不能依赖该文件 alone
- 先前 spike：`swoop-flights==0.7.0` 可装；2-leg 开口默认 TWD、同票总价链路待实现验收
- 用户决策：**独立 Web**、**通用全球**、飞书 + PushPlus、15 条达美作预设示例

## Goals / Non-Goals

**Goals:**

- `web/flight-watch` 独立服务，UX 对齐 nl-search（设置页、中文、暖色 token 可复用）
- 用户可创建 **多条** Watch：任意 IATA OD、1–N 段、固定日期、限价/降价/冷却
- 机场搜索：**RollingGo airportsearch** 全球关键字；展示中文城市名 + 代码
- 服务启动后 **进程内定时** 查价；UI 展示历史曲线与最近快照
- 告警：飞书 + PushPlus（设置页配置）
- 预设库：15 条达美开口可「导入为 Watch」

**Non-Goals:**

- Tauri / 桌面任何改动
- nl-search 合并或 iframe 嵌入
- 全球城市穷举发现（那是 nl-search exhaustive；Watch 只盯用户定好的结构）
- Trip.nl Playwright、ITA Matrix（Phase 2+）
- 多用户/云端账号（仍为本机单用户）

## Decisions

### D1: 产品形态 — 独立 Web，对齐 nl-search

```
┌─────────────────────────────────────────────────────────────┐
│  web/nl-search :8765     一次性查价 · 穷举 · NL 解析         │
│  web/exhaustive-viz :8766  穷举结果可视化                    │
│  web/flight-watch :8767  多条 Watch · 定时查价 · 告警  ← NEW │
│  Tauri 桌面              单规则监控（不变、不集成）           │
└─────────────────────────────────────────────────────────────┘
```

**栈**：FastAPI + Vue 3 CDN + SQLite + APScheduler（与 nl-search 同构，降低维护成本）。

### D2: 通用 Watch 规则模型

```yaml
# 逻辑模型（存 SQLite，非用户手写 YAML）
id: uuid
name: string
enabled: bool
trip_mode: round_trip | one_way | multi_leg | open_jaw
legs:
  - { from: IATA, to: IATA, date: YYYY-MM-DD }
return_date: optional          # round_trip
pricing_mode: auto             # auto | same_ticket | split_one_way
sales_region: optional         # ISO 3166-1 alpha-2，供 swoop set_country
currency: optional             # 展示/告警币种，默认 CNY
filters:
  carriers: [DL]               # 可选
  cabin: ECONOMY
alerts:
  max_price: number
  drop_abs: number
  drop_pct: number
  cooldown_hours: 24
schedule:
  interval_hours: 12
  active_until: optional
```

| trip_mode | 查价策略 |
|-----------|----------|
| `round_trip` | RollingGo ROUND_TRIP |
| `one_way` | RollingGo ONE_WAY |
| `multi_leg` | swoop `search_legs` + `price_selector` 同票；失败则每段 ONE_WAY 相加 |
| `open_jaw` | 与 multi_leg 相同（2 段且 OD 不对称）；第三国终点 **允许**（如 PVG→LAX, LAX→NRT） |

**与 nl-search open_jaw 差异**：nl-search 强制返程落 `origins` 集合；flight-watch **不限制** 返程终点，适配达美玩法。

### D3: 全球机场 / 地区

**主路径**：RollingGo `airportsearch(keyword)` — 已支持中文 + 全球 IATA（与 nl-search 机场选择一致）。

**辅路径**：

- 读取 `scripts/data/country_city_codes.json` 作热门城市 chip（5 国 + 可扩展）
- 未来 `sync_country_airports.py` 扩国家 **不阻塞** MVP；Watch 不依赖穷举目录

**地区展示**：航线/规则列表优先 **中文城市名**（AGENTS.md 一致）；无映射时显示 IATA。

### D4: Provider 与 bookable 语义

```
                    ┌──────────────┐
  WatchRule ───────▶│ QuoteEngine  │
                    └──────┬───────┘
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    RollingGo RT/OW   swoop same_ticket   (future)
           │               │
           └───────┬───────┘
                   ▼
            QuoteResult { price, currency, provider, bookable, legs[] }
```

UI 与通知 MUST 标明 `provider` 与「分段相加仅供参考」。

### D5: 调度

- **主**：FastAPI `lifespan` 启动 APScheduler，按各 Watch `interval_hours` 注册 job
- **辅**：`POST /api/watch/run-once` + cron 示例（服务未常驻时手动兜底）
- 单 Watch 查价 **串行**；多 Watch 之间 **有限并发**（如 2–3），避免 RollingGo/swoop 限流

### D6: 存储与凭据

- SQLite：`web/flight-watch/data/flight_watch.db`（gitignore）
- 凭据：`web/flight-watch/.credentials.local.json`（RollingGo、飞书、PushPlus）
- 与 nl-search **分离文件**（用户可填相同 Key）

### D7: UI 信息架构

```
/flight-watch
├── 监控列表（启用/暂停、最近价、距限价、下次执行）
├── 新建/编辑 Watch（段式表单 + 机场 chip + 日期 + 告警 + 调度）
├── 详情/历史（快照表 + 简易折线）
├── 预设库（15 条达美 → 导入）
└── 设置（Key、Webhook、PushPlus、测试连通性）
```

暖色 report token 可复用 nl-search `static` 中 CSS 变量（复制或软链），**不**复用搜索结果页逻辑。

### D8: 预设库（15 条达美）

仍为文章线路，但作为 **`presets/delta-open-jaw.json`** 由 API `POST /api/watch/import-preset/{id}` 导入，**不是** 唯一数据源。导入后变为 SQLite 内普通 Watch，用户可编辑。

默认导入后 `enabled: false`，避免 15 条同时推送。

### D9: 通知

- 飞书 / PushPlus 双通道，逻辑移植自 Tauri `evaluator.rs` + 扩展 drop 阈值
- 通知正文：Watch 名、各 leg、price、max_price、provider、bookable 免责声明

## Spike 结果（保留）

见上一版 design：swoop-flights 0.7.0、2-leg TWD 单段价问题、需 price_selector 全链路；RollingGo split 作 fallback。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| Web 服务需常驻才能定时 | 文档说明 + cron 调 run-once |
| swoop 区域/币种不准 | sales_region 字段 + UI 展示 raw currency |
| 全球 airportsearch 依赖 RollingGo | 设置页测试连通性；失败时表单提示 |
| 与 nl-search 代码重复 | 抽 `scripts/quote_engine.py` 共用 RollingGo；Watch 专用 swoop 放 web 侧 |

## Open Questions

- 项目目录名：`web/flight-watch` vs `web/price-watch`（暂定 flight-watch）
- 是否在 MVP 做「从 nl-search 某次搜索结果一键创建 Watch」（Non-Goal 暂不做）

## Migration Plan

1. 实现 `web/flight-watch` MVP
2. `npm run flight-watch:dev`
3. 设置页填 Key + Webhook
4. 从预设导入 1 条达美线试跑

## Rollback

删除 `web/flight-watch/` 与 npm script；不影响 nl-search / 桌面。
