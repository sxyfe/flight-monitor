"""将 nl-search 命中结果转换为 exhaustive-viz 可读 bundle。"""
from __future__ import annotations

from typing import Any


def offers_to_viz_bundle(
    offers: list[dict[str, Any]],
    meta: dict[str, Any] | None = None,
    search_id: str | None = None,
) -> dict[str, Any]:
    rt_hits: list[dict[str, Any]] = []
    oj_hits: list[dict[str, Any]] = []
    destinations_by_country: dict[str, dict[str, dict[str, Any]]] = {}

    for o in offers or []:
        trip = o.get("trip_type") or "round_trip"
        dest_code = o.get("dest") or o.get("out_dest") or ""
        dest_name = o.get("dest_name") or o.get("out_dest_name") or dest_code
        country = (meta or {}).get("country_labels", {}).get(dest_code) or "其他"

        if country not in destinations_by_country:
            destinations_by_country[country] = {}
        if dest_code and dest_code not in destinations_by_country[country]:
            destinations_by_country[country][dest_code] = {"name": dest_name, "airports": [dest_code]}

        if trip == "open_jaw":
            oj_hits.append(
                {
                    "origin": o.get("origin"),
                    "out_dest": o.get("out_dest"),
                    "ret_dest": o.get("ret_dest"),
                    "ret_origin": o.get("ret_origin"),
                    "out": o.get("out_date"),
                    "ret": o.get("ret_date"),
                    "stay_days": o.get("stay_days"),
                    "price": o.get("price"),
                    "detail": o.get("detail"),
                }
            )
        else:
            rt_hits.append(
                {
                    "origin": o.get("origin"),
                    "dest": o.get("dest") or o.get("out_dest"),
                    "out": o.get("out_date"),
                    "ret": o.get("ret_date"),
                    "stay_days": o.get("stay_days"),
                    "price": o.get("price"),
                    "detail": o.get("detail") or o.get("summary_out"),
                }
            )

    return {
        "rt_hits": rt_hits,
        "oj_hits": oj_hits,
        "destinations_by_country": destinations_by_country,
        "meta": {
            **(meta or {}),
            "source": "nl-search",
            "search_id": search_id,
            "rt_count": len(rt_hits),
            "oj_count": len(oj_hits),
        },
    }
