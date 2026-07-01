## 1. 后端：国庆日期与校验 API

- [ ] 1.1 新增 `scripts/holiday_windows.py`：`resolve_national_day_window(query, ref_date)` 实现国庆/国庆前后 future-aware 规则
- [ ] 1.2 更新 `nl_parser.py`：规则回退与 LLM prompt 调用 holiday_windows；注入 `today=YYYY-MM-DD`
- [ ] 1.3 实现 `GET /api/airport/search?q=` 代理 RollingGo airportsearch
- [ ] 1.4 实现 `POST /api/intent/validate` 返回 validation + 查询量预估（无 LLM）
- [ ] 1.5 为 holiday_windows 添加单元测试（国庆、国庆前后、跨年滚动）

## 2. 前端脚手架：Vue3 + Element Plus

- [x] 2.1 在 `index.html` 引入 Vue3、Element Plus、zh-CN locale（**已本地化至 `static/vendor/`**）
- [x] 2.2 重构页面为双 Tab 布局（自然语言查询 / 表单查询），保留设置与结果区
- [x] 2.3 创建 `static/intent-editor.js`（或等价模块）并 mount 到 `#intent-editor-app`（`boot.js` 依赖自检）
- [x] 2.4 设置面板 API Key 字段增加 👁 明文切换（RollingGo + LLM，**v1 纯 HTML 设置页**）
- [x] 2.5 设置页回退 v1 纯 HTML + `app.js` 配置逻辑，移除 `settings-app.js` 与 CDN 依赖

## 3. IntentEditor 表单组件

- [ ] 3.1 实现 `el-date-picker` daterange，`disabledDate < today`，预填解析日期
- [x] 3.2 实现国家多选（预设五国 + 可搜索/自定义输入新国家）
- [ ] 3.3 实现行程类型双 checkbox（往返 / 开口程），至少一项校验
- [ ] 3.4 实现 `AirportPicker` 组件（中文搜索、debounce、标签增删），出发地/目的地各一
- [ ] 3.5 实现可编辑 JSON textarea 与 dirty 状态追踪（form / json 分离）

## 4. 确认同步与搜索门禁

- [ ] 4.1 实现「确认」按钮：dirty 优先合并 → 双向刷新表单 + JSON
- [ ] 4.2 确认时调用 `POST /api/intent/validate`，刷新预估与 warnings/errors
- [ ] 4.3 双端 dirty 时阻止确认并提示用户
- [ ] 4.4 「开始搜索」仅使用 `confirmedIntent`；未确认时禁用或拦截

## 5. NL Tab 流程对接

- [ ] 5.1 NL Tab：textarea + 解析按钮，调用现有 `POST /api/intent/parse`
- [ ] 5.2 解析成功后自动切至表单 Tab 并传入 intent 预填
- [ ] 5.3 表单 Tab 支持直接进入（空表单或上次 confirmedIntent）

## 6. 文档与验证

- [x] 6.1 更新 `web/nl-search/README.md`：双 Tab 流程、确认按钮、国庆日期语义、vendor 本地化
- [ ] 6.2 手工验证：「国庆」→ 10-01~10-07、「国庆前后」→ 09-28~10-10（含 future 滚动）
- [ ] 6.3 手工验证：北京/曼谷 airport 搜索、确认同步 JSON、搜索门禁
- [x] 6.4 手工验证：API Key 👁 切换与保存（设置页 v1 HTML 可见可用）

## 7. 搜索进度与独立脚本

- [x] 7.1 搜索模式中文（智能精简 / 全量穷举）
- [x] 7.2 SSE 实时进度（已查询 x/xx、已命中 n 条）与列表增量更新
- [x] 7.3 国家可搜索多选 + 未知国 airportsearch 动态扩城
- [x] 7.4 新增 `scripts/exhaustive_search_standalone.py`（v1 京津出发独立备份）
