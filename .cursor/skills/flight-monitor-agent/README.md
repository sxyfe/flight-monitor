# flight-monitor-agent

RollingGo 航班实时查价 Agent Skill：自然语言 → 精简/全量穷举查价 → 分页 HTML 报告。

[中文](#中文) · [English](#english)

---

## 中文

### 功能

- 自然语言解析为 SearchIntent（国庆/国庆前后、多国、预算）
- **精简模式**：热门城市子集，快速扫价（命令行 `--mode smart`）
- **全量穷举**：覆盖全部配置城市（命令行 `--mode exhaustive`，高 API 成本，需确认）
- 往返联票 + 开口程（A→B + C→D，A/D 在出发地集合内）
- 暖色 HTML 报告：侧栏筛选、Chart.js 图表、排序、筛选后全量分页与页码跳转

### 快速开始

**要求**：Python 3.8+，RollingGo API Key

1. **申请 Key**：[rollinggo.store](https://rollinggo.store/)
2. **配置**：

```bash
cp .env.example .env
# 编辑 .env，填入 ROLLINGGO_API_KEY=mcp_...
```

3. **自检**：

```bash
python3 scripts/check_rollinggo.py
```

4. **解析 + 查价 + 报告**：

```bash
python3 scripts/parse_nl_intent.py -q "北京出发泰国菲律宾国庆特价2500以内" \
  --rules-only -o /tmp/payload.json

# 精简模式查价
python3 scripts/run_search.py --intent /tmp/payload.json --mode smart \
  --output output/search_result.json

python3 scripts/generate_flight_report.py --input output/search_result.json
```

### 精简模式 vs 全量穷举

| | 精简模式 | 全量穷举 |
|---|----------|----------|
| 命令行 | `--mode smart` | `--mode exhaustive` |
| 目的地 | 各国热门城市 | 全量城市 |
| API 次数 | 较少 | 可能数千 |
| 适用 | 日常扫价 | 深度穷举 |

预估 **>500 次** 时，`run_search.py` 需要加 `--confirm` 才会执行（全量穷举常见）。

### 反滥用声明

本工具供个人开发者与 Agent 进行**合理**机票查价与比价分析。RollingGo API Key 有使用边界，**请勿**：

- 高频自动化刷接口
- 将 Key 公开分享给他人或公共服务
- 绕过确认机制批量穷举

### Cursor / MCP（可选）

复制 `templates/mcp.json.example` 到 `~/.cursor/mcp.json` 并填入 Key。Python 脚本优先读取 `.env`。

### 安装为 Skill

**推荐（skills.sh）：**

```bash
npx skills add sxyfe/skills@flight-monitor-agent -g -y
```

源码仓库：[github.com/sxyfe/skills](https://github.com/sxyfe/skills) · [skills.sh/sxyfe/skills](https://skills.sh/sxyfe/skills)

**手动 symlink（Cursor）：**

```bash
ln -s "$(pwd)" ~/.cursor/skills/flight-monitor-agent
```

### License

MIT — 见 [LICENSE](LICENSE)

---

## English

### Features

- Natural language → SearchIntent (holidays, multi-country, budget)
- **Compact scan** (`--mode smart`): hot-city subset for quick price checks
- **Full sweep** (`--mode exhaustive`): all configured cities (high API cost, confirmation required)
- Round-trip + open-jaw (outbound A→B, return C→D; A and D must be in origin set)
- Warm editorial HTML report: sidebar filters, Chart.js charts, sort, paginated filtered results with page jump

### Quick Start

**Requires**: Python 3.8+, RollingGo API Key

1. **Get a Key**: [rollinggo.store](https://rollinggo.store/)
2. **Configure**:

```bash
cp .env.example .env
# Set ROLLINGGO_API_KEY=mcp_...
```

3. **Health check**:

```bash
python3 scripts/check_rollinggo.py
```

4. **Parse → search → report**:

```bash
python3 scripts/parse_nl_intent.py -q "Beijing to Thailand Philippines National Day under 2500 CNY" \
  --rules-only -o /tmp/payload.json

python3 scripts/run_search.py --intent /tmp/payload.json --mode smart \
  --output output/search_result.json

python3 scripts/generate_flight_report.py --input output/search_result.json
```

### Compact scan vs full sweep

| | Compact (`smart`) | Full sweep (`exhaustive`) |
|---|-------------------|---------------------------|
| Destinations | Hot cities per country | All configured cities |
| API calls | Lower | Can be thousands |
| Use case | Daily price scan | Deep exhaustive search |

When estimated calls **exceed 500**, `run_search.py` requires `--confirm`.

### Fair Use

This tool is for **reasonable** flight price research by individuals and agents. RollingGo API keys have usage limits. **Do not**:

- Automate high-frequency scraping
- Share your key publicly or in multi-tenant services
- Bypass confirmation for bulk full-sweep runs

### Cursor / MCP (optional)

Copy `templates/mcp.json.example` to `~/.cursor/mcp.json`. Scripts prefer `.env` first.

### Install as Skill

**Recommended (skills.sh):**

```bash
npx skills add sxyfe/skills@flight-monitor-agent -g -y
```

Source: [github.com/sxyfe/skills](https://github.com/sxyfe/skills) · [skills.sh/sxyfe/skills](https://skills.sh/sxyfe/skills)

**Manual symlink (Cursor):**

```bash
ln -s "$(pwd)" ~/.cursor/skills/flight-monitor-agent
```

### License

MIT — see [LICENSE](LICENSE)
