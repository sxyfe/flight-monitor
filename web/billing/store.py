"""订阅与用户 SQLite 存储。"""
from __future__ import annotations

import os
import sqlite3
import sys
import threading
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from plans import PLANS, PlanId

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
DB_PATH = Path(os.environ.get("BILLING_DB_PATH", str(DATA_DIR / "billing.db")))

_lock = threading.Lock()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.fromisoformat(s)


@contextmanager
def _conn():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _lock:
        with _conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    plan_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    starts_at TEXT NOT NULL,
                    expires_at TEXT,
                    stripe_customer_id TEXT,
                    stripe_subscription_id TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                CREATE INDEX IF NOT EXISTS idx_sub_user ON subscriptions(user_id);
                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    plan_id TEXT NOT NULL,
                    amount_cny INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    stripe_session_id TEXT,
                    created_at TEXT NOT NULL,
                    paid_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                CREATE TABLE IF NOT EXISTS usage_daily (
                    user_id TEXT NOT NULL,
                    day TEXT NOT NULL,
                    search_count INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (user_id, day)
                );
                """
            )


def create_user(email: str, password_hash: str) -> dict[str, Any]:
    uid = f"usr_{uuid.uuid4().hex[:12]}"
    now = _iso(_utcnow())
    with _lock:
        with _conn() as conn:
            conn.execute(
                "INSERT INTO users (id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (uid, email.lower().strip(), password_hash, now),
            )
    grant_subscription(uid, "free_trial", source="signup")
    return get_user(uid)  # type: ignore[return-value]


def get_user_by_email(email: str) -> dict[str, Any] | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT id, email, password_hash, created_at FROM users WHERE email = ?",
            (email.lower().strip(),),
        ).fetchone()
    return dict(row) if row else None


def get_user(user_id: str) -> dict[str, Any] | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT id, email, password_hash, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def grant_subscription(
    user_id: str,
    plan_id: PlanId,
    *,
    source: str = "purchase",
    stripe_customer_id: str | None = None,
    stripe_subscription_id: str | None = None,
) -> dict[str, Any]:
    plan = PLANS[plan_id]
    now = _utcnow()
    expires: datetime | None = None
    if plan.duration_days is not None:
        expires = now + timedelta(days=plan.duration_days)
    sub_id = f"sub_{uuid.uuid4().hex[:12]}"
    with _lock:
        with _conn() as conn:
            conn.execute(
                "UPDATE subscriptions SET status = 'replaced' WHERE user_id = ? AND status = 'active'",
                (user_id,),
            )
            conn.execute(
                """
                INSERT INTO subscriptions
                (id, user_id, plan_id, status, starts_at, expires_at,
                 stripe_customer_id, stripe_subscription_id, created_at)
                VALUES (?, ?, ?, 'active', ?, ?, ?, ?, ?)
                """,
                (
                    sub_id,
                    user_id,
                    plan_id,
                    _iso(now),
                    _iso(expires),
                    stripe_customer_id,
                    stripe_subscription_id,
                    _iso(now),
                ),
            )
    return get_active_subscription(user_id)  # type: ignore[return-value]


def get_active_subscription(user_id: str) -> dict[str, Any] | None:
    with _conn() as conn:
        row = conn.execute(
            """
            SELECT * FROM subscriptions
            WHERE user_id = ? AND status = 'active'
            ORDER BY created_at DESC LIMIT 1
            """,
            (user_id,),
        ).fetchone()
    if not row:
        return None
    sub = dict(row)
    exp = _parse_iso(sub.get("expires_at"))
    if exp and exp < _utcnow():
        expire_subscription(sub["id"])
        return None
    return sub


def expire_subscription(sub_id: str) -> None:
    with _lock:
        with _conn() as conn:
            conn.execute(
                "UPDATE subscriptions SET status = 'expired' WHERE id = ?",
                (sub_id,),
            )


def cancel_subscription(user_id: str) -> bool:
    sub = get_active_subscription(user_id)
    if not sub:
        return False
    with _lock:
        with _conn() as conn:
            conn.execute(
                "UPDATE subscriptions SET status = 'cancelled' WHERE id = ?",
                (sub["id"],),
            )
    return True


def create_order(
    user_id: str,
    plan_id: PlanId,
    amount_cny: int,
    stripe_session_id: str | None = None,
) -> dict[str, Any]:
    oid = f"ord_{uuid.uuid4().hex[:12]}"
    now = _iso(_utcnow())
    with _lock:
        with _conn() as conn:
            conn.execute(
                """
                INSERT INTO orders (id, user_id, plan_id, amount_cny, status, stripe_session_id, created_at)
                VALUES (?, ?, ?, ?, 'pending', ?, ?)
                """,
                (oid, user_id, plan_id, amount_cny, stripe_session_id, now),
            )
    return get_order(oid)  # type: ignore[return-value]


def get_order(order_id: str) -> dict[str, Any] | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    return dict(row) if row else None


def get_order_by_session(session_id: str) -> dict[str, Any] | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM orders WHERE stripe_session_id = ?", (session_id,)
        ).fetchone()
    return dict(row) if row else None


def mark_order_paid(order_id: str) -> None:
    with _lock:
        with _conn() as conn:
            conn.execute(
                "UPDATE orders SET status = 'paid', paid_at = ? WHERE id = ?",
                (_iso(_utcnow()), order_id),
            )


def increment_search_usage(user_id: str, count: int = 1) -> int:
    day = date.today().isoformat()
    with _lock:
        with _conn() as conn:
            conn.execute(
                """
                INSERT INTO usage_daily (user_id, day, search_count) VALUES (?, ?, ?)
                ON CONFLICT(user_id, day) DO UPDATE SET search_count = search_count + ?
                """,
                (user_id, day, count, count),
            )
            row = conn.execute(
                "SELECT search_count FROM usage_daily WHERE user_id = ? AND day = ?",
                (user_id, day),
            ).fetchone()
    return int(row["search_count"]) if row else count


def get_search_usage_today(user_id: str) -> int:
    day = date.today().isoformat()
    with _conn() as conn:
        row = conn.execute(
            "SELECT search_count FROM usage_daily WHERE user_id = ? AND day = ?",
            (user_id, day),
        ).fetchone()
    return int(row["search_count"]) if row else 0


def count_enabled_watches_for_user(user_id: str) -> int:
    fw_dir = APP_DIR.parent / "flight-watch"
    if str(fw_dir) not in sys.path:
        sys.path.insert(0, str(fw_dir))
    try:
        import store as fw_store

        return fw_store.count_enabled_watches(user_id)
    except Exception:
        return 0
