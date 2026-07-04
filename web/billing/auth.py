"""JWT 与密码哈希。"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

JWT_SECRET = os.environ.get("BILLING_JWT_SECRET", "dev-change-me-in-production")
JWT_ALG = "HS256"
JWT_EXPIRE_DAYS = int(os.environ.get("BILLING_JWT_EXPIRE_DAYS", "30"))
COOKIE_NAME = "fm_token"


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt.encode("utf-8"),
        n=2**14,
        r=8,
        p=1,
        dklen=32,
    )
    return f"scrypt${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, digest_hex = stored.split("$", 2)
    except ValueError:
        return False
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt.encode("utf-8"),
        n=2**14,
        r=8,
        p=1,
        dklen=32,
    )
    return hmac.compare_digest(digest.hex(), digest_hex)


def create_token(user_id: str, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=JWT_EXPIRE_DAYS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.PyJWTError:
        return None
