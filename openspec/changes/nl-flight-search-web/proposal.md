## Why

当前 `exhaustive_search.py` 只能通过硬编码参数全量穷举查票，门槛高、耗时长（2500+ 次 API、20–40 分钟），且结果仅以 JSON 文件呈现，普通用户难以用自然语言表达诉求并快速对比方案。需要一套**独立 Web 原型**：用自然语言描述机票需求，经 LLM 解析与规则校验后调用 RollingGo，再以表格与多维图表帮助用户决策。

## What Changes

- 新增 `web/nl-search/` 独立 Web 原型目录（FastAPI 后端 + 静态 HTML 前端），与现有 Tauri 桌面端**并行存在**，不修改监控主流程。
- 从 `exhaustive_search.py` 抽取可复用**航班查询引擎**（城市表、日期校验、RollingGo HTTP 客户端、RT/开口程聚合），支持 `smart`（窄范围）与 `exhaustive`（全量）两种模式。
- 新增 **NL 解析层**：用户输入中文自然语言 → LLM 输出结构化 `SearchIntent` JSON → 代码层二次校验（日期、停留天数、城市解析、查询量预估）。
- 新增 **REST API**：配置凭据、解析诉求、发起搜索（支持 SSE 进度）、获取结果与聚合统计。
- 新增 **可视化页面**：配置 RollingGo / LLM 双 Base URL 与 API Key；结构化诉求预览；结果表格（可排序筛选）；价格带、停留天数、目的地、行程类型等维度图表；推荐卡片（最便宜 / 最省心 / 玩最多天）。
- 明确区分**往返联票**与**开口程分段价**，UI 不得将开口程表述为「可直接预订联票」。
- **不**在本变更中实现：Tauri 集成、用户账号体系、支付跳转、生产环境公网部署。

## Capabilities

### New Capabilities

- `flight-search-engine`: 从自然语言解析后的 `SearchIntent` 生成查询计划、调用 RollingGo、聚合 RT/开口程结果
- `nl-query-parser`: LLM 自然语言解析、结构化输出、规则校验与澄清追问
- `nl-search-api`: FastAPI 服务、凭据管理、搜索任务与 SSE 进度、结果聚合 API
- `nl-search-ui`: 独立 HTML 配置页、搜索交互、表格与多维数据可视化

### Modified Capabilities

（无。本项目尚无 `openspec/specs/` 基线能力文档。）

## Impact

- **新增代码**：`web/nl-search/`（Python 后端、`static/` 前端）、`scripts/flight_search_engine.py`（自 `exhaustive_search.py` 抽取）
- **可选重构**：`exhaustive_search.py` 改为调用引擎的 CLI 包装，避免逻辑重复
- **依赖**：Python 3.10+、`fastapi`、`uvicorn`、`httpx` 或 `urllib`、可选 `openai` SDK（OpenAI 兼容 LLM）
- **外部系统**：[RollingGo API](https://mcp.rollinggo.cn)、用户自选 LLM 提供商（OpenAI 兼容 Base URL）
- **不受影响**：Tauri 桌面端、SQLite 监控规则、飞书通知、现有 Vue 前端
