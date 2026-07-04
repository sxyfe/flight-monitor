"""跨子应用订阅门禁（gateway 同进程调用）。"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

WEB = Path(__file__).resolve().parent.parent
BILLING_DIR = WEB / "billing"

# 追加到 path 末尾，避免覆盖 nl-search / flight-watch 的 server 模块解析
if str(BILLING_DIR) not in sys.path:
    sys.path.append(str(BILLING_DIR))


def billing_available() -> bool:
    return BILLING_DIR.is_dir() and (BILLING_DIR / "entitlements.py").is_file()


def _enabled() -> bool:
    return os.environ.get("BILLING_ENABLED", "true").lower() in ("1", "true", "yes")


def get_user_from_request(request) -> str | None:
    if not billing_available() or not _enabled():
        return None
    from auth import COOKIE_NAME, decode_token

    token = request.cookies.get(COOKIE_NAME)
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
    if not token:
        return None
    payload = decode_token(token)
    return payload.get("sub") if payload else None


def check_search_allowed(user_id: str | None, **kwargs) -> Any:
    if not billing_available() or not _enabled():
        from dataclasses import dataclass

        @dataclass
        class _Ok:
            allowed: bool = True
            code: str = "OK"
            message: str = ""

        return _Ok()
    from entitlements import check_search_allowed as _check

    return _check(user_id, **kwargs)


def check_watch_allowed(user_id: str | None, **kwargs) -> Any:
    if not billing_available() or not _enabled():
        from dataclasses import dataclass

        @dataclass
        class _Ok:
            allowed: bool = True
            code: str = "OK"
            message: str = ""

        return _Ok()
    from entitlements import check_watch_allowed as _check

    return _check(user_id, **kwargs)


def record_search_usage(user_id: str | None, count: int = 1) -> None:
    if not billing_available() or not _enabled() or not user_id:
        return
    from entitlements import record_search_usage as _rec

    _rec(user_id, count)


def get_entitlements(user_id: str | None) -> dict[str, Any]:
    if not billing_available() or not _enabled():
        return {"billing_enabled": False, "unlimited": True}
    from entitlements import get_entitlements as _get

    return _get(user_id)
