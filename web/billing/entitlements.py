"""权益检查 — 供 nl-search / flight-watch 调用。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from plans import PLANS, PlanId

BILLING_ENABLED = os.environ.get("BILLING_ENABLED", "true").lower() in ("1", "true", "yes")


@dataclass
class GateResult:
    allowed: bool
    code: str = "OK"
    message: str = ""
    plan_id: str | None = None
    usage_today: int = 0
    limit_today: int = 0
    upgrade_url: str = "/billing/"


def _effective_plan(user_id: str | None) -> tuple[PlanId | None, dict[str, Any] | None]:
    if not user_id:
        return None, None
    import store

    sub = store.get_active_subscription(user_id)
    if not sub:
        return None, None
    plan_id = sub["plan_id"]
    if plan_id not in PLANS:
        return None, sub
    return plan_id, sub


def get_entitlements(user_id: str | None) -> dict[str, Any]:
    if not BILLING_ENABLED:
        return {
            "billing_enabled": False,
            "authenticated": bool(user_id),
            "plan": None,
            "unlimited": True,
        }
    import store

    plan_id, sub = _effective_plan(user_id)
    if not plan_id:
        return {
            "billing_enabled": True,
            "authenticated": bool(user_id),
            "plan": None,
            "requires_login": not user_id,
            "requires_subscription": bool(user_id),
            "upgrade_url": "/billing/",
        }
    plan = PLANS[plan_id]
    usage = store.get_search_usage_today(user_id) if user_id else 0
    return {
        "billing_enabled": True,
        "authenticated": True,
        "plan": plan_id,
        "plan_name": plan.name,
        "expires_at": sub.get("expires_at") if sub else None,
        "search_queries_per_day": plan.search_queries_per_day,
        "search_usage_today": usage,
        "max_watches": plan.max_watches,
        "exhaustive_enabled": plan.exhaustive_enabled,
        "matrix_enabled": plan.matrix_enabled,
        "upgrade_url": "/billing/",
    }


def check_search_allowed(
    user_id: str | None,
    *,
    mode: str = "smart",
    search_type: str = "standard",
    estimated_queries: int = 1,
) -> GateResult:
    if not BILLING_ENABLED:
        return GateResult(True)
    if not user_id:
        return GateResult(
            False,
            "LOGIN_REQUIRED",
            "请先登录后再开始搜索",
            upgrade_url="/billing/#login",
        )
    plan_id, _ = _effective_plan(user_id)
    if not plan_id:
        return GateResult(
            False,
            "SUBSCRIPTION_REQUIRED",
            "暂无有效会员，请订阅或续费",
            upgrade_url="/billing/",
        )
    plan = PLANS[plan_id]
    if search_type == "matrix" and not plan.matrix_enabled:
        return GateResult(
            False,
            "PLAN_LIMIT",
            "当前套餐不支持价格矩阵，请升级会员",
            plan_id=plan_id,
            upgrade_url="/billing/",
        )
    if mode == "exhaustive" and not plan.exhaustive_enabled:
        return GateResult(
            False,
            "PLAN_LIMIT",
            "当前套餐不支持全量穷举，请升级会员",
            plan_id=plan_id,
            upgrade_url="/billing/",
        )
    import store

    usage = store.get_search_usage_today(user_id)
    projected = usage + max(estimated_queries, 1)
    if projected > plan.search_queries_per_day:
        return GateResult(
            False,
            "QUOTA_EXCEEDED",
            f"今日搜索配额已用尽（{usage}/{plan.search_queries_per_day}），请明日再试或升级套餐",
            plan_id=plan_id,
            usage_today=usage,
            limit_today=plan.search_queries_per_day,
            upgrade_url="/billing/",
        )
    return GateResult(
        True,
        plan_id=plan_id,
        usage_today=usage,
        limit_today=plan.search_queries_per_day,
    )


def record_search_usage(user_id: str | None, count: int = 1) -> None:
    if not BILLING_ENABLED or not user_id:
        return
    import store

    store.increment_search_usage(user_id, count)


def check_watch_allowed(user_id: str | None, *, current_count: int | None = None) -> GateResult:
    if not BILLING_ENABLED:
        return GateResult(True)
    if not user_id:
        return GateResult(
            False,
            "LOGIN_REQUIRED",
            "请先登录后再创建监控",
            upgrade_url="/billing/#login",
        )
    plan_id, _ = _effective_plan(user_id)
    if not plan_id:
        return GateResult(
            False,
            "SUBSCRIPTION_REQUIRED",
            "暂无有效会员，请订阅后使用监控功能",
            upgrade_url="/billing/",
        )
    plan = PLANS[plan_id]
    import store

    count = current_count if current_count is not None else store.count_enabled_watches_for_user(user_id)
    if count >= plan.max_watches:
        return GateResult(
            False,
            "WATCH_LIMIT",
            f"监控条数已达上限（{count}/{plan.max_watches}），请升级套餐或停用部分规则",
            plan_id=plan_id,
            upgrade_url="/billing/",
        )
    return GateResult(True, plan_id=plan_id)
