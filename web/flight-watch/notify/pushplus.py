from __future__ import annotations

import json
import urllib.request


def send(token: str, title: str, content: str) -> None:
    body = json.dumps(
        {"token": token, "title": title, "content": content, "template": "txt"}
    ).encode()
    req = urllib.request.Request(
        "https://www.pushplus.plus/send",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        resp.read()


def send_test(token: str) -> str:
    msg = "Flight Watch 测试：PushPlus 微信推送已连接成功。"
    send(token, "Flight Watch 测试", msg)
    return msg
