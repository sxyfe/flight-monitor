## Why

用户需要 **模板固定后的盯价能力**，但 **不要桌面端**；要类似 `web/nl-search` 的 **独立 Web 工具**，且监控规则须 **全球通用**（任意国家/地区 OD、多段行程），而非仅 15 条达美 YAML。现有 Tauri 监控（单规则、分段相加）与 nl-search（一次性查价）均无法覆盖：**Web 管理多条 Watch + 同票/分段查价 + 飞书/PushPlus 告警**。

## What Changes

- 新增 **`web/flight-watch/`**：FastAPI + Vue CDN 独立服务（默认 `127.0.0.1:8767`），与 nl-search、Tauri **无集成**
- **通用 Watch 规则模型**：往返 / 单程 / 多段（2–N leg）/ 开口程；机场选择支持 **RollingGo 中文关键字 + IATA**（全球）；可选航司、销售区/币种、限价与降价阈值
- **查价 Provider 抽象**：RollingGo（往返/分段）、swoop-flights（同票多段优先）；结果标注 `bookable` 与 `provider`
- **进程内调度器**（APScheduler）：服务运行时按规则 `interval_hours` 轮询；另提供 `POST /api/watch/run-once` 供本机 cron 兜底
- **设置页**：RollingGo Key、飞书 Webhook、PushPlus token（本地 `.credentials.local.json`，与 nl-search 模式一致）
- **预设库（非硬编码唯一入口）**：15 条达美开口文章线路作为「一键导入示例」，用户可改 OD/日期后保存为自有规则
- **不**扩展 Tauri 桌面监控；**不**在 nl-search 内嵌 Watch Tab（保持查价/监控分离）

## Capabilities

### New Capabilities

- `flight-watch-web`：Web UI、Watch CRUD、全球机场选择、手动/定时查价、价格历史
- `flight-watch-engine`：Provider 抽象、告警判定（限价/降价/24h 冷却）、SQLite 持久化
- `flight-watch-notify`：飞书 + PushPlus 双通道、失效告警

### Modified Capabilities

- （无）不修改 nl-search / 桌面监控既有 spec

## Impact

- 新增：`web/flight-watch/`（server、static、requirements、README）
- 复用：`scripts/flight_search_engine.py`（RollingGoClient）、可选 symlink/read `country_city_codes.json`
- 新增依赖：`swoop-flights`、`apscheduler`、`pyyaml`（预设导入）
- 根目录 `package.json` 增加 `flight-watch:dev` 脚本
- 全球机场：MVP 以 **RollingGo airportsearch** 为主；目录国家列表作辅助，不阻塞非目录国家
- Spike（swoop 2-leg）结论保留于 design.md
