## Context

- 当前 `SearchIntent` 仅有 `min_stay_days`；`valid_date_pairs()` 过滤 `stay >= min_stay`
- 日期控件为 `UiDateRange`：两个原生 `<input type="date">`，无法对系统日历 cell 做 CSS 高亮
- `holiday_windows.py` 已提供「国庆 / 国庆前后」窗口解析，但未暴露「核心周 10-01~10-07」供 UI 高亮
- v2 曾规划 Element Plus `el-date-picker` 高亮，被 v3 supersede；用户现明确**不改日历交互**

## Goals / Non-Goals

**Goals:**

- 新增 `max_stay_days: int | null`，引擎过滤 `min_stay <= stay <= max_stay`（max 为空时不限制上限）
- 表单可见：最少停留、**最多停留**、最高价格（三字段并排或两行紧凑布局）
- 在不改动原生 date input 的前提下，实现国庆核心周 **10-01~10-07** 的视觉高亮（Element 暖色 token）
- NL 解析与查询字符串双向同步包含 max stay

**Non-Goals:**

- 不实现 Popover / 整框点击展开的双月 range 日历
- 不在原生 `<input type="date">` 内嵌 cell 样式（浏览器不可控）
- 不新增除国庆核心周以外的节假日高亮（春节等留后续）

## Decisions

### D1: max_stay_days 语义

| 字段 | 默认 | 语义 |
|------|------|------|
| `min_stay_days` | 7 | 去程与回程间隔 ≥ N 天 |
| `max_stay_days` | null | 去程与回程间隔 ≤ N 天；null 不限制 |

校验规则：

- 若两者均非空且 `min_stay_days > max_stay_days` → `valid: false`
- `valid_date_pairs` 同时应用上下界；无合法日期对时错误信息同时提及 min/max

### D2: 国庆高亮 — 只读参考月历（不改 date input）

**选择**：在 `UiDateRange` 下方挂载 `UiHolidayLegend`（只读、不可选日期），展示**相邻两月**（9 月 + 10 月或按选中 range 动态），对 **10-01~10-07** 单元格加 `.is-national-core` 暖色底。

**理由**：原生 date picker 交互保持不变；高亮需求通过独立 DOM 满足 AGENTS.md「方案 A」视觉，避免重新引入 Element Plus。

**叠加层**：

- 用户已选 `dateRange` 在参考月历上用 `.is-in-range` 描边/浅底
- 图例文案：「橙色：国庆核心周 10/1–10/7」

**年份**：与 `resolve_national_day_window` 一致，取 `ref_date` future-valid 年份。

**备选（未选）**：仅文字图例无 grid — 无法满足「cell 高亮」；整页引入 EP date-picker — 与用户「不改日历」冲突。

### D3: holiday_windows 扩展

新增：

```python
def national_day_core_week(ref_date: date | None = None) -> tuple[str, str]:
    """返回 future-valid 年的 10-01 ~ 10-07 ISO 字符串。"""
```

供前端 `/api/holidays/national-day-core` 或直接在前端用相同算法（优先复用后端 endpoint 避免双份逻辑）。

**选择**：前端 `UiHolidayLegend` 内联与 `holiday_windows` 相同算法（复制 10 行），组件注释注明与 Skill 同步；不新增 API（减少 scope）。

### D4: 表单布局

```
┌─────────────────────────────────────────────────────────┐
│ 国家              │ [date] 至 [date]  （原生，不变）      │
│                   │ ┌─ 只读参考月历（国庆高亮） ─┐        │
│                   │ └ Sep / Oct mini grid ──────┘        │
├─────────────────────────────────────────────────────────┤
│ 最少停留 │ 最多停留 │ 最高价格                          │
└─────────────────────────────────────────────────────────┘
```

### D5: Skill 同步

monorepo `scripts/flight_search_engine.py` 与 Skill 副本、`nl_parser.py`、`search_intent.schema.json` 同 diff 应用，避免 Skill CLI 与 nl-search 行为分叉。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 参考月历与原生 picker 分离，用户可能误以为在参考月历上选日期 | 参考月历 `pointer-events: none` + 图例说明「只读参考」 |
| max_stay 过严导致 0 合法日期对 | validate 返回明确错误与 clarifications |
| 双份 holiday 算法 | 注释 + 可选后续抽共享 util |

## Migration Plan

- 向后兼容：旧 intent JSON 无 `max_stay_days` 视为 null
- 部署：仅前端 + 引擎，无 DB 迁移

## Open Questions

- （已关闭）是否改 Popover 日历 → **否**
- （已关闭）是否新增 max_stay → **是**
