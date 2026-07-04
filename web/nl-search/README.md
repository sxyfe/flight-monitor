# NL Flight Search

特价机票搜索 Web 原型（**独立查价工具**）：中文描述 → LLM 解析 `SearchIntent` → RollingGo 查票 → 暖色报告可视化。与 Tauri 桌面监控无数据打通。

## 前置条件

- Python 3.10+
- RollingGo Flight API Key（`~/.cursor/mcp.json` 中 `RollingGo-Flight` 的 Bearer Token 亦可）
- 可选：OpenAI 兼容 LLM API（未配置时使用规则回退解析）

## 安装

```bash
cd web/nl-search
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 启动

项目根目录（**推荐**：统一网关，与线上一致，含 `/nl-search/`、`/flight-watch/` 等）：

```bash
npm run nl-search:dev
```

启动后访问：

| 路径                                | 说明           |
| ----------------------------------- | -------------- |
| http://127.0.0.1:8765/              | 官网首页       |
| http://127.0.0.1:8765/nl-search/    | 查价（本工具） |
| http://127.0.0.1:8765/flight-watch/ | 机票监控       |
| http://127.0.0.1:8765/skill/        | Skill          |

仅调试 nl-search 子应用（无 `/flight-watch/` 等子路径）：

```bash
cd web/nl-search
python3 -m uvicorn server:app --host 127.0.0.1 --port 8765
# 浏览器：http://127.0.0.1:8765/（/nl-search/ 会重定向到 /）
```

等价网关命令（自定义端口）：

```bash
PYTHONPATH=. WEB_ROOT=/nl-search python -m uvicorn web.gateway.server:app --reload --port 7860
```

## 配置

1. 点击右上角「设置」
2. 阅读页顶 **隐私说明**：Key 仅保存在本机，不会泄漏给开发者
3. 填写 RollingGo Base URL 与 API Key（👁 可切换明文显示）
4. （可选）填写 LLM Base URL、API Key、Model
5. （可选）启用「搜索次数软提示」并设置阈值（超过时在搜索栏显示警告，仍可继续）
6. 点击「测试 RollingGo / 测试 LLM」验证连接，再「保存配置」

凭据保存在 `web/nl-search/.credentials.local.json`（已 gitignore），仅本机使用。

## 前端依赖

- **Vue 3**（`static/vendor/vue.global.js`，含模板编译器）
- **shadcn 风格轻量组件**（`static/ui/`，无 Element Plus）
- **暖色报告模板**（`static/report/`，同步自 flight-monitor-agent Skill）
- **Chart.js**（CDN，与 Skill 报告一致）

`boot.js` 检测 Vue 是否就绪；表单 Tab 空白时请硬刷新（Mac：`Cmd+Shift+R`）。

## 使用流程

### 自然语言 Tab

1. 在输入框描述诉求，例如：

   > 京津出发，国庆前后去东南亚和日本，至少玩7天，最多玩14天，2500以内，往返和开口程都要

2. 解析按钮旁提示：配置 LLM 后大模型解析更准确
3. 点击「解析意图」，成功后自动切到表单 Tab 并预填条件（**原文保留不清空**）

### 表单 Tab

- 出发地/目的地：中文机场搜索（标签展示 IATA）
- 最少/最多停留、最高价格：三列并排（位于出发地下方）
- 国家与出发日期：紧凑并排；日期为原生 `<input type="date">`，**不可选今天之前**
- 下方只读参考月历：法定节假日高亮 + 国庆核心周；已过期日期灰显
- **查询字符串**：由表单自动生成，可编辑后点「重新解析」
- 核对后点击 **「开始搜索」**（自动校验意图，无需单独确认按钮）

### 搜索与结果

1. 选择 **智能精简** 或 **全量穷举**
2. 若启用软提示且预估超过阈值，搜索栏显示警告（不弹窗、不阻断）
3. 长搜索可点击 **「停止搜索」**，保留已命中结果
4. 搜索完成后展示 **flight-monitor-agent 暖色报告**：侧栏 chip 筛选、五图、去程/返程低价榜、明细分页

### 国庆日期语义

- 「国庆」→ `10-01` ~ `10-07`（若已过则滚动到下一年）
- 「国庆前后」→ `09-28` ~ `10-10`（同上 future-aware）

## 模式说明

| 模式                     | 说明                                         |
| ------------------------ | -------------------------------------------- |
| `smart`（智能精简）      | 按国家热门城市缩小目的地，适合快速探索       |
| `exhaustive`（全量穷举） | 等同 `scripts/exhaustive_search.py` 全量逻辑 |

## 相关文件

- `static/ui/` — shadcn 风格表单组件
- `static/report/` — 暖色报告（vend 自 Skill）
- `static/intent-query.js` — Intent ↔ 查询字符串
- `openspec/changes/nl-search-ui-v3/` — UI 升级 OpenSpec

## 开口程免责声明

开口程价格为两段单程最低价相加，`bookable: false`，不代表可联程预订。请以航司/OTA 实际报价为准。
