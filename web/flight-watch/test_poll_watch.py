"""poll_watch 集成测试（mock 查价）。"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))

import store
from models import QuoteResult
from scheduler import poll_watch


def _sample_watch_data(**overrides):
    base = {
        "name": "测试开口",
        "enabled": True,
        "trip_mode": "open_jaw",
        "legs": [
            {"from_city": "PVG", "to_city": "LAX", "date": "2027-02-04"},
            {"from_city": "LAX", "to_city": "NRT", "date": "2027-02-14"},
        ],
        "alerts": {"max_price": 4000, "drop_abs": 200, "drop_pct": 5, "cooldown_hours": 24},
        "schedule": {"interval_hours": 12},
    }
    base.update(overrides)
    return base


class TempDb:
    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "test.db"
        store.DB_PATH = self.db
        store.init_db(self.db)
        return self

    def __exit__(self, *args):
        self.tmp.cleanup()


def test_poll_success_writes_snapshot():
    with TempDb():
        w = store.create_watch(_sample_watch_data())
        quote = QuoteResult(
            price=3500.0,
            currency="CNY",
            provider="rollinggo",
            bookable=False,
            legs_summary="PVG→LAX | LAX→NRT",
        )
        with patch("scheduler.quote_watch", return_value=quote):
            result = poll_watch(w.id, dry_run=True, client_factory=lambda: None)
        assert result["ok"] is True
        assert result["price"] == 3500.0
        assert result["notified"] is False
        assert result["notify_reason"] == "price_threshold"
        snaps = store.list_snapshots(w.id)
        assert len(snaps) == 1
        assert snaps[0]["price"] == 3500.0
        assert snaps[0]["provider"] == "rollinggo"


def test_poll_quote_failure():
    with TempDb():
        w = store.create_watch(_sample_watch_data())
        quote = QuoteResult(
            price=None,
            currency="CNY",
            provider="rollinggo",
            bookable=False,
            legs_summary="",
            error="查价服务异常",
        )
        with patch("scheduler.quote_watch", return_value=quote):
            result = poll_watch(w.id, dry_run=True, client_factory=lambda: None)
        assert result["ok"] is False
        assert result["error"] == "查价服务异常"
        snaps = store.list_snapshots(w.id)
        assert len(snaps) == 1
        assert snaps[0]["error_message"] == "查价服务异常"


def test_poll_above_max_no_notify_reason():
    with TempDb():
        w = store.create_watch(_sample_watch_data())
        quote = QuoteResult(
            price=5000.0,
            currency="CNY",
            provider="rollinggo",
            bookable=False,
            legs_summary="test",
        )
        with patch("scheduler.quote_watch", return_value=quote):
            result = poll_watch(w.id, dry_run=True, client_factory=lambda: None)
        assert result["ok"] is True
        assert result.get("notify_reason") is None


if __name__ == "__main__":
    test_poll_success_writes_snapshot()
    test_poll_quote_failure()
    test_poll_above_max_no_notify_reason()
    print("poll_watch tests ok")
