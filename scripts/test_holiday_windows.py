"""holiday_windows 单元测试。"""
from datetime import date

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from holiday_windows import resolve_national_day_window


def test_guoqing_window_future():
    ref = date(2026, 6, 19)
    start, end = resolve_national_day_window("国庆节去日本", ref)
    assert start == "2026-10-01"
    assert end == "2026-10-07"


def test_guoqing_qianhou_window():
    ref = date(2026, 6, 19)
    start, end = resolve_national_day_window("国庆前后出发", ref)
    assert start == "2026-09-28"
    assert end == "2026-10-10"


def test_guoqing_rolls_to_next_year():
    ref = date(2026, 10, 15)
    start, end = resolve_national_day_window("国庆", ref)
    assert start == "2027-10-01"
    assert end == "2027-10-07"


def test_qianhou_rolls_to_next_year():
    ref = date(2026, 10, 15)
    start, end = resolve_national_day_window("国庆节前后", ref)
    assert start == "2027-09-28"
    assert end == "2027-10-10"


if __name__ == "__main__":
    test_guoqing_window_future()
    test_guoqing_qianhou_window()
    test_guoqing_rolls_to_next_year()
    test_qianhou_rolls_to_next_year()
    print("all passed")
