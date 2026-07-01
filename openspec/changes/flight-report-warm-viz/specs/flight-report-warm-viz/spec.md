# flight-report-warm-viz

## Purpose

定义 flight-monitor-agent Skill HTML 报告的暖色统一 UI：侧栏筛选、Chart.js 图表、排序与全量分页。

## Requirements

### Requirement: 报告筛选与图表

HTML 报告 MUST 提供侧栏筛选：行程类型（全部/往返/开口程）、国家、目的地、出发城市、价格双滑块、价格 bucket、重置按钮。Chart.js 五图 MUST 随当前筛选集联动更新。

#### Scenario: 筛选国家

- **WHEN** 用户点击国家 chip
- **THEN** 表格与图表仅反映该国家相关命中
- **THEN** 分页重置为第 1 页

### Requirement: 报告排序

表格 MUST 支持按价格、目的地、出发日期、停留天数升序或降序排序。

#### Scenario: 按价格升序

- **WHEN** 用户选择「价格 ↑」
- **THEN** 分页结果按价格从低到高排列

### Requirement: 报告统一分页

筛选并排序后的全部命中 MUST 分页展示，提供上一页/下一页、每页条数、页码输入与跳转；不得仅展示 TOP N。

#### Scenario: 大量命中

- **WHEN** 筛选后结果超过单页条数
- **THEN** 用户可通过页码输入跳转到任意页
- **THEN** `#` 列显示全局序号

### Requirement: 报告视觉与范围

报告 MUST 采用暖色编辑风（与 demo-bilibili 一致 token）。MUST NOT 含桌面监控规则或 `monitor_suggestion` 区块。

#### Scenario: 生成报告

- **WHEN** 执行 `generate_flight_report.py`
- **THEN** 输出自包含 `report.html`（内嵌数据，不 fetch 外部 JSON）
- **THEN** 不含监控推荐 JSON 块
