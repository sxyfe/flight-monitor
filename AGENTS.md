## Learned User Preferences

- 航班查询优先使用 RollingGo-Flight MCP；穷举搜索需覆盖各国主要机场城市、有效日期组合，并支持最少/最多停留天数等约束
- 分析项目已有搜索结果时优先重新调用 API 查价；`flight-monitor-agent` Skill 工作流除外，须实时 RollingGo 查价，不要读取 JSON 缓存（如 `scripts/exhaustive_results.json` 或 `scripts/exhaustive_results_snapshot_*.json`）；向用户介绍时称 **Cursor Skill**（非 Agent），包名 `flight-monitor-agent` 不变
- 特价检索需同时覆盖往返联票与开口程（去程 A→B、返程 C→D，出发/返回城市均在用户指定出发地集合内）
- OpenSpec 产物（proposal、design、tasks、specs）一律使用简体中文撰写
- `web/nl-search` 需支持自然语言与表单两种查询模式；多选字段采用 chip 内嵌于输入框；自然语言解析后展示对应表单结果，且解析成功不清空 NL 输入框原文；已移除「确认意图」按钮，点击「开始搜索」时自动校验当前表单意图
- 出发地与目的地均支持「中文搜索 + 机场/城市编码」选择；航线与路线展示优先中文城市名（非仅机场代码）
- 独立 Web 工具 **`web/nl-search`**（查价）与 **`web/flight-watch`**（监控）均与 Tauri 桌面无集成
- 「国庆」解析为 10-01~10-07；「国庆前后」解析为 9-28~10-10
- nl-search 日期区保留原生 `<input type="date">` 双控件（`min` 为今日，禁止选历史日期）；下方只读参考月历高亮法定节假日与国庆核心周，暖色 token 对齐 Element UI 方案 A
- 设置页单独展示 RollingGo/LLM 配置及连通性测试（RollingGo 测试须含机场搜索 + 航班查价探针）；API 密钥输入支持眼睛图标切换明文/密文；可选「搜索次数软提示」阈值（超过时在搜索栏警告，不阻断）；RollingGo 查价 API 失败时须提示「查价服务异常」，勿误导为「无命中」
- nl-search 结果区对齐 flight-monitor-agent 暖色报告（侧栏筛选 + 图表/列表联动）；列表展示航班号/日期/价格；图表 hover 中文明细；筛选侧栏自然铺满、避免内部滚动
- 桌面监控不提供返利或 OTA 跳转，只展示航班号与日期时间；降价通知默认 24 小时冷却，单用户最多 1 条监控

## Learned Workspace Facts

- 本仓库为 Flight Monitor：Tauri 桌面端 + RollingGo 航班监控，目标平台 Mac 与 Windows
- 穷举搜索：`scripts/exhaustive_search.py`（引擎版）与 `scripts/exhaustive_search_standalone.py`（京津独立版）；结果写入 `scripts/exhaustive_results.json`
- RollingGo 航班搜索 API 为 `https://mcp.rollinggo.cn/api/mcp/flightsearch`；MCP 服务名 `RollingGo-Flight`（streamable-http 需 `Accept: application/json, text/event-stream`）；Key 申请 [rollinggo.store](https://rollinggo.store/)；`totalAdultPrice` 通常为成人含税合计参考价（无票面/税费拆分）；响应常无 OTA 跳转且仅查价（`bookingUrl` 常为 null）；HTTP 200 但 `success: false` 为查价业务失败（非无票），引擎 `probe_flight_pricing` 用于连通性探针
- 独立开源 **Cursor Skill** `flight-monitor-agent`（`.cursor/skills/flight-monitor-agent/`）：纯查价、不提 Flight Monitor 桌面 App；NL 解析、`run_search.py` 精简/全量穷举实时查价、暖色 HTML 分页报告（去程/返程低价榜、动态城市映射）；先 [rollinggo.store](https://rollinggo.store/) 申请 Key，再 `npx skills add sxyfe/skills@flight-monitor-agent` 或 GitHub [sxyfe/skills](https://github.com/sxyfe/skills)；对用户说明「精简模式/全量穷举」（CLI 仍为 `--mode smart/exhaustive`）；宣传页 `promo/skill-intro-1080x1440.html` 与 `promo/xhs/`（1080×1440），嵌入 `output/` 真实报告截图、不写 Python 代码块；Skill 不含视频分镜或推广素材生成
- OpenSpec 工作流规范见 `openspec/AGENTS.md`；变更提案位于 `openspec/changes/`（含 `nl-search-results-analytics-v2`、`nl-search-max-stay-holiday`、`flight-watch-web`）
- 独立 Web 查价原型位于 `web/nl-search`（FastAPI + Vue CDN，默认 http://127.0.0.1:8765，**长期定位为独立查价工具**，与桌面监控无集成）；RollingGo Key 必填、LLM Key 可选（规则回退）；`SearchIntent` 含 `min_stay_days` 与可选 `max_stay_days`；全量穷举直接启动，设置页可选「搜索次数软提示」阈值（超过时在搜索栏警告，不弹窗阻断）；长搜索可停止并保留已命中结果；SSE 推送进度与命中；结果区复用 Skill 暖色报告模板
- `web/flight-watch` 为独立 Web 监控工具（FastAPI + Vue CDN，默认 http://127.0.0.1:8767，与 nl-search、Tauri 无集成）；OpenSpec 变更 `flight-watch-web`；支持全球 Watch 规则（往返/单程/多段/开口程）、飞书 + PushPlus 通知、APScheduler 进程内调度 + `POST /api/watch/run-once` cron 兜底；15 条达美开口预设（`presets/delta-open-jaw.json`）可一键导入；多段/开口优先 `swoop-flights` 同票价，失败则 RollingGo 分段 ONE_WAY 相加（`bookable: false`）
- `web/exhaustive-viz` 为穷举结果独立可视化页，软链读取 `exhaustive_results.json`，本地服务默认端口 8766
- 监控规则约定：每段行程固定一个日期；价格下降时通知，24h 冷却仅防止「价格不变且仍低于限价」重复推送
- RollingGo `airportsearch` 仅关键字搜索、不支持按国家列举全国机场；五国穷举城市来自 `scripts/data/country_city_codes.json`（`scripts/sync_country_airports.py` 从 OurAirports 按热度排序：`exhaustive`=前 50%、`hot`=前 8）；目录外国家走 API 多关键词回退；开口程引擎为两段 ONE_WAY 价相加，同票多段真价需 `swoop-flights` 等通道（ITA Matrix 无公开 API）
- Onboarding 可内置跳转 [rollinggo.store](https://rollinggo.store/) 申请页及图文说明
