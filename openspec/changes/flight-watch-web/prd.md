# Flight Watch Web · PRD

## Problem Statement

用户需要**固定行程模板的长期盯价**（如达美开口、固定日期多段），但不想依赖 Tauri 桌面端。`web/nl-search` 适合一次性查价与穷举探索，无法覆盖「设好规则 → 后台轮询 → 降价推送」。现有能力缺口是：**Web 端多条 Watch + 同票/分段查价 + 飞书/微信双通道告警**。

## Solution

提供独立 Web 服务 `web/flight-watch`（网关 `/flight-watch/`，本地 `:8767`）：

- 创建全球任意 OD 的监控规则（往返/单程/多段/开口，固定日期 + 限价）
- 定时或手动查价，保留历史快照
- 命中限价或降价阈值时，飞书 + PushPlus 双通道通知
- 15 条达美开口预设一键导入起步

与 nl-search **无数据打通**；Non-Goal 不做「搜索结果一键转 Watch」。

## User Stories

1. 作为特价猎人，我想创建 PVG→LAX / LAX→NRT 开口 Watch 并设限价，以便春节档自动盯价。
2. 作为用户，我想从预设库一键导入达美方案并改日期，以便不用手填 OD。
3. 作为用户，我想在列表看到最近价与限价对比，以便快速判断是否出手。
4. 作为用户，我想手动点「查价」立即探测，以便启用前先验证规则有效。
5. 作为用户，我想启用/暂停单条 Watch，以便灵活控制 API 用量。
6. 作为用户，我想配置飞书 + 微信双通道，以便不漏告警。
7. 作为用户，我想设置轮询间隔（如 12h），以便平衡时效与配额。
8. 作为用户，我想查价历史看到 provider 与「同票/分段相加」，以便判断参考价可信度。
9. 作为用户，我想连续查价失败收到失效通知，以便及时修规则或 Key。
10. 作为用户，我想通过中文或 IATA 搜索全球机场，以便选 OD。
11. 作为用户，我想选择查价模式（自动/强制同票/仅分段），以便控制 swoop 行为。
12. 作为用户，我想设航司过滤与销售区，以便贴近目标票价渠道。
13. 作为用户，我想设降价绝对值/百分比阈值，以便捕捉二次跳水。
14. 作为会员，我想受套餐限制 Watch 条数，以便与 billing 商业化对齐。
15. 作为开发者，我想用 cron 调 `POST /api/watch/run-once`，以便服务非常驻时兜底轮询。
16. 作为用户，我想在设置页测试 RollingGo/飞书/PushPlus 连通性，以便部署前验证。
17. 作为用户，我想开口程返程不必落回出发国，以便适配达美玩法。
18. 作为用户，我想导入预设后默认未启用，以便批量导入不误推。
19. 作为用户，我想列表按最近查价/价格/名称排序筛选，以便管理多条 Watch。
20. 作为用户，我想看到「同票」标签与 bookable 语义，以便区分参考价类型。

## Implementation Decisions

- **产品形态**：FastAPI + Vue CDN + SQLite + APScheduler；经 `web/gateway` 挂载 `/flight-watch/`；不依赖 Tauri/nl-search 进程。
- **Watch 模型**：`trip_mode` × `legs[]` × `alerts` × `schedule`；开口程不限制返程落点（与 nl-search 不同）。
- **查价策略**：`auto` → swoop 同票优先 → RollingGo 分段 ONE_WAY fallback；UI/通知必须标注 `provider` 与 `bookable`。
- **告警**：限价命中 + 降价阈值 + 24h 冷却；连续 3 次查价失败 → 失效通知。
- **调度**：APScheduler 按 `interval_hours`；`POST /api/watch/run-once` cron 兜底。
- **凭据**：`.credentials.local.json` 本地存储，与 nl-search 分离。
- **预设**：`presets/delta-open-jaw.json`（15 条），导入后 `enabled=false`。
- **商业化**：`subscription_gate.check_watch_allowed` 创建时 402；列表按 `user_id` 隔离。
- **现状**：核心 CRUD/查价/通知/预设已实现；历史页仅表格（折线图 Out of Scope）。

## Testing Decisions

- **主接缝**：`POST /api/watches/{id}/poll` / `poll_watch()` — 覆盖 quote → snapshot → evaluator → notify 全链路；最接近用户「点查价」行为。
- **单元**：`evaluator.py`（`test_evaluator.py`）— 限价/冷却/降价规则，无外部依赖。
- **Mock 策略**：查价层 mock `RollingGoClient`/`quote_watch`；通知 dry_run 或 mock feishu/pushplus。
- **不优先**：Vue 组件/UI 细节、airport 下拉 DOM。
- **集成验收（手工/MVP）**：预设导入 → 补日期 → poll → 快照落库；全球机场「伦敦」→ LHR/LGW。

## Out of Scope

- Tauri 桌面端任何改动
- nl-search 内嵌 Watch Tab / 搜索结果一键转 Watch
- 全球城市穷举发现（nl-search exhaustive 职责）
- 多用户云端同步 / 云端账号体系
- ITA Matrix / Trip.nl Playwright
- 历史页价格折线图（MVP 后可选）

## Further Notes

- 本 PRD 与 OpenSpec 变更 `flight-watch-web`（proposal/design/spec/tasks）对齐；描述产品边界与代码现状。
- nl-search = 探索/穷举；Flight Watch = 固定模板长期盯价。
- 后续可选增强：402 升级 UX、历史折线图、机场空结果固定文案对齐 nl-search（「未搜索到机场」）。
