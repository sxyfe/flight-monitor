"""Stripe Checkout 与 Mock 支付。"""
from __future__ import annotations

import os
from typing import Any
from urllib.parse import urljoin

from plans import PLANS, PlanId

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://127.0.0.1:7860").rstrip("/")
BILLING_MOCK_PAY = os.environ.get("BILLING_MOCK_PAY", "auto").lower()


def _mock_mode() -> bool:
    if BILLING_MOCK_PAY == "true":
        return True
    if BILLING_MOCK_PAY == "false":
        return False
    return not STRIPE_SECRET_KEY


def stripe_configured() -> bool:
    return bool(STRIPE_SECRET_KEY) and not _mock_mode()


def create_checkout_session(
    user_id: str,
    email: str,
    plan_id: PlanId,
    order_id: str,
) -> dict[str, Any]:
    plan = PLANS[plan_id]
    if plan.price_cny <= 0:
        raise ValueError("免费套餐无需支付")

    success_url = f"{PUBLIC_BASE_URL}/billing/?checkout=success&order={order_id}"
    cancel_url = f"{PUBLIC_BASE_URL}/billing/?checkout=cancel&order={order_id}"

    if _mock_mode():
        return {
            "mode": "mock",
            "checkout_url": f"{PUBLIC_BASE_URL}/billing/api/checkout/mock-complete?order_id={order_id}",
            "session_id": f"mock_{order_id}",
        }

    import stripe

    stripe.api_key = STRIPE_SECRET_KEY
    line_item: dict[str, Any] = {
        "price_data": {
            "currency": "cny",
            "product_data": {"name": f"Flight Monitor · {plan.name}"},
            "unit_amount": plan.price_cny,
        },
        "quantity": 1,
    }
    kwargs: dict[str, Any] = {
        "mode": "subscription" if plan.billing_mode == "subscription" else "payment",
        "line_items": [line_item],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": order_id,
        "customer_email": email,
        "metadata": {"user_id": user_id, "plan_id": plan_id, "order_id": order_id},
    }
    if plan.billing_mode == "subscription":
        line_item["price_data"]["recurring"] = {
            "interval": "month" if plan_id == "month" else "year",
        }
    session = stripe.checkout.Session.create(**kwargs)
    return {"mode": "stripe", "checkout_url": session.url, "session_id": session.id}


def complete_mock_order(order_id: str) -> dict[str, Any]:
    import store

    order = store.get_order(order_id)
    if not order:
        raise ValueError("订单不存在")
    if order["status"] == "paid":
        return {"ok": True, "already_paid": True}
    store.mark_order_paid(order_id)
    sub = store.grant_subscription(order["user_id"], order["plan_id"])
    return {"ok": True, "subscription": sub}


def handle_stripe_webhook(payload: bytes, sig_header: str) -> dict[str, Any]:
    if not STRIPE_WEBHOOK_SECRET:
        raise ValueError("未配置 STRIPE_WEBHOOK_SECRET")
    import stripe

    stripe.api_key = STRIPE_SECRET_KEY
    event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    import store

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        order_id = session.get("client_reference_id") or session.get("metadata", {}).get("order_id")
        if not order_id:
            return {"ok": False, "reason": "missing order_id"}
        order = store.get_order(order_id)
        if not order:
            return {"ok": False, "reason": "order not found"}
        store.mark_order_paid(order_id)
        meta = session.get("metadata") or {}
        plan_id = meta.get("plan_id") or order["plan_id"]
        user_id = meta.get("user_id") or order["user_id"]
        store.grant_subscription(
            user_id,
            plan_id,
            stripe_customer_id=session.get("customer"),
            stripe_subscription_id=session.get("subscription"),
        )
        return {"ok": True, "event": event["type"]}
    if event["type"] in ("customer.subscription.deleted", "customer.subscription.updated"):
        sub_obj = event["data"]["object"]
        if event["type"] == "customer.subscription.deleted" or sub_obj.get("status") == "canceled":
            stripe_sub_id = sub_obj.get("id")
            if stripe_sub_id:
                with store._conn() as conn:  # noqa: SLF001 — internal for webhook
                    row = conn.execute(
                        "SELECT user_id FROM subscriptions WHERE stripe_subscription_id = ? AND status = 'active'",
                        (stripe_sub_id,),
                    ).fetchone()
                    if row:
                        store.cancel_subscription(row["user_id"])
        return {"ok": True, "event": event["type"]}
    return {"ok": True, "ignored": event["type"]}
