"""evaluator 单元测试。"""
from evaluator import should_notify, should_notify_drop, should_notify_price
from models import NotifyState, WatchAlerts


def test_first_hit():
    state = NotifyState(watch_id="w1")
    alerts = WatchAlerts(max_price=3500)
    assert should_notify_price(state, 3400, alerts) is True


def test_cooldown_same_price():
    state = NotifyState(
        watch_id="w1",
        last_notified_price=3400,
        last_notified_at="2020-01-01T00:00:00+00:00",
    )
    alerts = WatchAlerts(max_price=3500, cooldown_hours=24)
    assert should_notify_price(state, 3400, alerts) is True


def test_drop_threshold():
    state = NotifyState(watch_id="w1", last_snapshot_price=4000)
    alerts = WatchAlerts(max_price=3000, drop_abs=200)
    assert should_notify_drop(state, 3700, alerts) is True
    ok, reason = should_notify(state, 3700, alerts)
    assert ok and reason == "price_drop"


if __name__ == "__main__":
    test_first_hit()
    test_cooldown_same_price()
    test_drop_threshold()
    print("evaluator tests ok")
