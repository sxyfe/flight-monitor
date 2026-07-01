#!/usr/bin/env python3
"""穷举搜索 CLI（调用 flight_search_engine）。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from flight_search_engine import (  # noqa: E402
    DESTINATIONS_BY_COUNTRY,
    ORIGINS,
    RollingGoClient,
    SearchIntent,
    search,
    validate_intent,
)

MAX_PRICE = 3000
OUTPUT = Path(__file__).parent / "exhaustive_results.json"


def load_token() -> str:
    mcp = Path.home() / ".cursor/mcp.json"
    data = json.loads(mcp.read_text())
    return data["mcpServers"]["RollingGo-Flight"]["headers"]["Authorization"].split(" ", 1)[1]


def main():
    intent = SearchIntent(
        origins=list(ORIGINS.keys()),
        destinations=[],
        countries=["泰国", "菲律宾", "印度尼西亚", "马来西亚", "日本"],
        date_start="2026-09-25",
        date_end="2026-10-07",
        min_stay_days=7,
        max_price=MAX_PRICE,
        trip_modes=["round_trip", "open_jaw"],
    )
    validation = validate_intent(intent)
    print(f"预估查询: {validation.estimated_queries_exhaustive}", flush=True)
    client = RollingGoClient("https://mcp.rollinggo.cn", load_token())

    def on_progress(done, total):
        if done % 100 == 0:
            print(f"进度: {done}/{total}", flush=True)

    result = search(client, intent, mode="exhaustive", on_progress=on_progress)
    rt_hits = [o for o in result.offers if o["trip_type"] == "round_trip"]
    oj_hits = [o for o in result.offers if o["trip_type"] == "open_jaw"]

    summary = {
        "max_price": MAX_PRICE,
        "min_stay_days": intent.min_stay_days,
        "date_range": [intent.date_start, intent.date_end],
        "origins": ORIGINS,
        "destinations_by_country": DESTINATIONS_BY_COUNTRY,
        "errors": result.stats.errors,
        "rt_hits": rt_hits,
        "oj_hits": oj_hits,
        "rt_cheapest": rt_hits[:20],
        "oj_cheapest": oj_hits[:20],
        "aggregations": result.aggregations,
        "stats": result.stats.__dict__,
    }
    OUTPUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n往返命中: {len(rt_hits)} | 开口程命中: {len(oj_hits)}", flush=True)
    print(f"详细结果: {OUTPUT}", flush=True)


if __name__ == "__main__":
    main()
