#!/usr/bin/env python3
"""RollingGo API 连通性自检。"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

from config import ensure_api_key, setup_scripts_path

setup_scripts_path()


def main() -> None:
    settings = ensure_api_key()
    body = json.dumps({"keyword": "北京"}).encode()
    req = urllib.request.Request(
        f"{settings.base_url}/api/mcp/airportsearch",
        data=body,
        headers={
            "Authorization": f"Bearer {settings.api_key}",
            "Content-Type": "application/json",
            "Accept-Language": "zh_CN",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"连接失败: {e}", file=sys.stderr)
        sys.exit(1)

    airports = data.get("airPortInformationList") or []
    if airports:
        print(f"OK: RollingGo 连通正常，机场搜索返回 {len(airports)} 条（{data.get('message', '')}）")
    else:
        print(f"警告: 请求成功但无机场数据 — {data.get('message', data)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
