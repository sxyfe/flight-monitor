#!/usr/bin/env python3
"""示例：NL 解析 + 确认 + smart 搜索。"""
import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8765"
QUERY = (
    "北京、天津、河北、山西出发，国庆节前后前往日本至少玩七天，2500元以内往返，"
    "开口程都要查询，比如A城市到B城市，返回的时候C城市到D城市，A、D在我提供的出发地里面就行"
)


def post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=1200) as resp:
        return json.loads(resp.read())


def main():
    print("=== 1. 解析意图 ===")
    parsed = post("/api/intent/parse", {"query": QUERY})
    intent = parsed["intent"]
    val = parsed["validation"]
    print(json.dumps(intent, ensure_ascii=False, indent=2))
    print(f"校验: valid={val['valid']} smart={val['estimated_queries_smart']} exhaustive={val['estimated_queries_exhaustive']}")
    if not val["valid"]:
        print("警告:", val.get("errors"), val.get("clarifications"))

    print("\n=== 2. 确认（validate）===")
    confirmed = post("/api/intent/validate", {"intent": intent})
    print(json.dumps(confirmed["validation"], ensure_ascii=False, indent=2))

    print("\n=== 3. Smart 搜索（可能需数分钟）===")
    body = {"intent": intent, "mode": "smart", "confirmed_high_cost": True}
    try:
        result = post("/api/search", body)
    except urllib.error.HTTPError as e:
        err = json.loads(e.read())
        print("HTTP", e.code, err)
        sys.exit(1)

    stats = result.get("stats") or {}
    offers = result.get("offers") or []
    print(f"完成: {stats.get('total_queries')} 次查询, {stats.get('duration_ms')}ms")
    print(f"命中: {len(offers)} 条 (RT={stats.get('rt_count')} OJ={stats.get('oj_count')})")
    for o in offers[:10]:
        print(f"  ¥{o['price']} {o.get('trip_type')} {o.get('origin_name')} {o.get('route')} {o.get('out_date')}~{o.get('ret_date')}")


if __name__ == "__main__":
    main()
