from __future__ import annotations

import json
import urllib.error
import urllib.request


def send_text(webhook_url: str, text: str) -> None:
    body = json.dumps({"msg_type": "text", "content": {"text": text}}).encode()
    req = urllib.request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        resp.read()


def send_test(webhook_url: str) -> str:
    msg = "Flight Watch 测试：飞书 Webhook 已连接成功。"
    send_text(webhook_url, msg)
    return msg
