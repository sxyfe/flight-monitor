# flight-monitor-agent Specification

## Purpose

定义 Cursor Agent Skill 在机票查价、缓存分析、HTML 报告与桌面监控建议方面的行为规范。

## Requirements

### Requirement: 缓存优先分析

系统 MUST 在用户仅要求分析已有结果时，只读取本地 JSON 缓存，不得调用 RollingGo API。

#### Scenario: 用户要求分析本地穷举结果

- **WHEN** 用户说「读本地穷举结果做分析」且 `scripts/exhaustive_results.json` 存在
- **THEN** Agent 读取该 JSON 并运行 `generate_flight_report.py`
- **THEN** Agent 不得调用 `exhaustive_search.py` 或 RollingGo MCP

### Requirement: 报告生成命令

系统 MUST 通过单条 CLI 命令生成 HTML 报告至 `output/reports/<run-id>/report.html`。

#### Scenario: 默认输出路径

- **WHEN** Agent 执行 `python3 scripts/generate_flight_report.py --input <json>` 且未指定 `--output`
- **THEN** 报告写入 `output/reports/<YYYYMMDD-HHMMSS>/report.html`
- **THEN** 同目录生成 `summary.json` 含 `total_hits`、`rt_count`、`oj_count`、`cheapest_price`

### Requirement: 报告数据一致性

报告页展示的命中总数、往返/开口程计数、最低价 MUST 与输入 JSON 归一化后的 offers 一致。

#### Scenario: exhaustive_results 格式

- **WHEN** 输入 JSON 含 `rt_hits` 与 `oj_hits` 数组
- **THEN** `total_hits` 等于两数组长度之和
- **THEN** 最低价等于全部 offer 中 `price` 最小值

### Requirement: 监控规则建议

系统 MUST 仅从 `trip_type=round_trip` 且 `bookable=true` 的 offer 生成监控建议。

#### Scenario: 开口程不可监控

- **WHEN** 最低价 offer 为 `open_jaw` 且 `bookable=false`
- **THEN** `monitor_suggestion.json` 使用最便宜的可订往返联票
- **THEN** Agent 向用户说明开口程不可作为联票监控

#### Scenario: MonitorRuleInput 字段对齐

- **WHEN** 生成监控建议
- **THEN** 输出含 `name`、`tripType`、`maxPrice`、`segments`、`returnDate`、`cabinGrade`
- **THEN** `segments[0].fromCity` / `toCity` / `fromDate` 与命中 offer 一致

### Requirement: Skill 与视频文档分离

`SKILL.md` MUST NOT 包含 B 站分镜、旁白、slides 或 storyboard 内容。

#### Scenario: 录屏材料外置

- **WHEN** 需要视频旁白或演示台词
- **THEN** 材料位于 `docs/video-bilibili-monitor.md`
- **THEN** Skill 仅引用该路径，不复制旁白正文

### Requirement: 域知识 — 日期语义

Agent MUST 将「国庆」解析为 10-01~10-07，「国庆前后」解析为 9-28~10-10。

### Requirement: 域知识 — 桌面监控约束

Agent MUST 告知用户：单用户最多 1 条监控规则、降价通知 24h 冷却、不提供 OTA 跳转。
