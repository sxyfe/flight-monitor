## 1. 引擎与解析

- [x] 1.1 `scripts/flight_search_engine.py`：`SearchIntent` 增加 `max_stay_days: int | None`；`from_dict` / `to_dict` 同步
- [x] 1.2 `valid_date_pairs()` 增加 `stay <= max_stay_days` 过滤；OW 分支同步
- [x] 1.3 `validate_intent()`：min>max 报错；无合法对时错误文案含 max stay
- [x] 1.4 Skill 镜像：`flight-monitor-agent/scripts/flight_search_engine.py` 同 diff
- [x] 1.5 `nl_parser.py`（Skill）：schema、SYSTEM_PROMPT、规则回退解析 max stay 短语
- [x] 1.6 `search_intent.schema.json` 增加 `max_stay_days`

## 2. 前端表单

- [x] 2.1 `intent-editor.js`：form 增加 `max_stay_days`；`formToIntent` / `intentToForm` / watch 同步
- [x] 2.2 模板：三字段 grid（最少/最多停留、最高价格）
- [x] 2.3 `intent-query.js`：生成/识别「最多玩 N 天」等短语

## 3. 国庆高亮（不改原生 date input）

- [x] 3.1 `holiday_windows.py`（Skill + monorepo 委托处）：`national_day_core_week(ref_date)` 返回 10-01~10-07
- [x] 3.2 新增 `UiHolidayLegend` 于 `ui/components.js`：双月只读 grid，`.is-national-core` / `.is-in-range` 样式
- [x] 3.3 `UiDateRange` 模板下方嵌入 `UiHolidayLegend`；`tokens.css` 暖色 cell 样式 + `pointer-events: none`
- [x] 3.4 图例文案：「橙色：国庆核心周 10/1–10/7（只读参考）」

## 4. 报告与验证

- [x] 4.1 `report-bridge.js` / `report.js` meta 展示 max stay
- [x] 4.2 手动验证：parse「最多玩10天」→ 表单 → 搜索；参考月历 10/1–10/7 高亮；原生 date 仍可点
