## ADDED Requirements

### Requirement: 查价 Provider 抽象

QuoteEngine SHALL 根据 Watch 的 `trip_mode` 与 `pricing_mode` 选择 Provider：往返/单程走 RollingGo；多段/开口优先 swoop-flights 同票，失败 MUST fallback RollingGo 分段相加。

#### Scenario: 往返查价

- **WHEN** trip_mode 为 round_trip
- **THEN** 调用 RollingGo ROUND_TRIP 并标记 bookable=true（在 API 有结果时）

#### Scenario: 多段同票 fallback

- **WHEN** trip_mode 为 multi_leg 且 swoop 无总价
- **THEN** 使用分段 ONE_WAY 相加且 bookable=false、provider=rollinggo_split

### Requirement: 定时调度

服务启动时 SHALL 使用 APScheduler 为每条 enabled Watch 注册按 `interval_hours` 执行的查价任务；SHALL 提供 `POST /api/watch/run-once` 供外部 cron 触发全量或单条查价。

#### Scenario: 进程内定时

- **WHEN** 服务运行且 Watch enabled、interval_hours=12
- **THEN** 每 12 小时自动查价并写入 snapshot

#### Scenario: 手动立即查价

- **WHEN** 用户点击「立即查价」
- **THEN** 该 Watch 立即执行一次查价并刷新 UI

### Requirement: 快照持久化

系统 SHALL 在 SQLite 表 `snapshots` 记录 watch_id、price、currency、provider、bookable、checked_at、error（可选）。

#### Scenario: 查价成功写快照

- **WHEN** 查价返回价格
- **THEN** 插入 snapshot 且 notify_state 可读上次价格

### Requirement: 连续失败禁用

同一 Watch 连续 3 次查价失败时，系统 MUST 自动 `enabled=false` 并记录 failure_reason。

#### Scenario: 三次失败暂停

- **WHEN** 连续 3 次 API 错误或无航班
- **THEN** Watch 自动暂停且列表显示失效状态
