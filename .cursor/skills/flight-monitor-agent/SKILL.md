---
name: flight-monitor-agent
description: >-
  机票实时查价助手：RollingGo 查价、精简/全量穷举模式、HTML 分页报告。
  用于东南亚/日本特价、开口程、国庆日期窗等自然语言查价。纯查价 Skill，不含桌面监控。
---

# Flight Monitor Agent

自然语言 → **实时 RollingGo 查价** → 分页 `report.html`。

## 前置条件（必读）

1. 在 **[rollinggo.store](https://rollinggo.store/)** 申请 RollingGo MCP API Key（格式 `mcp_...`）
2. 复制 `.env.example` 为 `.env`，填入 `ROLLINGGO_API_KEY`
3. 运行连通性检查：

```bash
python3 scripts/check_rollinggo.py
```

**无 Key 时**：禁止调用 `run_search.py`；必须提示用户前往 rollinggo.store 申请并配置 `.env`。

可选：Cursor 用户可将 Key 写入 `~/.cursor/mcp.json`（见 `templates/mcp.json.example`），脚本会作为回退读取。

## 反滥用

本 Skill **不是**免费无限 API 的滥用工具。禁止：高频自动化刷接口、公开共享 Key、绕过确认机制批量穷举。大量查询前须让用户选择 **精简模式** 或明确 **--confirm**。

## 何时使用

- 用户要查多国特价、开口程、往返联票
- 用户提到国庆/国庆前后 + 出发地 + 预算

## 工作流

### 1. 解析意图

```bash
python3 scripts/parse_nl_intent.py \
  -q "国庆前后东南亚，京津出发，2500以内" \
  --rules-only --intent-only
```

输出含**精简模式**与**全量穷举**两种预估 API 次数与耗时（脚本 JSON 字段分别为 `estimated_queries_smart`、`estimated_queries_exhaustive`）。

### 2. 模式选择与用户确认

| 模式 | 说明 | 命令行 `--mode` |
|------|------|-----------------|
| **精简模式** | 各国热门城市子集，适合快速扫价（推荐日常使用） | `smart` |
| **全量穷举** | 覆盖配置内全部城市，API 次数多、耗时长 | `exhaustive` |

**Agent MUST**：
1. 向用户展示两种模式的预估 API 次数与约计耗时（用中文说明，勿对用户说英文模式名）
2. 让用户在**精简模式**与**全量穷举**中二选一
3. 若选定模式预估 **>500 次** 且无用户明确确认 → **拒绝执行**

### 3. 实时查价

**禁止**读取历史 `exhaustive_results.json` 代替查价。

```bash
# 仅预估
python3 scripts/run_search.py --intent /tmp/intent.json --mode smart --estimate-only

# 查价（精简模式）
python3 scripts/run_search.py --intent /tmp/intent.json --mode smart \
  --output output/search_result.json

# 全量穷举：预估超 500 次时需 --confirm
python3 scripts/run_search.py --intent /tmp/intent.json --mode exhaustive --confirm \
  --output output/search_result.json
```

### 4. 开口程规则

去程 **A→B**，返程 **C→D**：

| 端点 | 约束 |
|------|------|
| A、D | 必须在用户出发地集合内 |
| B、C | 任意目的地（可不同，实现开口） |

价格为两段单程最低价相加，`bookable: false`。

### 5. 生成 HTML 报告

```bash
python3 scripts/generate_flight_report.py \
  --input output/search_result.json
```

报告为暖色编辑风自包含 HTML，含：

- 侧栏筛选：行程类型、国家、目的地、出发地、价格区间与价格档位
- Chart.js 五图（随筛选联动）
- 表格排序 + **筛选后全量分页**（上一页/下一页、每页条数、页码跳转）
- 列：序号、类型、路线、日期、价格、可订、航班详情

### 6. 交付清单（中文）

- Key 与查价模式说明（精简 / 全量穷举）
- 预估/实际 API 次数
- 命中：往返 N / 开口程 M / 最低价
- 报告路径：`output/reports/<timestamp>/report.html`

## 域知识

### RollingGo

- API：`https://mcp.rollinggo.cn/api/mcp/flightsearch`
- MCP 服务名：`RollingGo-Flight`（单次补查可用）
- streamable-http 需 `Accept: application/json, text/event-stream`

### 日期语义

| 表述 | 日期窗 |
|------|--------|
| 国庆 | 10-01 ~ 10-07 |
| 国庆前后 | 09-28 ~ 10-10 |

### 路线展示

- 往返：`北京 ⇄ 曼谷`
- 开口程：`天津 → 马尼拉 · 棉兰 → 天津` 或者 ：`北京 → 曼谷 · 普吉 → 天津` 或者：`北京 → 曼谷 · 曼谷 → 天津`

## 脚本一览

| 脚本 | 作用 |
|------|------|
| `config.py` | `.env` / Key 加载 |
| `check_rollinggo.py` | 连通性自检 |
| `parse_nl_intent.py` | 自然语言 → SearchIntent |
| `run_search.py` | 精简 / 全量穷举实时查价 |
| `generate_flight_report.py` | 分页 HTML 报告 |
| `flight_search_engine.py` | 查价引擎 |

## 禁止事项

- 不要用历史 JSON 缓存代替实时查价
- 不要生成桌面监控规则或提及 Flight Monitor App
- 不要跳过用户模式选择与高成本确认

## 示例

**用户**：北京出发，日本菲律宾国庆期间航班价格。

**Agent**：

1. `parse_nl_intent.py` 解析意图
2. 展示精简模式与全量穷举的预估次数，请用户选择
3. `run_search.py --mode smart` 或 `--mode exhaustive` 查价（对用户只说明中文模式名）
4. `generate_flight_report.py` 出报告并汇报 summary

---
