# B 站横屏推广视频：机票监控 + Agent Skill

> 本文档为**人工录屏**用旁白与 Agent 演示台词。  
> **不**写入 `.cursor/skills/flight-monitor-agent/SKILL.md`。

## 视频信息

| 项 | 值 |
|----|-----|
| 平台 | B 站横屏 16:9 |
| 时长 | 约 4–5 分钟 |
| 叙事重心 | 桌面监控为主；Agent Skill 为「查价 → 报告 → 录入监控」演示 |
| CTA | [rollinggo.store](https://rollinggo.store) 申请 API Key |

---

## 分镜与旁白

### 第一幕：痛点 + 监控是什么（0:00–1:00）

**画面**：Tauri Dashboard 录屏 — 已有监控规则、轮询状态、价格历史。

**旁白**：

> 国庆、寒暑假的机票，价格天天变。你盯一次 OTA，过两天又涨了。  
> Flight Monitor 做的是：**选定航线后持续轮询**，只有**真的降价**才通知你。  
> 同一条规则 24 小时冷却，避免同价反复打扰；桌面端只展示航班号和日期，不跳 OTA。

**镜头清单**：

- [ ] Dashboard 规则列表
- [ ] 轮询中 / 上次查价时间
- [ ] 通知记录（或 mock 降价推送）

---

### 第二幕：案例从哪来（1:00–1:45）

**画面**：简短展示 `exhaustive_results.json` 或 `report.html` 概览数字（不必展开穷举细节）。

**旁白**：

> 监控之前，得先找到「值得盯」的票。  
> 可以手搓脚本穷举，也可以用 **Agent + Skill**：自然语言描述诉求，自动读缓存、出可视化报告。  
> 下面演示这条链路。

**镜头清单**：

- [ ] 终端 `wc -l scripts/exhaustive_results.json` 或报告页统计卡片（3 秒）

---

### 第三幕：重点 — Agent + Skill 演示（1:45–3:30）

**画面**：Cursor / Claude Code / Codex 任一，挂载 `flight-monitor-agent` Skill。

#### 演示台词 A（读缓存 + 报告）

**用户（口述或打字）**：

```
国庆前后东南亚特价，京津出发，预算 2500，先读本地穷举结果做分析。
```

**Agent 预期动作**（录屏需拍到）：

1. 读取 `scripts/exhaustive_results.json`（**不调 API**）
2. 终端执行：
   ```bash
   python3 scripts/generate_flight_report.py \
     --input scripts/exhaustive_results.json
   ```
3. 浏览器打开 `output/reports/<timestamp>/report.html`
4. 中文汇报：往返 N 条、开口程 M 条、最低价

**旁白**：

> 注意 Agent **优先读本地缓存**，分析场景不会无谓打 API。  
> 一条命令生成 HTML 报告：价格分布、目的地 TOP、往返/开口程 Tab 切换。

**镜头时长建议**：终端 15s · 浏览器报告 25s · Agent 文字回复 10s

#### 演示台词 B（监控规则）

**用户**：

```
往返联票里最省心的一条，帮我写成监控规则。
```

**Agent 预期动作**：

1. 读取 `monitor_suggestion.json` 或从报告推荐块复制
2. 输出 `MonitorRuleInput` JSON（`tripType: round_trip`，含 `returnDate`）
3. 提示：开口程不可当联票监控

**旁白**：

> Skill 只推荐 **可订往返联票**。开口程是分段最低价相加，不能当一张票监控。

**镜头时长建议**：JSON 片段 15s

---

### 第四幕：桌面监控收尾（3:30–4:30）

**画面**：Tauri `MonitorForm` 按 Skill 建议填表 → 保存 → 轮询 → 通知。

**旁白**：

> 把 Skill 给的字段填进桌面监控：出发、到达、去程日期、回程日期、限价。  
> 保存后后台自动轮询；价格跌破限价就推送到你配置的 Webhook。  
> 免费 Key 在 rollinggo.store 申请，Onboarding 里有图文说明。

**镜头清单**：

- [ ] MonitorForm 填写（与 JSON 字段一一对应）
- [ ] 保存成功 / 轮询启动
- [ ] Onboarding 申请 Key 入口（可选 5s）

---

### 第五幕：收尾 CTA（4:30–5:00）

**画面**：Logo + 下载链接 + rollinggo.store。

**旁白**：

> 查价用 Agent，盯价用桌面。链接在简介。

---

## Agent 演示脚本（完整版，给人照着念）

```
【挂载 Skill】
在 Cursor 中确保项目已加载 .cursor/skills/flight-monitor-agent

【第一轮】
用户：国庆前后东南亚特价，京津出发，预算 2500，先读本地穷举结果做分析。
Agent：[读 exhaustive_results.json] → [generate_flight_report] → 打开 report.html
      → 汇报命中条数与最低价

【第二轮】
用户：往返联票里最省心的一条，帮我写成监控规则。
Agent：输出 monitor_suggestion.json → 说明各字段含义 → 提醒单用户 1 条规则

【切换画面】
Tauri：按 JSON 填入 MonitorForm → 保存 → 展示轮询状态
```

---

## 录屏技术清单

| 工具 | 用途 |
|------|------|
| OBS / 系统录屏 | B 站横屏 1920×1080 |
| Cursor | Agent 演示 |
| 浏览器 | `report.html` |
| Tauri 桌面端 | 监控录入与轮询 |

**检查项**：

- [ ] `report.html` 数字与 JSON 一致（总命中、往返/开口程计数）
- [ ] 演示全程分析场景未触发 RollingGo API
- [ ] 监控规则为 `round_trip` + `bookable` 路线
- [ ] 旁白与 Skill 文档分离（Skill 无视频章节）

---

## 可选：预生成报告路径

录屏前可预先跑一遍，固定输出目录：

```bash
python3 scripts/generate_flight_report.py \
  --input scripts/exhaustive_results.json \
  --output output/reports/demo-bilibili
```

打开：`output/reports/demo-bilibili/report.html`

---

## 与 Skill 的边界

| 归属 | 内容 |
|------|------|
| `flight-monitor-agent` Skill | 查价、读缓存、报告、监控字段 |
| 本文档 | 旁白、分镜、录屏节奏、演示台词 |
| `output/rollinggo-xhs-cards` | 小红书竖卡（独立营销资产） |
