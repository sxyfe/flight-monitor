## Learned User Preferences

- 航班查询优先使用 RollingGo-Flight MCP；穷举搜索需覆盖各国主要机场城市、有效日期组合，并支持最少/最多停留天数等约束
- 分析项目已有搜索结果时优先重新调用 API 查价；`flight-monitor-agent` Skill 工作流除外，须实时 RollingGo 查价，不要读取 JSON 缓存（如 `scripts/exhaustive_results.json` 或 `scripts/exhaustive_results_snapshot_*.json`）；向用户介绍时称 **Skill**（非 Agent），包名 `flight-monitor-agent` 不变
- 特价检索需同时覆盖往返联票与开口程（去程 A→B、返程 C→D，出发/返回城市均在用户指定出发地集合内）
- OpenSpec 产物（proposal、design、tasks、specs）一律使用简体中文撰写
- `web/nl-search` 需支持自然语言与表单两种查询模式；多选字段采用 chip 内嵌于输入框；自然语言解析后展示对应表单结果，且解析成功不清空 NL 输入框原文；已移除「确认意图」按钮，点击「开始搜索」时自动校验当前表单意图；**价格矩阵**支持「独立范围」（去程/返程各起止）与「共用窗口」双模式、按路线独立色阶（深浅仅表该矩阵内相对高低）、最少/最多停留天数；矩阵行列日期须完整展示，卡片布局按矩阵尺寸自适应（不强制一行三列），移动端可横滑与点击 tooltip；机场搜索空结果固定文案「未搜索到机场」
- 出发地与目的地均支持「中文搜索 + 机场/城市编码」选择；航线与路线展示优先中文城市名（非仅机场代码）
- **后续开发仅 Web 端**（`web/nl-search`、`web/flight-watch`、`web/billing`、`web/landing`、`web/gateway`、`web/exhaustive-viz`）；勿改 Tauri 桌面端
- 「国庆」解析为 10-01~10-07；「国庆前后」解析为 9-28~10-10
- nl-search 日期区保留原生 `<input type="date">` 双控件（`min` 为今日，禁止选历史日期）；下方只读参考月历高亮法定节假日与国庆核心周，暖色 token 对齐 Element UI 方案 A
- 设置页单独展示 RollingGo/LLM 配置及连通性测试（RollingGo 测试须含机场搜索 + 航班查价探针）；API 密钥输入支持眼睛图标切换明文/密文；可选「搜索次数软提示」阈值（超过时在搜索栏警告，不阻断）；RollingGo 查价 API 失败时须提示「查价服务异常」，勿误导为「无命中」
- nl-search 结果区对齐 flight-monitor-agent 暖色报告（侧栏筛选 + 图表/列表联动）；列表展示航班号/日期/价格；图表 hover 中文明细；筛选侧栏自然铺满、避免内部滚动
- Flight Monitor Web 迭代优先方向 A（商业化）：可自主选型实现、自测迭代；每完成一项 Web 功能即 git commit 并 push 备份
- **会员订阅**（`web/billing`）：六档套餐（免费试用 7 天、一周/两周/月度/年度/永久）；注册自动开通试用；`BILLING_ENABLED=false` 可关闭门禁（本地开发）；Stripe 支付（`STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` + `PUBLIC_BASE_URL`），未配置 Stripe 时 Mock 支付；Cookie `fm_token` 跨子路径鉴权；查价/监控按套餐限制日搜索次数与 Watch 条数

## Learned Workspace Facts

- 本仓库 Flight Monitor 当前迭代主线为 Web：`web/gateway` 统一挂载 landing、`/nl-search/`、`/flight-watch/`、`/billing/`、`/viz/`、`/skill/`；`web/billing` 提供注册/登录、Stripe/Mock 支付与套餐权益；生产部署 Render（`flight-monitor-web.onrender.com`）；Tauri 桌面端存量存在、非当前开发范围
- 穷举搜索：`scripts/exhaustive_search.py`（引擎版）与 `scripts/exhaustive_search_standalone.py`（京津独立版）；结果写入 `scripts/exhaustive_results.json`
- RollingGo 航班搜索 API 为 `https://mcp.rollinggo.cn/api/mcp/flightsearch`；MCP 服务名 `RollingGo-Flight`（streamable-http 需 `Accept: application/json, text/event-stream`）；Key 申请 [rollinggo.store](https://rollinggo.store/)；`totalAdultPrice` 通常为成人含税合计参考价（无票面/税费拆分）；响应常无 OTA 跳转且仅查价（`bookingUrl` 常为 null）；HTTP 200 但 `success: false` 为查价业务失败（非无票），引擎 `probe_flight_pricing` 用于连通性探针
- 独立开源 **Skill** `flight-monitor-agent`（`.cursor/skills/flight-monitor-agent/`）：纯查价、不提 Flight Monitor 桌面 App；NL 解析、`run_search.py` 精简/全量穷举实时查价、暖色 HTML 分页报告（去程/返程低价榜、动态城市映射）；先 [rollinggo.store](https://rollinggo.store/) 申请 Key，再 `npx skills add sxyfe/skills@flight-monitor-agent` 或 GitHub [sxyfe/skills](https://github.com/sxyfe/skills)；对用户说明「精简模式/全量穷举」（CLI 仍为 `--mode smart/exhaustive`）；宣传页 `promo/skill-intro-1080x1440.html` 与 `promo/xhs/`（1080×1440），嵌入 `output/` 真实报告截图、不写 Python 代码块；Skill 不含视频分镜或推广素材生成
- OpenSpec 工作流规范见 `openspec/AGENTS.md`；变更提案位于 `openspec/changes/`（含 `nl-search-results-analytics-v2`、`nl-search-max-stay-holiday`、`nl-search-price-matrix`、`flight-watch-web`）
- 独立 Web 查价原型位于 `web/nl-search`（FastAPI + Vue CDN，默认 http://127.0.0.1:8765，**长期定位为独立查价工具**，与桌面监控无集成）；含自然语言/表单/价格矩阵三 Tab；RollingGo Key 必填、LLM Key 可选（规则回退）；`SearchIntent` 含 `min_stay_days` 与可选 `max_stay_days`；全量穷举直接启动，设置页可选「搜索次数软提示」阈值（超过时在搜索栏警告，不弹窗阻断）；长搜索可停止并保留已命中结果；SSE 推送进度与命中；结果区复用 Skill 暖色报告模板
- `web/flight-watch` 为独立 Web 监控工具（FastAPI + Vue CDN，经网关 `/flight-watch/` 或本地 8767）；定位固定模板长期盯价（nl-search 为探索/穷举查价），与 nl-search 无数据打通、Non-Goal 不做一键转 Watch；已实现全球 Watch 规则（往返/单程/多段/开口程，开口程不限制返程落点）、飞书 + PushPlus 微信通知（设置页含申请链接与「测试微信」）、APScheduler 进程内调度 + `POST /api/watch/run-once` cron 兜底；15 条达美开口预设（`presets/delta-open-jaw.json`）可一键导入；多段/开口优先 `swoop-flights` 同票价，失败则 RollingGo 分段 ONE_WAY 相加（`bookable: false`）；凭据 `.credentials.local.json` 与 nl-search 分离
- `web/exhaustive-viz` 为穷举结果可视化页；默认读 `data.json` 静态快照，亦可通过 `?search_id=` 联动 nl-search 实时命中（`/api/search/{id}/viz-bundle`）
- 监控规则约定：每段行程固定一个日期；价格下降时通知，24h 冷却仅防止「价格不变且仍低于限价」重复推送
- RollingGo `airportsearch` 仅关键字搜索、不支持按国家列举全国机场；五国穷举城市来自 `scripts/data/country_city_codes.json`（`scripts/sync_country_airports.py` 从 OurAirports 按热度排序：`exhaustive`=前 50%、`hot`=前 8）；目录外国家走 API 多关键词回退；开口程引擎为两段 ONE_WAY 价相加，同票多段真价需 `swoop-flights` 等通道（ITA Matrix 无公开 API）
- `web/landing` 为 Flight Monitor 品牌官网，顶部导航含在线查价/监控/Skill；含价格矩阵真实截图 gallery；Skill 二级页 `/skill/`
