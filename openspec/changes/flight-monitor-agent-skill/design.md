## Context

Flight Monitor 桌面端负责持续轮询与降价通知；穷举脚本与 JSON 缓存承载特价发现。推广视频以监控为主叙事，Agent Skill 作为录屏中演示的可操作能力。

## Goals / Non-Goals

**Goals:**

- Agent 可仅凭自然语言完成：读缓存 → 生成 HTML 报告 → 输出 `MonitorRuleInput` 建议
- 报告数字与 JSON 一致；分析场景优先缓存
- Skill 与视频文档职责分离

**Non-Goals:**

- 视频素材自动化、分镜生成
- 修改 Tauri 监控引擎或 nl-search 核心

## Decisions

### 1. Skill 定位为操作工作流，非内容生成器

- **理由**：用户明确 Skill 是视频中演示的查价/报告能力，旁白由人工维护
- **替代**：将分镜写入 Skill — 已否决

### 2. 报告页用 Python 单文件模板 + 静态 HTML

- **理由**：Agent 需「一条命令 → 稳定 HTML」；shadcn/React 增加构建链，对录屏无收益
- **视觉**：延续 xhs-cards coral/teal 编辑风，CSS 变量即可

### 3. 缓存优先决策树

```
分析诉求 / JSON 覆盖 → 只读 JSON
用户要求重查 / 缓存缺失 → exhaustive_search 或 MCP（需确认）
```

### 4. 监控建议仅来自 `round_trip` + `bookable: true`

开口程为分段最低价相加，不可当联票监控。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| `aggregate()` 要求 offer `id` | `normalize_offers` 注入合成 id |
| 穷举 JSON 体积大 | 报告只展示 TOP N 行 |
| 缓存与诉求日期窗不一致 | Agent 应提示用户或触发重查 |

## Migration Plan

1. 合并 Skill + 脚本 + 文档
2. 用现有 `exhaustive_results.json` 跑通 `generate_flight_report.py`
3. 录屏前可固定 `--output output/reports/demo-bilibili`

## Open Questions

- 是否未来将 `report.html` 嵌入 nl-search（可复用 Element Plus，非本变更范围）
