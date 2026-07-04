"""会员套餐定义与权益。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PlanId = Literal[
    "free_trial",
    "week",
    "two_weeks",
    "month",
    "year",
    "lifetime",
]

BillingMode = Literal["one_time", "subscription"]


@dataclass(frozen=True)
class Plan:
    id: PlanId
    name: str
    tagline: str
    price_cny: int  # 分
    duration_days: int | None  # None = 永久
    billing_mode: BillingMode
    search_queries_per_day: int
    max_watches: int
    exhaustive_enabled: bool
    matrix_enabled: bool
    highlight: bool = False


PLANS: dict[PlanId, Plan] = {
    "free_trial": Plan(
        id="free_trial",
        name="免费试用",
        tagline="注册即享 7 天体验",
        price_cny=0,
        duration_days=7,
        billing_mode="one_time",
        search_queries_per_day=30,
        max_watches=1,
        exhaustive_enabled=False,
        matrix_enabled=True,
    ),
    "week": Plan(
        id="week",
        name="一周会员",
        tagline="短途出行扫价",
        price_cny=1900,
        duration_days=7,
        billing_mode="one_time",
        search_queries_per_day=200,
        max_watches=3,
        exhaustive_enabled=True,
        matrix_enabled=True,
    ),
    "two_weeks": Plan(
        id="two_weeks",
        name="两周会员",
        tagline="双周深度穷举",
        price_cny=2900,
        duration_days=14,
        billing_mode="one_time",
        search_queries_per_day=400,
        max_watches=5,
        exhaustive_enabled=True,
        matrix_enabled=True,
    ),
    "month": Plan(
        id="month",
        name="月度会员",
        tagline="持续监控 + 全量穷举",
        price_cny=4900,
        duration_days=30,
        billing_mode="subscription",
        search_queries_per_day=800,
        max_watches=10,
        exhaustive_enabled=True,
        matrix_enabled=True,
        highlight=True,
    ),
    "year": Plan(
        id="year",
        name="年度会员",
        tagline="全年不限心",
        price_cny=39900,
        duration_days=365,
        billing_mode="subscription",
        search_queries_per_day=2000,
        max_watches=30,
        exhaustive_enabled=True,
        matrix_enabled=True,
    ),
    "lifetime": Plan(
        id="lifetime",
        name="永久会员",
        tagline="一次付费，长期可用",
        price_cny=99900,
        duration_days=None,
        billing_mode="one_time",
        search_queries_per_day=5000,
        max_watches=50,
        exhaustive_enabled=True,
        matrix_enabled=True,
    ),
}

PAID_PLAN_IDS: tuple[PlanId, ...] = (
    "week",
    "two_weeks",
    "month",
    "year",
    "lifetime",
)


def plan_to_dict(plan: Plan) -> dict:
    return {
        "id": plan.id,
        "name": plan.name,
        "tagline": plan.tagline,
        "price_cny": plan.price_cny,
        "price_display": f"¥{plan.price_cny / 100:.2f}".rstrip("0").rstrip("."),
        "duration_days": plan.duration_days,
        "billing_mode": plan.billing_mode,
        "search_queries_per_day": plan.search_queries_per_day,
        "max_watches": plan.max_watches,
        "exhaustive_enabled": plan.exhaustive_enabled,
        "matrix_enabled": plan.matrix_enabled,
        "highlight": plan.highlight,
    }


def list_plans_public() -> list[dict]:
    return [plan_to_dict(PLANS[pid]) for pid in PLANS]
