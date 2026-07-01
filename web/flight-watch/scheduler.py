"""Watch 轮询、告警与调度。"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from evaluator import should_notify
from models import Watch
from notify import feishu_send, pushplus_send
from quote_engine import quote_watch
from store import (
    get_notify_state,
    get_watch,
    insert_notify_log,
    insert_snapshot,
    latest_snapshot,
    record_failure,
    reset_failure,
    upsert_notify_state,
)

CREDENTIALS_FILE = Path(__file__).parent / ".credentials.local.json"
_scheduler: BackgroundScheduler | None = None
_poll_fn: Callable[[str, bool], dict[str, Any]] | None = None


def load_credentials() -> dict[str, Any]:
    if CREDENTIALS_FILE.exists():
        try:
            return json.loads(CREDENTIALS_FILE.read_text())
        except Exception:
            pass
    return {}


def _build_alert_message(watch: Watch, price: float, currency: str, provider: str, bookable: bool, reason: str) -> str:
    legs = "\n".join(
        f"  · {l.from_city}→{l.to_city} {l.date}" for l in watch.legs
    )
    bookable_note = "同票可订参考" if bookable else "分段相加/仅供参考，请以 OTA 确认"
    return (
        f"✈️ Flight Watch · {watch.name}\n"
        f"触发：{reason}\n"
        f"价格：{currency} {price:.0f}（限价 {watch.currency} {watch.alerts.max_price:.0f}）\n"
        f"Provider：{provider} · {bookable_note}\n"
        f"航段：\n{legs}\n"
        f"⚠️ 请以 Trip/航司官网确认可订与退改规则。"
    )


def _send_notifications(watch: Watch, message: str, price: float, creds: dict[str, Any]) -> list[str]:
    channels: list[str] = []
    feishu = creds.get("feishu_webhook") or creds.get("notify", {}).get("feishu_webhook")
    pushplus = creds.get("pushplus_token") or creds.get("notify", {}).get("pushplus_token")
    if feishu:
        try:
            feishu_send(feishu, message)
            insert_notify_log(watch.id, price, "feishu", True, message[:500])
            channels.append("feishu")
        except Exception as exc:
            insert_notify_log(watch.id, price, "feishu", False, str(exc))
    if pushplus:
        try:
            pushplus_send(pushplus, f"Flight Watch · {watch.name}", message)
            insert_notify_log(watch.id, price, "pushplus", True, message[:500])
            channels.append("pushplus")
        except Exception as exc:
            insert_notify_log(watch.id, price, "pushplus", False, str(exc))
    return channels


def _is_expired(watch: Watch) -> bool:
    until = watch.schedule.active_until
    if not until:
        return False
    try:
        return date.fromisoformat(until) < date.today()
    except ValueError:
        return False


def poll_watch(
    watch_id: str,
    *,
    dry_run: bool = False,
    client_factory: Callable,
) -> dict[str, Any]:
    watch = get_watch(watch_id)
    if not watch:
        return {"ok": False, "error": "watch not found"}
    if _is_expired(watch):
        return {"ok": False, "error": "watch expired", "skipped": True}

    quote = quote_watch(watch, client_factory)
    if not quote.success():
        count = record_failure(watch_id, quote.error or "查价失败")
        insert_snapshot(
            watch_id,
            None,
            watch.currency,
            quote.provider,
            False,
            quote.legs_summary,
            error=quote.error,
        )
        result = {"ok": False, "error": quote.error, "failure_count": count}
        if count >= 3 and not dry_run:
            creds = load_credentials()
            msg = f"⚠️ 监控失效 · {watch.name}\n连续 3 次查价失败：{quote.error}"
            _send_notifications(watch, msg, 0, creds)
        return result

    reset_failure(watch_id)
    insert_snapshot(
        watch_id,
        quote.price,
        quote.currency,
        quote.provider,
        quote.bookable,
        quote.legs_summary,
        raw=quote.raw,
    )
    state = get_notify_state(watch_id)
    notify, reason = should_notify(state, float(quote.price), watch.alerts)
    channels: list[str] = []
    if notify and not dry_run:
        msg = _build_alert_message(
            watch, float(quote.price), quote.currency, quote.provider, quote.bookable, reason
        )
        channels = _send_notifications(watch, msg, float(quote.price), load_credentials())
        from store import _utc_now

        upsert_notify_state(
            watch_id,
            last_notified_price=float(quote.price),
            last_notified_at=_utc_now(),
        )

    return {
        "ok": True,
        "price": quote.price,
        "currency": quote.currency,
        "provider": quote.provider,
        "bookable": quote.bookable,
        "notified": bool(channels),
        "channels": channels,
        "notify_reason": reason if notify else None,
    }


def poll_all(*, dry_run: bool = False, client_factory: Callable) -> dict[str, Any]:
    from store import list_watches

    results = []
    for w in list_watches():
        if not w.enabled:
            continue
        results.append({"id": w.id, **poll_watch(w.id, dry_run=dry_run, client_factory=client_factory)})
    return {"count": len(results), "results": results}


def start_scheduler(client_factory: Callable) -> BackgroundScheduler:
    global _scheduler, _poll_fn
    _poll_fn = lambda wid, dry=False: poll_watch(wid, dry_run=dry, client_factory=client_factory)

    if _scheduler and _scheduler.running:
        return _scheduler

    sched = BackgroundScheduler(daemon=True)

    def job_for_watch(watch_id: str):
        w = get_watch(watch_id)
        if w and w.enabled and not _is_expired(w):
            _poll_fn(watch_id, False)

    from store import list_watches

    for w in list_watches():
        if w.enabled:
            sched.add_job(
                job_for_watch,
                IntervalTrigger(hours=max(1, w.schedule.interval_hours)),
                args=[w.id],
                id=f"watch_{w.id}",
                replace_existing=True,
            )
    sched.start()
    _scheduler = sched
    return sched


def refresh_scheduler_jobs(client_factory: Callable) -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    start_scheduler(client_factory)
