"""中国节假日窗口解析（future-aware）。"""
from __future__ import annotations

from datetime import date, timedelta

# 国务院放假安排近似区间（用于日历参考高亮，非购票保证）
CHINA_PUBLIC_HOLIDAY_PERIODS: dict[int, list[tuple[str, str, str]]] = {
    2025: [
        ("2025-01-01", "2025-01-01", "元旦"),
        ("2025-01-28", "2025-02-04", "春节"),
        ("2025-04-04", "2025-04-06", "清明"),
        ("2025-05-01", "2025-05-05", "劳动节"),
        ("2025-05-31", "2025-06-02", "端午"),
        ("2025-10-01", "2025-10-08", "国庆中秋"),
    ],
    2026: [
        ("2026-01-01", "2026-01-03", "元旦"),
        ("2026-02-15", "2026-02-23", "春节"),
        ("2026-04-04", "2026-04-06", "清明"),
        ("2026-05-01", "2026-05-05", "劳动节"),
        ("2026-06-19", "2026-06-21", "端午"),
        ("2026-09-25", "2026-09-27", "中秋"),
        ("2026-10-01", "2026-10-07", "国庆"),
    ],
    2027: [
        ("2027-01-01", "2027-01-03", "元旦"),
        ("2027-02-06", "2027-02-12", "春节"),
        ("2027-04-03", "2027-04-05", "清明"),
        ("2027-05-01", "2027-05-05", "劳动节"),
        ("2027-06-09", "2027-06-11", "端午"),
        ("2027-09-15", "2027-09-17", "中秋"),
        ("2027-10-01", "2027-10-07", "国庆"),
    ],
    2028: [
        ("2028-01-01", "2028-01-03", "元旦"),
        ("2028-01-26", "2028-02-01", "春节"),
        ("2028-04-04", "2028-04-06", "清明"),
        ("2028-05-01", "2028-05-05", "劳动节"),
        ("2028-05-28", "2028-05-30", "端午"),
        ("2028-10-03", "2028-10-05", "中秋"),
        ("2028-10-01", "2028-10-07", "国庆"),
    ],
}


def _window_for_year(year: int, start_md: tuple[int, int], end_md: tuple[int, int]) -> tuple[str, str]:
    start = date(year, start_md[0], start_md[1])
    end = date(year, end_md[0], end_md[1])
    return start.isoformat(), end.isoformat()


def resolve_national_day_window(query: str, ref_date: date | None = None) -> tuple[str, str] | None:
    """解析国庆相关关键词，返回 future-valid 的 (date_start, date_end)。

    - 「国庆前后」→ 09-28 ~ 10-10
    - 「国庆」（不含前后）→ 10-01 ~ 10-07
    """
    ref = ref_date or date.today()
    q = query.replace(" ", "")

    if "国庆前后" in q or "国庆节前后" in q:
        start_md, end_md = (9, 28), (10, 10)
    elif "国庆" in q:
        start_md, end_md = (10, 1), (10, 7)
    else:
        return None

    year = ref.year
    date_start, date_end = _window_for_year(year, start_md, end_md)
    if date.fromisoformat(date_end) < ref:
        year += 1
        date_start, date_end = _window_for_year(year, start_md, end_md)
    return date_start, date_end


def national_day_core_week(ref_date: date | None = None) -> tuple[str, str]:
    """返回 future-valid 年的国庆核心周 10-01 ~ 10-07。"""
    ref = ref_date or date.today()
    year = ref.year
    date_start, date_end = _window_for_year(year, (10, 1), (10, 7))
    if date.fromisoformat(date_end) < ref:
        year += 1
        date_start, date_end = _window_for_year(year, (10, 1), (10, 7))
    return date_start, date_end


def calendar_holiday_map(year: int) -> dict[str, str]:
    """返回指定年份 ISO 日期 → 节假日名称，供日历 UI 高亮。"""
    out: dict[str, str] = {}
    for start, end, label in CHINA_PUBLIC_HOLIDAY_PERIODS.get(year, []):
        d = date.fromisoformat(start)
        end_d = date.fromisoformat(end)
        while d <= end_d:
            out[d.isoformat()] = label
            d += timedelta(days=1)
    core_start, core_end = _window_for_year(year, (10, 1), (10, 7))
    d = date.fromisoformat(core_start)
    end_d = date.fromisoformat(core_end)
    while d <= end_d:
        out.setdefault(d.isoformat(), "国庆")
        d += timedelta(days=1)
    return out
