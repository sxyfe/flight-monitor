"""matrix_valid_date_pairs / validate_matrix_intent 单元测试。"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from flight_search_engine import (  # noqa: E402
    MatrixSearchIntent,
    matrix_valid_date_pairs,
    validate_matrix_intent,
)


def _future(days_ahead: int = 30) -> str:
    return (date.today() + timedelta(days=days_ahead)).isoformat()


def test_separate_ranges_valid_pairs():
    out_s = _future(10)
    out_e = _future(12)
    ret_s = _future(15)
    ret_e = _future(18)
    intent = MatrixSearchIntent.from_dict(
        {
            "origins": ["PEK"],
            "destinations": ["MNL"],
            "out_date_start": out_s,
            "out_date_end": out_e,
            "ret_date_start": ret_s,
            "ret_date_end": ret_e,
            "min_stay_days": 1,
        }
    )
    pairs = matrix_valid_date_pairs(intent)
    assert pairs
    assert all(ret > out for out, ret in pairs)


def test_max_stay_filters_pairs():
    out_s = _future(10)
    out_e = _future(10)
    ret_s = _future(12)
    ret_e = _future(20)
    intent = MatrixSearchIntent.from_dict(
        {
            "origins": ["PEK"],
            "destinations": ["MNL"],
            "out_date_start": out_s,
            "out_date_end": out_e,
            "ret_date_start": ret_s,
            "ret_date_end": ret_e,
            "min_stay_days": 2,
            "max_stay_days": 5,
        }
    )
    pairs = matrix_valid_date_pairs(intent)
    assert pairs
    for out, ret in pairs:
        stay = (ret - out).days
        assert 2 <= stay <= 5


def test_window_mode_shared_dates():
    start = _future(20)
    end = _future(27)
    intent = MatrixSearchIntent.from_dict(
        {
            "origins": ["PEK"],
            "destinations": ["HKT"],
            "out_date": start,
            "ret_date": end,
            "min_stay_days": 1,
        }
    )
    assert intent.out_date_start == start
    assert intent.ret_date_end == end
    assert matrix_valid_date_pairs(intent)


def test_validate_rejects_empty_pairs():
    start = _future(10)
    intent = MatrixSearchIntent.from_dict(
        {
            "origins": ["PEK"],
            "destinations": ["MNL"],
            "out_date_start": start,
            "out_date_end": start,
            "ret_date_start": start,
            "ret_date_end": start,
            "min_stay_days": 7,
        }
    )
    result = validate_matrix_intent(intent)
    assert not result.valid
    assert any("无有效" in e for e in result.errors)


def test_validate_rejects_min_gt_max_stay():
    start = _future(10)
    end = _future(20)
    intent = MatrixSearchIntent.from_dict(
        {
            "origins": ["PEK"],
            "destinations": ["MNL"],
            "out_date_start": start,
            "out_date_end": end,
            "ret_date_start": start,
            "ret_date_end": end,
            "min_stay_days": 10,
            "max_stay_days": 3,
        }
    )
    result = validate_matrix_intent(intent)
    assert not result.valid
    assert any("最少停留" in e for e in result.errors)


if __name__ == "__main__":
    test_separate_ranges_valid_pairs()
    test_max_stay_filters_pairs()
    test_window_mode_shared_dates()
    test_validate_rejects_empty_pairs()
    test_validate_rejects_min_gt_max_stay()
    print("all passed")
