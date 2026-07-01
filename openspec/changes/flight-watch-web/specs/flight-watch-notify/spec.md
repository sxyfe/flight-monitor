## ADDED Requirements

### Requirement: 告警判定

告警引擎 SHALL 在 price ≤ max_price 时按桌面端同等逻辑通知：首次命中、降价立即通知、同价 24h 冷却后可再通知；MAY 支持 drop_abs/drop_pct 相对上次 snapshot。

#### Scenario: 首次低于限价

- **WHEN** 首次查价 price ≤ max_price
- **THEN** 触发通知

#### Scenario: 24h 冷却

- **WHEN** price 与 last_notified_price 相同且未过 cooldown_hours
- **THEN** 不重复通知

### Requirement: 飞书通知

配置 feishu_webhook 时，告警 MUST 发送文本消息，含 Watch 名、各 leg OD/日期、price、max_price、provider 及免责声明。

#### Scenario: 飞书双发

- **WHEN** 飞书与 PushPlus 均已配置且告警触发
- **THEN** 两通道均发送

### Requirement: PushPlus 微信通知

配置 pushplus_token 时，告警 MUST POST 至 PushPlus API。

#### Scenario: 仅 PushPlus

- **WHEN** 仅配置 PushPlus
- **THEN** 正常发送且不因缺少飞书报错

### Requirement: 监控失效通知

Watch 因连续失败被禁用时，系统 MUST 发送一次失效通知（若已配置任一通道）。

#### Scenario: 失效通知

- **WHEN** Watch 第三次查价失败被自动禁用
- **THEN** 发送含 watch_id 与错误摘要的告警
