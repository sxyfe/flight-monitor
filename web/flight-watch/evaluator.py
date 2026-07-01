"""告警判定：限价、降价、冷却。"""
from __future__ import annotations

from datetime import datetime, timezone

from models import NotifyState, WatchAlerts


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def within_cooldown(last_notified_at: str | None, cooldown_hours: int) -> bool:
    dt = _parse_dt(last_notified_at)
    if not dt:
        return False
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (now - dt).total_seconds() < cooldown_hours * 3600


def should_notify_price(
    state: NotifyState,
    price: float,
    alerts: WatchAlerts,
) -> bool:
    if price > alerts.max_price + 0.009:
        return False
    last = state.last_notified_price
    if last is None:
        return True
    if price + 0.009 < last:
        return True
    if abs(price - last) <= 0.009:
        return not within_cooldown(state.last_notified_at, alerts.cooldown_hours)
    return False


def should_notify_drop(
    state: NotifyState,
    price: float,
    alerts: WatchAlerts,
) -> bool:
    if state.last_snapshot_price is None:
        return False
    prev = state.last_snapshot_price
    if price >= prev - 0.009:
        return False
    drop = prev - price
    if alerts.drop_abs and drop >= alerts.drop_abs:
        return True
    if prev > 0 and alerts.drop_pct and (drop / prev * 100) >= alerts.drop_pct:
        return True
    return False


def should_notify(
    state: NotifyState,
    price: float,
    alerts: WatchAlerts,
) -> tuple[bool, str]:
    if should_notify_price(state, price, alerts):
        return True, "price_threshold"
    if should_notify_drop(state, price, alerts):
        return True, "price_drop"
    return False, ""
