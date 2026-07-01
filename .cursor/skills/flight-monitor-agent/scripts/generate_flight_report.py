#!/usr/bin/env python3
"""从查价 JSON 生成暖色统一 HTML 报告（筛选、图表、排序、分页）。"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import OUTPUT_DIR, setup_scripts_path

setup_scripts_path()

from flight_search_engine import aggregate  # noqa: E402

DEFAULT_OUTPUT_ROOT = OUTPUT_DIR / "reports"
TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates" / "report"


def load_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_offers(data: dict[str, Any]) -> list[dict[str, Any]]:
    if data.get("offers"):
        return list(data["offers"])
    offers: list[dict[str, Any]] = []
    for hit in data.get("rt_hits") or []:
        o = dict(hit)
        o.setdefault("trip_type", "round_trip")
        o.setdefault("out_dest", o.get("dest"))
        o.setdefault("out_dest_name", o.get("dest_name"))
        offers.append(o)
    for hit in data.get("oj_hits") or []:
        o = dict(hit)
        o.setdefault("trip_type", "open_jaw")
        offers.append(o)
    offers.sort(key=lambda x: x.get("price", 0))
    for i, o in enumerate(offers):
        o.setdefault("id", f"hit-{i}")
    return offers


def _pick_name(o: dict[str, Any], code_key: str, name_key: str) -> str:
    code = o.get(code_key) or ""
    return str(o.get(name_key) or code)


def build_locations(
    data: dict[str, Any], offers: list[dict[str, Any]]
) -> tuple[dict[str, str], dict[str, dict[str, dict[str, str]]]]:
    """从命中结果与 intent 动态构建出发地、目的地（按国家分组）映射。"""
    code_to_country: dict[str, str] = {}
    if isinstance(data.get("code_to_country"), dict):
        code_to_country.update({k: v for k, v in data["code_to_country"].items() if k and v})

    intent = data.get("intent") or {}
    intent_countries = [c for c in (intent.get("countries") or []) if c]
    default_country = intent_countries[0] if len(intent_countries) == 1 else "其他"

    origins: dict[str, str] = {}
    dest_names: dict[str, str] = {}

    for o in offers:
        for code_key, name_key in (
            ("origin", "origin_name"),
            ("ret_origin", "ret_origin_name"),
        ):
            code = o.get(code_key)
            if code:
                origins[str(code)] = _pick_name(o, code_key, name_key)

        for code_key, name_key in (
            ("out_dest", "out_dest_name"),
            ("dest", "dest_name"),
            ("ret_dest", "ret_dest_name"),
        ):
            code = o.get(code_key)
            if not code:
                continue
            code = str(code)
            dest_names[code] = _pick_name(o, code_key, name_key)
            for country_key in ("dest_country", "country", "out_dest_country"):
                cc = o.get(country_key)
                if cc:
                    code_to_country[code] = str(cc)

    explicit = data.get("destinations_by_country")
    if isinstance(explicit, dict):
        for country, cities in explicit.items():
            if not isinstance(cities, dict):
                continue
            for code, info in cities.items():
                if code not in dest_names:
                    continue
                code_to_country.setdefault(str(code), str(country))
                if isinstance(info, dict) and info.get("name"):
                    dest_names[str(code)] = str(info["name"])

    data_origins = data.get("origins")
    if isinstance(data_origins, dict):
        for code, name in data_origins.items():
            if code and code not in origins and isinstance(name, str):
                origins[str(code)] = name

    dest_by_country: dict[str, dict[str, dict[str, str]]] = {}
    for code, name in sorted(dest_names.items()):
        country = code_to_country.get(code, default_country)
        dest_by_country.setdefault(country, {})[code] = {"name": name}

    return origins, dest_by_country


def offer_to_client(o: dict[str, Any], idx: int) -> dict[str, Any]:
    trip_type = o.get("trip_type") or o.get("type") or "round_trip"
    if trip_type not in ("round_trip", "open_jaw"):
        trip_type = "round_trip" if trip_type == "rt" else trip_type

    detail = o.get("detail")
    if isinstance(detail, dict):
        parts = [detail.get("out", ""), detail.get("ret", "")]
        detail_str = " · ".join(p for p in parts if p)
    else:
        detail_str = (detail or "").replace("|", " · ")

    price_out = o.get("price_out")
    price_ret = o.get("price_ret")
    if price_out is not None:
        price_out = float(price_out)
    if price_ret is not None:
        price_ret = float(price_ret)

    summary_out = o.get("summary_out") or ""
    summary_ret = o.get("summary_ret") or ""

    base = {
        "out": o.get("out_date") or o.get("out", ""),
        "ret": o.get("ret_date") or o.get("ret", ""),
        "stay_days": o.get("stay_days"),
        "price": float(o.get("price", 0)),
        "price_out": price_out,
        "price_ret": price_ret,
        "summary_out": summary_out or None,
        "summary_ret": summary_ret or None,
        "detail": detail_str or None,
    }

    if trip_type == "round_trip":
        dest = o.get("dest") or o.get("out_dest", "")
        return {
            **base,
            "id": idx,
            "type": "round_trip",
            "origin": o.get("origin", ""),
            "origin_name": o.get("origin_name"),
            "out_dest": dest,
            "out_dest_name": o.get("out_dest_name") or o.get("dest_name"),
            "ret_dest": dest,
            "ret_dest_name": o.get("ret_dest_name") or o.get("dest_name"),
            "ret_origin": o.get("origin", ""),
            "ret_origin_name": o.get("ret_origin_name") or o.get("origin_name"),
            "bookable": bool(o.get("bookable", True)),
        }

    return {
        **base,
        "id": idx,
        "type": "open_jaw",
        "origin": o.get("origin", ""),
        "origin_name": o.get("origin_name"),
        "out_dest": o.get("out_dest", ""),
        "out_dest_name": o.get("out_dest_name"),
        "ret_dest": o.get("ret_dest", ""),
        "ret_dest_name": o.get("ret_dest_name"),
        "ret_origin": o.get("ret_origin", ""),
        "ret_origin_name": o.get("ret_origin_name"),
        "bookable": bool(o.get("bookable", False)),
    }


def build_payload(data: dict[str, Any], offers: list[dict[str, Any]]) -> dict[str, Any]:
    meta_range = data.get("date_range") or ["", ""]
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    origins, dest_by_country = build_locations(data, offers)

    return {
        "meta": {
            "date_range": meta_range,
            "max_price": data.get("max_price"),
            "min_stay_days": data.get("min_stay_days"),
            "search_mode": data.get("search_mode"),
            "generated_at": generated,
        },
        "origins": origins,
        "destinations_by_country": dest_by_country,
        "offers": [offer_to_client(o, i) for i, o in enumerate(offers)],
    }


def build_html(payload: dict[str, Any]) -> str:
    shell = (TEMPLATES_DIR / "report.html").read_text(encoding="utf-8")
    css = (TEMPLATES_DIR / "report.css").read_text(encoding="utf-8")
    js = (TEMPLATES_DIR / "report.js").read_text(encoding="utf-8")
    data_json = json.dumps(payload, ensure_ascii=False)
    data_json = data_json.replace("</", "<\\/")

    html = shell.replace("/*__INLINE_CSS__*/", css)
    html = html.replace("/*__INLINE_JS__*/", js)
    html = html.replace("/*__REPORT_DATA__*/", data_json)
    return html


def generate_report(input_path: Path, output_dir: Path) -> dict[str, Any]:
    data = load_payload(input_path)
    offers = normalize_offers(data)
    ag = aggregate(offers)
    payload = build_payload(data, offers)

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "report.html"
    report_path.write_text(build_html(payload), encoding="utf-8")

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input": str(input_path),
        "total_hits": len(offers),
        "rt_count": sum(1 for o in offers if o.get("trip_type") == "round_trip"),
        "oj_count": sum(1 for o in offers if o.get("trip_type") == "open_jaw"),
        "cheapest_price": offers[0]["price"] if offers else None,
        "date_range": data.get("date_range"),
        "max_price": data.get("max_price"),
        "search_mode": data.get("search_mode"),
        "report_path": str(report_path),
        "by_destination": ag.get("by_destination"),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="从查价 JSON 生成 HTML 报告")
    parser.add_argument("--input", "-i", type=Path, required=True, help="查价结果 JSON")
    parser.add_argument("--output", "-o", type=Path, default=None, help="输出目录")
    args = parser.parse_args()
    out = args.output or (DEFAULT_OUTPUT_ROOT / datetime.now().strftime("%Y%m%d-%H%M%S"))
    summary = generate_report(args.input.resolve(), out.resolve())
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
