## ADDED Requirements

### Requirement: 独立 Web 服务

系统 SHALL 在 `web/flight-watch/` 提供 FastAPI 服务，默认监听 `127.0.0.1:8767`；SHALL 提供静态 Vue 单页与 REST API；MUST NOT 依赖 Tauri 桌面或 nl-search 进程。

#### Scenario: 本地启动

- **WHEN** 用户执行 `npm run flight-watch:dev`
- **THEN** 浏览器可访问监控列表页且 API 返回 200

### Requirement: Watch 规则 CRUD

系统 SHALL 允许用户创建、编辑、删除、启用/暂停多条 Watch 规则；每条规则 MUST 含 `name`、`trip_mode`、`legs`（含 from/to/date）、`alerts.max_price`、`schedule.interval_hours`。

#### Scenario: 创建往返监控

- **WHEN** 用户选择往返、填写 PVG→NRT、去程与回程日期、限价
- **THEN** 规则保存至 SQLite 且列表可见

#### Scenario: 创建多段开口监控

- **WHEN** 用户选择多段/开口、添加 PVG→LAX 与 LAX→NRT 两段不同日期
- **THEN** 系统接受且返程终点不要求回到出发国

### Requirement: 全球机场选择

系统 SHALL 通过 RollingGo `airportsearch` 支持中文关键字与 IATA 编码选择全球机场；结果展示 MUST 优先中文城市名。

#### Scenario: 中文搜索机场

- **WHEN** 用户在机场输入框输入「洛杉矶」
- **THEN** 下拉包含 LAX 等匹配项

#### Scenario: IATA 直接输入

- **WHEN** 用户输入「NRT」
- **THEN** 系统接受为有效机场编码

### Requirement: 监控列表与历史

系统 SHALL 在列表页展示每条 Watch 的最近价格、provider、距限价差额、下次执行时间；详情页 MUST 展示历史快照列表。

#### Scenario: 查看最近查价

- **WHEN** 某 Watch 至少执行过一次查价
- **THEN** 列表显示最近一次 price 与 checked_at

### Requirement: 预设库导入

系统 SHALL 提供预设库 API 与 UI，包含 15 条达美开口示例；用户 MUST 可一键导入为可编辑 Watch。

#### Scenario: 导入预设

- **WHEN** 用户点击导入 `delta-pvg-lax-nrt-27spring-d0214`
- **THEN** 生成新 Watch 且默认 `enabled: false`

### Requirement: 设置页凭据

系统 SHALL 提供设置页配置 RollingGo、飞书 Webhook、PushPlus token；凭据 MUST 仅存本机 `.credentials.local.json` 且支持连通性测试。

#### Scenario: 保存凭据

- **WHEN** 用户保存 RollingGo Key 并点击测试
- **THEN** 显示连通成功或失败原因
