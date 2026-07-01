"""中国节假日窗口解析（委托 flight-monitor-agent Skill）。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SKILL_HW = (
    Path(__file__).resolve().parents[1]
    / ".cursor/skills/flight-monitor-agent/scripts/holiday_windows.py"
)
_spec = importlib.util.spec_from_file_location("flight_monitor_skill_holiday_windows", _SKILL_HW)
if _spec is None or _spec.loader is None:
    raise ImportError(f"无法加载 Skill holiday_windows: {_SKILL_HW}")
_mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _mod
_spec.loader.exec_module(_mod)

resolve_national_day_window = _mod.resolve_national_day_window
national_day_core_week = _mod.national_day_core_week
calendar_holiday_map = _mod.calendar_holiday_map

__all__ = ["resolve_national_day_window", "national_day_core_week", "calendar_holiday_map"]
