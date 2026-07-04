"""Flight Monitor 订阅与支付 API。"""
from __future__ import annotations

import os
import re
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))

import auth
import entitlements
import store
import stripe_pay
from auth import COOKIE_NAME, create_token, hash_password, verify_password
from plans import PAID_PLAN_IDS, PLANS, list_plans_public

STATIC_DIR = APP_DIR / "static"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    store.init_db()
    yield


app = FastAPI(title="Flight Monitor Billing", version="1.0.0", lifespan=lifespan)
_cors = os.environ.get("ALLOWED_ORIGINS", "*").strip()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _cors == "*" else [o.strip() for o in _cors.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class RegisterBody(BaseModel):
    email: str
    password: str = Field(min_length=6, max_length=128)


class LoginBody(BaseModel):
    email: str
    password: str


class CheckoutBody(BaseModel):
    plan_id: str


def _cookie_opts() -> dict[str, Any]:
    secure = os.environ.get("PUBLIC_BASE_URL", "").startswith("https")
    return {
        "httponly": True,
        "samesite": "lax",
        "max_age": 86400 * int(os.environ.get("BILLING_JWT_EXPIRE_DAYS", "30")),
        "path": "/",
        "secure": secure,
    }


def _current_user(request: Request) -> dict[str, Any] | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        auth_h = request.headers.get("Authorization", "")
        if auth_h.lower().startswith("bearer "):
            token = auth_h[7:].strip()
    if not token:
        return None
    payload = auth.decode_token(token)
    if not payload:
        return None
    user = store.get_user(payload["sub"])
    return user


def require_user(request: Request) -> dict[str, Any]:
    user = _current_user(request)
    if not user:
        raise HTTPException(401, {"code": "UNAUTHORIZED", "message": "请先登录"})
    return user


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/plans")
async def api_plans():
    return {
        "plans": list_plans_public(),
        "stripe_configured": stripe_pay.stripe_configured(),
        "mock_pay": stripe_pay._mock_mode(),
        "billing_enabled": entitlements.BILLING_ENABLED,
    }


@app.get("/api/me")
async def api_me(request: Request):
    user = _current_user(request)
    if not user:
        return {"authenticated": False}
    ent = entitlements.get_entitlements(user["id"])
    sub = store.get_active_subscription(user["id"])
    return {
        "authenticated": True,
        "user": {"id": user["id"], "email": user["email"]},
        "subscription": sub,
        "entitlements": ent,
    }


@app.post("/api/auth/register")
async def api_register(body: RegisterBody, response: Response):
    email = body.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "邮箱格式无效")
    if store.get_user_by_email(email):
        raise HTTPException(409, "该邮箱已注册")
    user = store.create_user(email, hash_password(body.password))
    token = create_token(user["id"], user["email"])
    response.set_cookie(COOKIE_NAME, token, **_cookie_opts())
    return {
        "ok": True,
        "user": {"id": user["id"], "email": user["email"]},
        "entitlements": entitlements.get_entitlements(user["id"]),
    }


@app.post("/api/auth/login")
async def api_login(body: LoginBody, response: Response):
    user = store.get_user_by_email(body.email)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "邮箱或密码错误")
    token = create_token(user["id"], user["email"])
    response.set_cookie(COOKIE_NAME, token, **_cookie_opts())
    return {
        "ok": True,
        "user": {"id": user["id"], "email": user["email"]},
        "entitlements": entitlements.get_entitlements(user["id"]),
    }


@app.post("/api/auth/logout")
async def api_logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@app.post("/api/checkout")
async def api_checkout(body: CheckoutBody, request: Request, user: dict = Depends(require_user)):
    plan_id = body.plan_id
    if plan_id not in PAID_PLAN_IDS:
        raise HTTPException(400, "无效套餐")
    plan = PLANS[plan_id]
    order = store.create_order(user["id"], plan_id, plan.price_cny)
    session = stripe_pay.create_checkout_session(
        user["id"], user["email"], plan_id, order["id"]
    )
    if session.get("session_id"):
        import store as st

        with st._lock:  # noqa: SLF001
            with st._conn() as conn:  # noqa: SLF001
                conn.execute(
                    "UPDATE orders SET stripe_session_id = ? WHERE id = ?",
                    (session["session_id"], order["id"]),
                )
    return {"checkout_url": session["checkout_url"], "order_id": order["id"], "mode": session["mode"]}


@app.get("/api/checkout/mock-complete")
async def mock_complete(order_id: str):
    if not stripe_pay._mock_mode():
        raise HTTPException(403, "Mock 支付未启用")
    result = stripe_pay.complete_mock_order(order_id)
    return RedirectResponse("/billing/?checkout=success", status_code=302)


@app.post("/api/webhook/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    try:
        result = stripe_pay.handle_stripe_webhook(payload, sig)
    except Exception as e:
        raise HTTPException(400, str(e)) from e
    return result


@app.post("/api/subscription/cancel")
async def cancel_sub(user: dict = Depends(require_user)):
    sub = store.get_active_subscription(user["id"])
    if not sub:
        raise HTTPException(404, "无有效订阅")
    plan = PLANS.get(sub["plan_id"])
    if plan and plan.billing_mode == "subscription" and sub.get("stripe_subscription_id"):
        if stripe_pay.stripe_configured():
            import stripe

            stripe.api_key = stripe_pay.STRIPE_SECRET_KEY
            stripe.Subscription.cancel(sub["stripe_subscription_id"])
    store.cancel_subscription(user["id"])
    return {"ok": True}


@app.get("/api/entitlements")
async def api_entitlements(request: Request):
    user = _current_user(request)
    uid = user["id"] if user else None
    return entitlements.get_entitlements(uid)
