"""SQLite 持久化：Watch、快照、通知状态。"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from models import (
    Leg,
    NotifyState,
    Watch,
    WatchAlerts,
    WatchFilters,
    WatchSchedule,
)

DB_PATH = Path(__file__).parent / "data" / "flight_watch.db"
_db_initialized = False


def _ensure_db() -> None:
    """网关 mount 子应用时不触发 lifespan，首次访问前确保建表。"""
    global _db_initialized
    if not _db_initialized:
        init_db()
        _db_initialized = True


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def init_db(path: Path | None = None) -> None:
    db = path or DB_PATH
    db.parent.mkdir(parents=True, exist_ok=True)
    with _connect(db) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS watches (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              enabled INTEGER NOT NULL DEFAULT 1,
              trip_mode TEXT NOT NULL,
              legs_json TEXT NOT NULL,
              return_date TEXT,
              pricing_mode TEXT NOT NULL DEFAULT 'auto',
              sales_region TEXT,
              currency TEXT NOT NULL DEFAULT 'CNY',
              filters_json TEXT NOT NULL DEFAULT '{}',
              alerts_json TEXT NOT NULL,
              schedule_json TEXT NOT NULL,
              reference_price REAL,
              notes TEXT,
              failure_count INTEGER NOT NULL DEFAULT 0,
              failure_reason TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS snapshots (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              watch_id TEXT NOT NULL,
              price REAL,
              currency TEXT,
              provider TEXT,
              bookable INTEGER,
              legs_summary TEXT,
              error_message TEXT,
              checked_at TEXT NOT NULL,
              raw_json TEXT,
              FOREIGN KEY (watch_id) REFERENCES watches(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS notify_state (
              watch_id TEXT PRIMARY KEY,
              last_notified_price REAL,
              last_notified_at TEXT,
              last_snapshot_price REAL,
              FOREIGN KEY (watch_id) REFERENCES watches(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS notify_log (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              watch_id TEXT NOT NULL,
              sent_at TEXT NOT NULL,
              price REAL,
              channel TEXT NOT NULL,
              success INTEGER NOT NULL,
              message TEXT NOT NULL
            );
            """
        )
        _migrate_user_id(conn)


def _migrate_user_id(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(watches)").fetchall()}
    if "user_id" not in cols:
        conn.execute("ALTER TABLE watches ADD COLUMN user_id TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_watches_user ON watches(user_id)")


@contextmanager
def _connect(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    if path is None:
        _ensure_db()
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def list_watches(user_id: str | None = None) -> list[Watch]:
    with _connect() as conn:
        if user_id:
            rows = conn.execute(
                "SELECT * FROM watches WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM watches ORDER BY updated_at DESC").fetchall()
    return [Watch.from_row(dict(r)) for r in rows]


def count_enabled_watches(user_id: str | None = None) -> int:
    with _connect() as conn:
        if user_id:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM watches WHERE enabled = 1 AND user_id = ?",
                (user_id,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM watches WHERE enabled = 1"
            ).fetchone()
    return int(row["c"]) if row else 0


def get_watch(watch_id: str) -> Watch | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM watches WHERE id = ?", (watch_id,)).fetchone()
    return Watch.from_row(dict(row)) if row else None


def create_watch(data: dict[str, Any]) -> Watch:
    watch_id = data.get("id") or f"watch_{uuid.uuid4().hex[:12]}"
    now = _utc_now()
    legs = [Leg.from_dict(x) for x in data["legs"]]
    alerts = WatchAlerts.from_dict(data["alerts"])
    schedule = WatchSchedule.from_dict(data.get("schedule") or {})
    filters = WatchFilters.from_dict(data.get("filters"))
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO watches (
              id, name, enabled, trip_mode, legs_json, return_date, pricing_mode,
              sales_region, currency, filters_json, alerts_json, schedule_json,
              reference_price, notes, failure_count, failure_reason, created_at, updated_at,
              user_id
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,NULL,?,?,?)
            """,
            (
                watch_id,
                data["name"],
                1 if data.get("enabled", True) else 0,
                data["trip_mode"],
                json.dumps([l.to_dict() for l in legs], ensure_ascii=False),
                data.get("return_date"),
                data.get("pricing_mode") or "auto",
                data.get("sales_region"),
                data.get("currency") or "CNY",
                json.dumps(filters.to_dict(), ensure_ascii=False),
                json.dumps(alerts.to_dict(), ensure_ascii=False),
                json.dumps(schedule.to_dict(), ensure_ascii=False),
                data.get("reference_price"),
                data.get("notes"),
                now,
                now,
                data.get("user_id"),
            ),
        )
    w = get_watch(watch_id)
    assert w is not None
    return w


def update_watch(watch_id: str, data: dict[str, Any]) -> Watch | None:
    existing = get_watch(watch_id)
    if not existing:
        return None
    now = _utc_now()
    legs = [Leg.from_dict(x) for x in data.get("legs", [l.to_dict() for l in existing.legs])]
    alerts = WatchAlerts.from_dict(data.get("alerts", existing.alerts.to_dict()))
    schedule = WatchSchedule.from_dict(data.get("schedule", existing.schedule.to_dict()))
    filters = WatchFilters.from_dict(data.get("filters", existing.filters.to_dict()))
    with _connect() as conn:
        conn.execute(
            """
            UPDATE watches SET
              name=?, enabled=?, trip_mode=?, legs_json=?, return_date=?, pricing_mode=?,
              sales_region=?, currency=?, filters_json=?, alerts_json=?, schedule_json=?,
              reference_price=?, notes=?, updated_at=?
            WHERE id=?
            """,
            (
                data.get("name", existing.name),
                1 if data.get("enabled", existing.enabled) else 0,
                data.get("trip_mode", existing.trip_mode),
                json.dumps([l.to_dict() for l in legs], ensure_ascii=False),
                data.get("return_date", existing.return_date),
                data.get("pricing_mode", existing.pricing_mode),
                data.get("sales_region", existing.sales_region),
                data.get("currency", existing.currency),
                json.dumps(filters.to_dict(), ensure_ascii=False),
                json.dumps(alerts.to_dict(), ensure_ascii=False),
                json.dumps(schedule.to_dict(), ensure_ascii=False),
                data.get("reference_price", existing.reference_price),
                data.get("notes", existing.notes),
                now,
                watch_id,
            ),
        )
    return get_watch(watch_id)


def delete_watch(watch_id: str) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM watches WHERE id = ?", (watch_id,))
    return cur.rowcount > 0


def set_watch_enabled(watch_id: str, enabled: bool) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE watches SET enabled=?, updated_at=? WHERE id=?",
            (1 if enabled else 0, _utc_now(), watch_id),
        )


def record_failure(watch_id: str, reason: str) -> int:
    with _connect() as conn:
        row = conn.execute(
            "SELECT failure_count FROM watches WHERE id=?", (watch_id,)
        ).fetchone()
        count = int(row["failure_count"]) + 1 if row else 1
        conn.execute(
            "UPDATE watches SET failure_count=?, failure_reason=?, updated_at=? WHERE id=?",
            (count, reason, _utc_now(), watch_id),
        )
        if count >= 3:
            conn.execute(
                "UPDATE watches SET enabled=0, updated_at=? WHERE id=?",
                (_utc_now(), watch_id),
            )
    return count


def reset_failure(watch_id: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE watches SET failure_count=0, failure_reason=NULL, updated_at=? WHERE id=?",
            (_utc_now(), watch_id),
        )


def insert_snapshot(
    watch_id: str,
    price: float | None,
    currency: str,
    provider: str,
    bookable: bool,
    legs_summary: str,
    error: str | None = None,
    raw: dict[str, Any] | None = None,
) -> int:
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO snapshots (
              watch_id, price, currency, provider, bookable, legs_summary,
              error_message, checked_at, raw_json
            ) VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                watch_id,
                price,
                currency,
                provider,
                1 if bookable else 0,
                legs_summary,
                error,
                _utc_now(),
                json.dumps(raw, ensure_ascii=False) if raw else None,
            ),
        )
        if price is not None:
            conn.execute(
                """
                INSERT INTO notify_state (watch_id, last_snapshot_price)
                VALUES (?,?)
                ON CONFLICT(watch_id) DO UPDATE SET last_snapshot_price=excluded.last_snapshot_price
                """,
                (watch_id, price),
            )
        return int(cur.lastrowid)


def list_snapshots(watch_id: str, limit: int = 50) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM snapshots WHERE watch_id=? ORDER BY checked_at DESC LIMIT ?
            """,
            (watch_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def latest_snapshot(watch_id: str) -> dict[str, Any] | None:
    snaps = list_snapshots(watch_id, limit=1)
    return snaps[0] if snaps else None


def get_notify_state(watch_id: str) -> NotifyState:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM notify_state WHERE watch_id=?", (watch_id,)
        ).fetchone()
    if not row:
        return NotifyState(watch_id=watch_id)
    return NotifyState(
        watch_id=watch_id,
        last_notified_price=row["last_notified_price"],
        last_notified_at=row["last_notified_at"],
        last_snapshot_price=row["last_snapshot_price"],
    )


def upsert_notify_state(
    watch_id: str,
    last_notified_price: float | None = None,
    last_notified_at: str | None = None,
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO notify_state (watch_id, last_notified_price, last_notified_at)
            VALUES (?,?,?)
            ON CONFLICT(watch_id) DO UPDATE SET
              last_notified_price=COALESCE(excluded.last_notified_price, notify_state.last_notified_price),
              last_notified_at=COALESCE(excluded.last_notified_at, notify_state.last_notified_at)
            """,
            (watch_id, last_notified_price, last_notified_at),
        )


def insert_notify_log(
    watch_id: str,
    price: float | None,
    channel: str,
    success: bool,
    message: str,
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO notify_log (watch_id, sent_at, price, channel, success, message)
            VALUES (?,?,?,?,?,?)
            """,
            (watch_id, _utc_now(), price, channel, 1 if success else 0, message),
        )
