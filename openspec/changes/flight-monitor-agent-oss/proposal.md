## Why

`flight-monitor-agent` Skill 将独立开源，需脱离 flight-monitor monorepo、统一 RollingGo Key 申请与配置方式，并在查价前提供 smart/exhaustive 模式选择与成本确认，避免 API 滥用。

## What Changes

- **BREAKING**：Skill 不再依赖 monorepo `scripts/flight_search_engine.py` 与 `_project.py`，引擎 vendored 至 Skill 仓库内
- **BREAKING**：移除桌面监控 / `monitor_suggestion.json` / Flight Monitor App 相关文档与脚本逻辑
- **BREAKING**：用户查价必须实时调用 RollingGo API，禁止以历史 JSON 缓存代替
- 新增 `.env` / `ROLLINGGO_API_KEY` 配置与 `scripts/config.py` 统一加载
- 新增 `scripts/check_rollinggo.py` 连通性自检
- `run_exhaustive.py` 演进为 `run_search.py`，支持 `--mode smart|exhaustive`、`--confirm` 高成本门槛
- 新增独立仓库 `README.md`（中英双语）、`.env.example`、`templates/mcp.json.example`
- 统一 Key 申请入口为 [rollinggo.store](https://rollinggo.store/)
- HTML 报告保留全量分页 + 页码跳转，移除监控推荐区块

## Capabilities

### New Capabilities

- `flight-monitor-agent-oss`：独立开源 Skill 的查价、配置、模式确认、报告与反滥用规范

### Modified Capabilities

（无 — 旧 `flight-monitor-agent` change 已完成，本 change 以新 capability 承载）

## Impact

- **新增/修改**：`.cursor/skills/flight-monitor-agent/` 全目录结构、OpenSpec change `flight-monitor-agent-oss`
- **后续**：独立 GitHub 仓库 `flight-monitor-agent`；monorepo 文档链接指向外部 repo
- **不受影响**：Tauri 桌面端、nl-search、xhs-cards

## Non-Goals

- 不打包 Flight Monitor 桌面客户端
- 不发布 npm/pypi 包
- 不实现 OTA 跳转 / bookingUrl
