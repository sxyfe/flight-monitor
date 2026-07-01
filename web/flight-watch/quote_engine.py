"""查价：RollingGo + swoop-flights（可选）。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from flight_search_engine import (  # noqa: E402
    RollingGoClient,
    flight_response_failed,
    flight_response_message,
)

from models import QuoteResult, Watch

RollingGoFactory = Callable[[], RollingGoClient]


def _rollinggo_date(date_str: str) -> str:
    """RollingGo 接受 YYYY-MM-DD，勿去掉连字符。"""
    return date_str.strip()


def _rollinggo_error(data: dict[str, Any]) -> str | None:
    if "error" in data:
        return str(data["error"])
    if flight_response_failed(data):
        return flight_response_message(data)
    return None


def _is_swoop_network_error(message: str | None) -> bool:
    if not message:
        return False
    lowered = message.lower()
    return any(
        token in lowered
        for token in (
            "connection error",
            "cannot decrypt",
            "sendrequest",
            "timed out",
            "timeout",
            "tls",
            "ssl",
        )
    )


def _pick_cheapest(flights: list[dict[str, Any]]) -> dict[str, Any] | None:
    valid = [f for f in flights if f.get("totalAdultPrice", 0) > 0]
    if not valid:
        return None
    return min(valid, key=lambda x: x["totalAdultPrice"])


def _fmt_seg(segs: list[dict[str, Any]]) -> str:
    parts = []
    for s in segs or []:
        parts.append(
            f"{s.get('flightNumber','')} {s.get('depAirport','')}→{s.get('arrAirport','')} "
            f"{(s.get('depTime') or '')[:10]}"
        )
    return " | ".join(parts) if parts else ""


def quote_rollinggo_round_trip(
    client: RollingGoClient, watch: Watch
) -> QuoteResult:
    if not watch.legs:
        return QuoteResult(None, watch.currency, "rollinggo", False, "", error="缺少航段")
    leg = watch.legs[0]
    if not watch.return_date:
        return QuoteResult(None, watch.currency, "rollinggo", False, "", error="缺少回程日期")
    data = client.search_flights(
        leg.from_city,
        leg.to_city,
        _rollinggo_date(leg.date),
        "ROUND_TRIP",
        ret_date=_rollinggo_date(watch.return_date),
        cabin=watch.filters.cabin,
    )
    if err := _rollinggo_error(data):
        return QuoteResult(None, watch.currency, "rollinggo", False, "", error=err)
    best = _pick_cheapest(data.get("flightInformationList") or [])
    if not best:
        return QuoteResult(None, watch.currency, "rollinggo", False, "", error="无航班")
    summary = _fmt_seg(best.get("fromSegments", [])) + " // " + _fmt_seg(best.get("retSegments", []))
    return QuoteResult(
        best["totalAdultPrice"],
        best.get("currency") or watch.currency,
        "rollinggo",
        True,
        summary,
    )


def quote_rollinggo_one_way(client: RollingGoClient, watch: Watch) -> QuoteResult:
    if not watch.legs:
        return QuoteResult(None, watch.currency, "rollinggo", False, "", error="缺少航段")
    leg = watch.legs[0]
    data = client.search_flights(
        leg.from_city,
        leg.to_city,
        _rollinggo_date(leg.date),
        "ONE_WAY",
        cabin=watch.filters.cabin,
    )
    if err := _rollinggo_error(data):
        return QuoteResult(None, watch.currency, "rollinggo", False, "", error=err)
    best = _pick_cheapest(data.get("flightInformationList") or [])
    if not best:
        return QuoteResult(None, watch.currency, "rollinggo", False, "", error="无航班")
    return QuoteResult(
        best["totalAdultPrice"],
        best.get("currency") or watch.currency,
        "rollinggo",
        True,
        _fmt_seg(best.get("fromSegments", [])),
    )


def quote_rollinggo_split(client: RollingGoClient, watch: Watch) -> QuoteResult:
    total = 0.0
    summaries: list[str] = []
    currency = watch.currency
    for leg in watch.legs:
        data = client.search_flights(
            leg.from_city,
            leg.to_city,
            _rollinggo_date(leg.date),
            "ONE_WAY",
            cabin=watch.filters.cabin,
        )
        if err := _rollinggo_error(data):
            return QuoteResult(None, currency, "rollinggo_split", False, "", error=err)
        best = _pick_cheapest(data.get("flightInformationList") or [])
        if not best:
            return QuoteResult(
                None,
                currency,
                "rollinggo_split",
                False,
                "",
                error=f"无航班 {leg.from_city}→{leg.to_city} {leg.date}",
            )
        total += best["totalAdultPrice"]
        currency = best.get("currency") or currency
        summaries.append(_fmt_seg(best.get("fromSegments", [])))
    return QuoteResult(
        total,
        currency,
        "rollinggo_split",
        False,
        " + ".join(summaries),
    )


def quote_swoop_same_ticket(watch: Watch) -> QuoteResult | None:
    if watch.pricing_mode == "split_one_way":
        return None
    try:
        from swoop import SORT_CHEAPEST, price_selector, search_legs, set_country
        from swoop.builders import SearchLeg
    except ImportError:
        return None

    if watch.sales_region:
        try:
            set_country(watch.sales_region.upper())
        except Exception:
            pass

    search_legs_list = [
        SearchLeg(
            date=leg.date,
            from_airport=leg.from_city,
            to_airport=leg.to_city,
            airlines=watch.filters.carriers or None,
        )
        for leg in watch.legs
    ]
    try:
        result = search_legs(search_legs_list, sort=SORT_CHEAPEST)
    except Exception as exc:
        return QuoteResult(None, watch.currency, "swoop", False, "", error=str(exc))

    candidates = [o for o in result.results if o.price is not None]
    candidates.sort(key=lambda x: x.price or 0)
    for opt in candidates[:8]:
        if not opt.selector:
            continue
        try:
            priced = price_selector(opt.selector)
        except Exception:
            continue
        if priced and priced.price is not None:
            leg_str = " | ".join(str(l) for l in opt.legs)
            return QuoteResult(
                float(priced.price),
                priced.currency or watch.currency,
                "swoop",
                True,
                leg_str,
                raw={"selector": opt.selector},
            )
    if candidates:
        best = candidates[0]
        leg_str = " | ".join(str(l) for l in best.legs)
        return QuoteResult(
            float(best.price),
            best.currency or watch.currency,
            "swoop",
            False,
            leg_str,
            raw={"note": "list_price_only"},
        )
    return QuoteResult(None, watch.currency, "swoop", False, "", error="swoop 无结果")


def quote_watch(watch: Watch, client_factory: RollingGoFactory) -> QuoteResult:
    client = client_factory()
    mode = watch.trip_mode
    if mode == "round_trip":
        return quote_rollinggo_round_trip(client, watch)
    if mode == "one_way":
        return quote_rollinggo_one_way(client, watch)
    if mode in ("multi_leg", "open_jaw"):
        if watch.pricing_mode == "split_one_way":
            return quote_rollinggo_split(client, watch)

        split = quote_rollinggo_split(client, watch)
        swoop: QuoteResult | None = None
        if watch.pricing_mode in ("auto", "same_ticket"):
            swoop = quote_swoop_same_ticket(watch)
            if swoop and swoop.success() and swoop.bookable:
                return swoop

        if split.success():
            return split
        if swoop and swoop.success():
            return swoop
        if split.error:
            if swoop and _is_swoop_network_error(swoop.error):
                return split
            return split
        if swoop and swoop.error:
            return swoop
        return split
    return QuoteResult(None, watch.currency, "unknown", False, "", error=f"未知 trip_mode: {mode}")
