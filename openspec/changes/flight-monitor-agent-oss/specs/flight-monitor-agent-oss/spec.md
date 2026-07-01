# flight-monitor-agent-oss Specification

## Purpose

定义独立开源 `flight-monitor-agent` Skill 的配置、实时查价、模式确认、报告与合规行为规范。

## Requirements

### Requirement: Key 前置条件

系统 MUST 在无有效 `ROLLINGGO_API_KEY` 时拒绝执行查价，并提示用户在 [rollinggo.store](https://rollinggo.store/) 申请 Key。

#### Scenario: 无 Key 执行查价

- **WHEN** 用户或 Agent 调用 `run_search.py` 且未配置 Key
- **THEN** 进程以非零退出码结束
- **THEN** stderr 输出 rollinggo.store 申请链接与 `.env` 配置说明

### Requirement: 配置加载

系统 MUST 通过 `scripts/config.load_settings()` 加载配置，优先级为环境变量 > 仓库 `.env` > `~/.cursor/mcp.json`。

#### Scenario: 从 .env 加载

- **WHEN** 仓库根目录存在 `.env` 且含 `ROLLINGGO_API_KEY`
- **THEN** `load_settings()` 返回该 Key 与 `ROLLINGGO_BASE_URL`（默认 `https://mcp.rollinggo.cn`）

### Requirement: 实时查价

系统 MUST 在用户发起查价时调用 RollingGo API，不得使用历史 `exhaustive_results.json` 或 snapshot 代替实时结果。

#### Scenario: 用户请求查价

- **WHEN** 用户提出查价诉求且 Key 已配置
- **THEN** Agent 执行 `run_search.py` 或 MCP 单次补查
- **THEN** Agent 不得仅读取本地历史 JSON 作为价格答复

### Requirement: 查价模式选择

系统 MUST 提供 `smart`（热门城市子集）与 `exhaustive`（全量穷举）两种模式，并在执行前向用户展示两种模式的预估 API 次数。

#### Scenario: 解析意图后展示预估

- **WHEN** `parse_nl_intent.py` 成功解析 SearchIntent
- **THEN** 输出含 `estimated_queries_smart` 与 `estimated_queries_exhaustive`

### Requirement: 高成本确认

当所选模式预估 API 次数大于 500 时，系统 MUST 在用户未明确确认（CLI `--confirm`）时拒绝执行查价。

#### Scenario: 超阈值未确认

- **WHEN** `run_search.py --mode exhaustive` 且预估次数 > 500 且无 `--confirm`
- **THEN** 进程拒绝执行并以非零退出码结束
- **THEN** 提示用户确认或使用 smart 模式

### Requirement: 开口程语义

开口程组合 MUST 为去程 A→B、返程 C→D，其中 A 与 D 属于用户指定出发地集合，B 与 C 为目的地城市。

#### Scenario: 京津出发开口程

- **WHEN** origins 为 `BJS, TSN` 且引擎组合 open_jaw
- **THEN** 允许 `北京→曼谷` + `普吉→天津`
- **THEN** 不允许去程从非 origins 城市出发

### Requirement: 报告分页

HTML 报告 MUST 通过侧栏行程筛选与统一表格展示全部命中；筛选并排序后的结果 MUST 分页展示，并提供上一页/下一页、每页条数选择与页码输入跳转。Chart.js 图表 MUST 随筛选联动更新。

#### Scenario: 大量命中

- **WHEN** 查价结果超过单页默认条数
- **THEN** 报告页提供上一页/下一页、每页条数选择与页码跳转
- **THEN** 不得仅展示 TOP N 而隐藏其余结果
- **THEN** 侧栏提供国家/目的地/出发地/价格区间等筛选控件

### Requirement: 纯查价范围

Skill 文档与脚本 MUST NOT 生成桌面监控规则、引用 Flight Monitor App 或 `monitor_suggestion.json`。

#### Scenario: 生成报告

- **WHEN** 执行 `generate_flight_report.py`
- **THEN** 输出 `report.html` 与 `summary.json`
- **THEN** 不得写入 `monitor_suggestion.json`

### Requirement: 文档语言

`SKILL.md` MUST 使用简体中文；`README.md` MUST 提供中文与英文说明。

### Requirement: 反滥用声明

`SKILL.md` 与 `README.md` MUST 声明本工具非免费无限 API 滥用工具，禁止高频刷接口、公开共享 Key、绕过确认机制批量穷举。
