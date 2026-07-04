## 1. 项目脚手架

- [x] 1.1 创建 `web/flight-watch/`（server.py、requirements.txt、README、static/index.html）
- [x] 1.2 根目录 `package.json` 增加 `flight-watch:dev`（默认端口 8767）
- [x] 1.3 `.gitignore`：`data/flight_watch.db`、`.credentials.local.json`

## 2. 引擎与存储

- [x] 2.1 `quote_engine.py`：RollingGo RT/OW + swoop multi_leg + fallback
- [x] 2.2 `store.py`：SQLite watches / snapshots / notify_state / notify_log
- [x] 2.3 `evaluator.py`：告警判定（移植桌面逻辑 + drop 阈值）
- [x] 2.4 `scheduler.py`：APScheduler + run-once API

## 3. API

- [x] 3.1 Watch CRUD：`GET/POST/PUT/DELETE /api/watches`
- [x] 3.2 `POST /api/watches/{id}/poll` 立即查价
- [x] 3.3 `GET /api/watches/{id}/snapshots` 历史
- [x] 3.4 `GET /api/airports/search?q=` 代理 RollingGo airportsearch
- [x] 3.5 预设：`GET /api/presets`、`POST /api/presets/{id}/import`
- [x] 3.6 设置：凭据读写、RollingGo/飞书/PushPlus 测试

## 4. 预设库

- [x] 4.1 `presets/delta-open-jaw.json` 15 条达美线路
- [x] 4.2 导入后 enabled=false、可编辑

## 5. 前端 UI

- [x] 5.1 监控列表 + 启用开关 + 立即查价
- [x] 5.2 Watch 编辑器（段式表单、机场 chip、trip_mode、告警、调度）
- [x] 5.3 详情/历史快照
- [x] 5.4 预设库页
- [x] 5.5 设置页（对齐 nl-search 交互：眼睛切换密钥、测试按钮）
- [x] 5.6 暖色 token 复用（CSS 变量）
- [x] 5.7 机场空结果「未搜索到机场」、日期 min=今日、折叠高级告警字段

## 6. 通知

- [x] 6.1 `notify/feishu.py`、`notify/pushplus.py`
- [x] 6.2 失效通知与 dry-run 模式（仅查价不推送）

## 7. 验收

- [x] 7.1 创建 PVG→LAX / LAX→NRT 开口 Watch，立即查价有 snapshot
- [x] 7.2 从预设导入 15 条之一并编辑日期
- [x] 7.3 mock 低价触发飞书 + PushPlus（或单元测试 evaluator）
- [x] 7.4 全球机场：搜索「伦敦」返回 LHR/LGW 等
- [x] 7.5 README 含「服务需常驻或 cron 调 run-once」说明

## 8. Spike 收尾

- [x] 8.1 `web/flight-watch/spike_swoop.py` 记录 2-leg 查价样例输出（依赖 swoop-flights）

## 9. 测试（PRD）

- [x] 9.1 `test_poll_watch.py`：`poll_watch` 集成测试（mock 查价，dry_run）
