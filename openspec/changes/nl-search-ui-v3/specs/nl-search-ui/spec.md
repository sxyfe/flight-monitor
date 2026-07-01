# nl-search-ui

## Requirements

### Requirement: shadcn 风格表单组件

意图编辑器 SHALL 使用 shadcn 风格轻量组件，不得依赖 Element Plus。

#### Scenario: 表单加载

- **WHEN** 用户打开「表单查询」Tab
- **THEN** 出发地/目的地/国家/日期/行程类型控件正常渲染且无 Element Plus 脚本

### Requirement: 紧凑国家与日期布局

国家多选与出发日期范围 SHALL 在同一紧凑行内展示，单项宽度不超过约 320px。

#### Scenario: 紧凑布局

- **WHEN** 桌面宽度 ≥768px
- **THEN** 国家与日期控件并排，不占据整行全宽

### Requirement: 查询字符串与重新解析

表单 SHALL 以可编辑中文查询字符串替代 SearchIntent JSON 展示。

#### Scenario: 重新解析

- **WHEN** 用户编辑查询字符串并点击「重新解析」
- **THEN** 系统调用 `/api/intent/parse` 并回填表单字段

#### Scenario: 确认门禁

- **WHEN** 查询字符串处于 queryDirty 且未重新解析
- **THEN** 「确认意图」SHALL 提示用户先重新解析或恢复自动同步

### Requirement: 暖色报告结果区

搜索完成后结果区 SHALL 采用 flight-monitor-agent 暖色报告布局（侧栏筛选、五图、去程/返程榜、明细分页）。

#### Scenario: 搜索完成

- **WHEN** SSE `completed` 事件到达
- **THEN** 结果区展示与 Skill 报告一致的筛选与表格交互

### Requirement: LLM 与隐私提示

自然语言 Tab SHALL 在解析按钮附近展示 LLM 解析准确性提示。设置页 SHALL 说明 API Key 仅保存在本机且不会泄漏给开发者。

#### Scenario: 隐私说明

- **WHEN** 用户打开设置页
- **THEN** 可见 Key 本地存储说明 callout
