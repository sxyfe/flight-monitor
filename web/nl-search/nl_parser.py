"""自然语言 → SearchIntent（优先复用本地 Skill，生产环境内置规则回退）。"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

from flight_search_engine import (  # noqa: E402
    DESTINATIONS,
    DESTINATIONS_BY_COUNTRY,
    RollingGoClient,
    SearchIntent,
    ValidationResult,
    resolve_city_codes,
    validate_intent,
)
from holiday_windows import resolve_national_day_window  # noqa: E402

_SKILL_NL = (
    Path(__file__).resolve().parents[2]
    / ".cursor/skills/flight-monitor-agent/scripts/nl_parser.py"
)

_FALLBACK_ORIGIN_CODES = {
    "北京": "BJS",
    "天津": "TSN",
    "河北": "SJW",
    "山西": "TYN",
    "石家庄": "SJW",
    "太原": "TYN",
}

_TODAY = date.today().isoformat()

SYSTEM_PROMPT = f"""你是机票搜索意图解析器。参考日期 today={_TODAY}，所有 date_start/date_end 必须是 today 当天或之后的未来日期。

国庆日期规则：
- 用户说「国庆前后」或「国庆节前后」→ date_start=当年或次年的 09-28，date_end=10-10
- 用户只说「国庆」→ date_start=10-01，date_end=10-07
- 若当年窗口已过去则用次年

根据用户中文描述输出 JSON，字段：
- origins: 城市 IATA 编码数组（北京 BJS、天津 TSN；省份可用石家庄 SJW、太原 TYN 等）
- origin_names: 可选，中文出发地名称数组，供机场搜索消歧
- destinations: 目的地城市编码数组
- destination_names: 可选，中文目的地名称数组
- countries: 国家中文名数组（泰国、菲律宾、印度尼西亚、马来西亚、日本）
- date_start, date_end: YYYY-MM-DD
- min_stay_days: 整数，默认 7
- max_stay_days: 整数或 null（最多停留天数，不设表示不限制）
- max_price: 数字或 null
- trip_modes: ["round_trip"] 和/或 ["open_jaw"]
- cabin: ECONOMY
- adults: 1
- children: 0
只输出 JSON，不要 markdown。"""


def _load_skill_parser():
    if not _SKILL_NL.exists():
        return None
    skill_scripts = _SKILL_NL.parent
    if str(skill_scripts) not in sys.path:
        sys.path.insert(0, str(skill_scripts))
    spec = importlib.util.spec_from_file_location("flight_monitor_skill_nl_parser", _SKILL_NL)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


_SKILL_MOD = _load_skill_parser()

if _SKILL_MOD is not None:
    SYSTEM_PROMPT = _SKILL_MOD.SYSTEM_PROMPT
    enrich_intent = _SKILL_MOD.enrich_intent
    parse_query = _SKILL_MOD.parse_query
    parse_with_llm = _SKILL_MOD.parse_with_llm
    parse_with_rules = _SKILL_MOD.parse_with_rules
else:

    def _http_post_json(url: str, headers: dict[str, str], body: dict[str, Any]) -> dict[str, Any]:
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode(),
            headers={**headers, "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            return json.loads(resp.read())

    def parse_with_llm(
        query: str,
        base_url: str,
        api_key: str,
        model: str,
    ) -> dict[str, Any]:
        url = f"{base_url.rstrip('/')}/chat/completions"
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }
        data = _http_post_json(url, {"Authorization": f"Bearer {api_key}"}, body)
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)

    def _apply_holiday_dates(raw: dict[str, Any], query: str) -> dict[str, Any]:
        win = resolve_national_day_window(query)
        if win:
            raw["date_start"], raw["date_end"] = win
        return raw

    def parse_with_rules(query: str) -> dict[str, Any]:
        """无 LLM 时的关键词回退解析。"""
        q = query.replace(" ", "")

        origin_names: list[str] = []
        for name in ["北京", "天津", "河北", "山西"]:
            if name in q:
                origin_names.append(name)
        origins = [_FALLBACK_ORIGIN_CODES[n] for n in origin_names if n in _FALLBACK_ORIGIN_CODES]
        origins = list(dict.fromkeys(origins))
        if not origins:
            origins = ["BJS", "TSN"]

        countries: list[str] = []
        for c in DESTINATIONS_BY_COUNTRY:
            if c.replace("尼西亚", "") in q or c in q:
                countries.append(c)
        if "东南亚" in q:
            countries = ["泰国", "菲律宾", "印度尼西亚", "马来西亚"]
        if "日本" in q and "日本" not in countries:
            countries.append("日本")

        max_price = None
        m = re.search(r"(\d{3,5})\s*(以内|以下|块|元)?", q)
        if m:
            max_price = float(m.group(1))

        min_stay = 7
        m2 = re.search(r"(?:至少|最少|玩)\s*(\d+)\s*天", q)
        if m2:
            min_stay = int(m2.group(1))

        max_stay = None
        m3 = re.search(r"(?:最多|不超过|至多)(?:玩|停留)?\s*(\d+)\s*天", q)
        if m3:
            max_stay = int(m3.group(1))

        trip_modes: list[str] = []
        if "开口" in q or "多城" in q:
            trip_modes.append("open_jaw")
        if "往返" in q or "来回" in q or not trip_modes:
            trip_modes.append("round_trip")

        win = resolve_national_day_window(q) or resolve_national_day_window("国庆前后")
        if win:
            date_start, date_end = win
        else:
            date_start, date_end = f"{date.today().year}-09-28", f"{date.today().year}-10-10"

        return {
            "origins": origins,
            "origin_names": origin_names,
            "destinations": [],
            "countries": countries,
            "date_start": date_start,
            "date_end": date_end,
            "min_stay_days": min_stay,
            "max_stay_days": max_stay,
            "max_price": max_price,
            "trip_modes": trip_modes,
            "cabin": "ECONOMY",
            "adults": 1,
            "children": 0,
        }

    def _as_str_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [v for v in value if isinstance(v, str)]

    def normalize_raw_intent(raw: dict[str, Any]) -> dict[str, Any]:
        """LLM 可能返回 null 列表字段，统一归一化后再构造 SearchIntent。"""
        trip_modes = _as_str_list(raw.get("trip_modes"))
        origins = _as_str_list(raw.get("origins"))
        return {
            **raw,
            "origins": origins or ["BJS", "TSN"],
            "destinations": _as_str_list(raw.get("destinations")),
            "countries": _as_str_list(raw.get("countries")),
            "trip_modes": trip_modes or ["round_trip", "open_jaw"],
            "origin_names": _as_str_list(raw.get("origin_names")),
            "destination_names": _as_str_list(raw.get("destination_names")),
        }

    def enrich_intent(raw: dict[str, Any], rollinggo: RollingGoClient | None) -> SearchIntent:
        raw = normalize_raw_intent(raw)
        if rollinggo:
            onames = raw["origin_names"]
            if onames:
                codes = resolve_city_codes(rollinggo, onames)
                if codes:
                    raw = {**raw, "origins": codes}
            dnames = raw["destination_names"]
            if dnames:
                codes = resolve_city_codes(rollinggo, dnames)
                if codes:
                    raw = {**raw, "destinations": codes}
        intent = SearchIntent.from_dict(raw)
        intent.destinations = [c for c in intent.destinations if c in DESTINATIONS or c]
        return intent

    def parse_query(
        query: str,
        llm_base_url: str | None,
        llm_api_key: str | None,
        llm_model: str,
        rollinggo: RollingGoClient | None,
        use_llm: bool = True,
    ) -> tuple[SearchIntent, ValidationResult]:
        raw: dict[str, Any]
        if use_llm and llm_base_url and llm_api_key:
            try:
                raw = parse_with_llm(query, llm_base_url, llm_api_key, llm_model)
                raw = _apply_holiday_dates(raw, query)
            except Exception:
                raw = parse_with_rules(query)
        else:
            raw = parse_with_rules(query)
        intent = enrich_intent(raw, rollinggo)
        validation = validate_intent(intent)
        return intent, validation

__all__ = [
    "SYSTEM_PROMPT",
    "enrich_intent",
    "parse_query",
    "parse_with_llm",
    "parse_with_rules",
]
