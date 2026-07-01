#!/usr/bin/env python3
"""实时查价 CLI（smart / exhaustive）。"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from config import OUTPUT_DIR, ensure_api_key, setup_scripts_path

setup_scripts_path()

from flight_search_engine import (  # noqa: E402
    CONCURRENCY,
    HIGH_COST_THRESHOLD,
    ORIGINS,
    RollingGoClient,
    SearchIntent,
    build_search_meta,
    resolve_origins,
    search,
    validate_intent,
)

AVG_LATENCY_SEC = 1.0
DEFAULT_OUTPUT = OUTPUT_DIR / "search_result.json"


def load_intent(path: Path | None) -> SearchIntent:
    if path:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if "intent" in raw:
            raw = raw["intent"]
        return SearchIntent.from_dict(raw)
    return SearchIntent(
        origins=list(ORIGINS.keys()),
        destinations=[],
        countries=["泰国", "菲律宾", "印度尼西亚", "马来西亚", "日本"],
        date_start="2026-09-25",
        date_end="2026-10-07",
        min_stay_days=7,
        max_price=3000,
        trip_modes=["round_trip", "open_jaw"],
    )


def estimate_seconds(queries: int) -> int:
    return max(1, math.ceil(queries / CONCURRENCY) * AVG_LATENCY_SEC)


def main() -> None:
    parser = argparse.ArgumentParser(description="RollingGo 实时查价（smart / exhaustive）")
    parser.add_argument("--intent", "-i", type=Path, help="SearchIntent JSON")
    parser.add_argument(
        "--mode",
        "-m",
        choices=["smart", "exhaustive"],
        required=True,
        help="smart=热门城市子集；exhaustive=全量穷举",
    )
    parser.add_argument("--output", "-o", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-price", type=float, help="覆盖 intent.max_price")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help=f"确认执行高成本查价（预估 > {HIGH_COST_THRESHOLD} 次 API）",
    )
    parser.add_argument(
        "--estimate-only",
        action="store_true",
        help="仅输出预估次数与耗时，不查价",
    )
    args = parser.parse_args()

    settings = ensure_api_key()
    intent = load_intent(args.intent)
    if args.max_price is not None:
        intent.max_price = args.max_price

    client = RollingGoClient(settings.base_url, settings.api_key)
    validation = validate_intent(intent, client)
    est = (
        validation.estimated_queries_exhaustive
        if args.mode == "exhaustive"
        else validation.estimated_queries_smart
    )
    eta = estimate_seconds(est)

    print(
        f"模式: {args.mode} | 预估 API: {est} 次 | 约 {eta}s（{CONCURRENCY} 并发，仅供参考）",
        flush=True,
    )

    if not validation.valid:
        print("校验失败:", validation.errors, file=sys.stderr)
        if validation.clarifications:
            print("待澄清:", validation.clarifications, file=sys.stderr)
        sys.exit(1)

    if args.estimate_only:
        print(
            json.dumps(
                {
                    "mode": args.mode,
                    "estimated_queries": est,
                    "estimated_seconds": eta,
                    "smart_queries": validation.estimated_queries_smart,
                    "exhaustive_queries": validation.estimated_queries_exhaustive,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if est > HIGH_COST_THRESHOLD and not args.confirm:
        print(
            f"拒绝执行：预估 {est} 次 API 超过 {HIGH_COST_THRESHOLD}。"
            f"请使用 --mode smart、缩小日期/目的地，或加 --confirm 明确确认。",
            file=sys.stderr,
        )
        sys.exit(2)

    def on_progress(done: int, total: int) -> None:
        if done % 50 == 0 or done == total:
            print(f"进度: {done}/{total}", flush=True)

    result = search(client, intent, mode=args.mode, on_progress=on_progress)
    rt_hits = [o for o in result.offers if o["trip_type"] == "round_trip"]
    oj_hits = [o for o in result.offers if o["trip_type"] == "open_jaw"]

    dest_codes: set[str] = set()
    for o in result.offers:
        for key in ("out_dest", "dest", "ret_dest"):
            if o.get(key):
                dest_codes.add(str(o[key]))
    search_meta = build_search_meta(list(dest_codes), result.offers)
    origin_codes = resolve_origins(intent)

    summary = {
        "max_price": intent.max_price,
        "min_stay_days": intent.min_stay_days,
        "max_stay_days": intent.max_stay_days,
        "date_range": [intent.date_start, intent.date_end],
        "search_mode": args.mode,
        "estimated_queries": est,
        "origins": {k: ORIGINS[k] for k in origin_codes if k in ORIGINS},
        "code_to_country": search_meta.get("code_to_country", {}),
        "errors": result.stats.errors,
        "rt_hits": rt_hits,
        "oj_hits": oj_hits,
        "aggregations": result.aggregations,
        "stats": result.stats.__dict__,
        "intent": intent.to_dict(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n往返命中: {len(rt_hits)} | 开口程命中: {len(oj_hits)}", flush=True)
    print(f"结果: {args.output}", flush=True)


if __name__ == "__main__":
    main()
