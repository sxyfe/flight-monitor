"""viz_export 单元测试。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web" / "nl-search"))

from viz_export import offers_to_viz_bundle  # noqa: E402


def test_rt_and_oj_split():
    offers = [
        {
            "trip_type": "round_trip",
            "origin": "PEK",
            "dest": "BKK",
            "dest_name": "曼谷",
            "out_date": "2026-10-01",
            "ret_date": "2026-10-08",
            "stay_days": 7,
            "price": 2100,
            "detail": "CA123",
        },
        {
            "trip_type": "open_jaw",
            "origin": "PEK",
            "out_dest": "LAX",
            "ret_dest": "NRT",
            "ret_origin": "PEK",
            "out_date": "2026-10-01",
            "ret_date": "2026-10-15",
            "stay_days": 14,
            "price": 8000,
        },
    ]
    bundle = offers_to_viz_bundle(offers, meta={}, search_id="abc")
    assert len(bundle["rt_hits"]) == 1
    assert len(bundle["oj_hits"]) == 1
    assert bundle["meta"]["source"] == "nl-search"
    assert bundle["meta"]["search_id"] == "abc"
    assert "其他" in bundle["destinations_by_country"]


if __name__ == "__main__":
    test_rt_and_oj_split()
    print("all passed")
