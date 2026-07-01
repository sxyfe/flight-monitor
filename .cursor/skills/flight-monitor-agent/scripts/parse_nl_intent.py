#!/usr/bin/env python3
"""自然语言 → RollingGo SearchIntent JSON（CLI）。"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

from config import AVG_LATENCY_SEC, load_settings, setup_scripts_path

setup_scripts_path()

from flight_search_engine import CONCURRENCY, RollingGoClient  # noqa: E402
from nl_parser import parse_query  # noqa: E402


def validation_dict(v: Any) -> dict[str, Any]:
    smart = v.estimated_queries_smart
    exhaustive = v.estimated_queries_exhaustive
    return {
        "valid": v.valid,
        "warnings": v.warnings,
        "errors": v.errors,
        "clarifications": v.clarifications,
        "estimated_queries_smart": smart,
        "estimated_queries_exhaustive": exhaustive,
        "estimated_seconds_smart": max(1, math.ceil(smart / CONCURRENCY) * AVG_LATENCY_SEC),
        "estimated_seconds_exhaustive": max(
            1, math.ceil(exhaustive / CONCURRENCY) * AVG_LATENCY_SEC
        ),
        "recommended_mode": "smart" if smart <= exhaustive else "exhaustive",
    }


def rollinggo_client() -> RollingGoClient | None:
    settings = load_settings()
    if not settings.api_key:
        return None
    return RollingGoClient(settings.base_url, settings.api_key)


def main() -> None:
    parser = argparse.ArgumentParser(description="自然语言解析为 RollingGo SearchIntent JSON")
    parser.add_argument("query", nargs="?", help="自然语言查询")
    parser.add_argument("-q", "--query-text", dest="query_text", help="自然语言查询（替代位置参数）")
    parser.add_argument("--rules-only", action="store_true", help="仅用规则回退解析，不调用 LLM")
    parser.add_argument("-o", "--output", type=Path, help="写入 JSON 文件（含 intent 与 validation）")
    parser.add_argument("--intent-only", action="store_true", help="stdout 仅输出 intent 对象")
    parser.add_argument("--llm-base-url", default=os.environ.get("LLM_BASE_URL"))
    parser.add_argument("--llm-api-key", default=os.environ.get("LLM_API_KEY"))
    parser.add_argument("--llm-model", default=os.environ.get("LLM_MODEL", "gpt-4o-mini"))
    parser.add_argument("--no-rollinggo", action="store_true", help="不调用 RollingGo 机场搜索消歧")
    args = parser.parse_args()

    query = args.query_text or args.query
    if not query:
        parser.error("请提供自然语言查询（位置参数或 -q）")

    rg: RollingGoClient | None = None
    if not args.no_rollinggo:
        rg = rollinggo_client()

    intent, validation = parse_query(
        query,
        args.llm_base_url,
        args.llm_api_key,
        args.llm_model,
        rg,
        use_llm=not args.rules_only,
    )

    payload = {
        "query": query,
        "intent": intent.to_dict(),
        "validation": validation_dict(validation),
    }

    if args.intent_only:
        out = json.dumps(intent.to_dict(), ensure_ascii=False, indent=2)
    else:
        out = json.dumps(payload, ensure_ascii=False, indent=2)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(out + "\n", encoding="utf-8")
        print(f"已写入 {args.output}", file=sys.stderr)
    else:
        print(out)


if __name__ == "__main__":
    main()
