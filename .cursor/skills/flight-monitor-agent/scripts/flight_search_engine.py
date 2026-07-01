"""航班查询引擎：SearchIntent → RollingGo → FlightOffer 列表与聚合。"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable, Iterable, Literal

SearchMode = Literal["smart", "exhaustive"]
TripMode = Literal["round_trip", "open_jaw"]

ORIGINS: dict[str, str] = {
    "BJS": "北京",
    "TSN": "天津",
    "SJW": "石家庄",
    "TYN": "太原",
}

_CATALOG_PATH = Path(__file__).resolve().parent / "data" / "country_city_codes.json"
_country_catalog: dict[str, Any] | None = None

CONCURRENCY = 6
HIGH_COST_THRESHOLD = 500
SMART_UNKNOWN_COUNTRY_LIMIT = 6

_country_city_cache: dict[str, list[str]] = {}


def load_country_catalog(force: bool = False) -> dict[str, Any]:
    global _country_catalog
    if _country_catalog is not None and not force:
        return _country_catalog
    if _CATALOG_PATH.exists():
        _country_catalog = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    else:
        _country_catalog = {"countries": {}}
    return _country_catalog


def _build_maps_from_catalog() -> tuple[
    dict[str, dict[str, dict[str, Any]]],
    dict[str, str],
    dict[str, str],
    dict[str, list[str]],
]:
    catalog = load_country_catalog()
    destinations_by_country: dict[str, dict[str, dict[str, Any]]] = {}
    destinations: dict[str, str] = {}
    country_by_code: dict[str, str] = {}
    hot_cities: dict[str, list[str]] = {}
    for country, entry in catalog.get("countries", {}).items():
        codes = list(entry.get("exhaustive") or [])
        labels = entry.get("labels") or {}
        destinations_by_country[country] = {
            code: {"name": labels.get(code, code)} for code in codes
        }
        hot_cities[country] = list(entry.get("hot") or [])
        for code in codes:
            destinations[code] = labels.get(code, code)
            country_by_code[code] = country
    return destinations_by_country, destinations, country_by_code, hot_cities


(
    DESTINATIONS_BY_COUNTRY,
    DESTINATIONS,
    COUNTRY_BY_CODE,
    HOT_CITIES_BY_COUNTRY,
) = _build_maps_from_catalog()


@dataclass
class SearchIntent:
    origins: list[str]
    destinations: list[str]
    date_start: str
    date_end: str
    min_stay_days: int = 7
    max_stay_days: int | None = None
    max_price: float | None = None
    trip_modes: list[str] = field(default_factory=lambda: ["round_trip", "open_jaw"])
    countries: list[str] = field(default_factory=list)
    cabin: str = "ECONOMY"
    adults: int = 1
    children: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SearchIntent:
        return cls(
            origins=list(data.get("origins") or ["BJS"]),
            destinations=list(data.get("destinations") or []),
            date_start=str(data["date_start"]),
            date_end=str(data["date_end"]),
            min_stay_days=int(data.get("min_stay_days") or 7),
            max_stay_days=(
                int(data["max_stay_days"])
                if data.get("max_stay_days") not in (None, "")
                else None
            ),
            max_price=data.get("max_price"),
            trip_modes=list(data.get("trip_modes") or ["round_trip", "open_jaw"]),
            countries=list(data.get("countries") or []),
            cabin=str(data.get("cabin") or "ECONOMY"),
            adults=int(data.get("adults") or 1),
            children=int(data.get("children") or 0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "origins": self.origins,
            "destinations": self.destinations,
            "date_start": self.date_start,
            "date_end": self.date_end,
            "min_stay_days": self.min_stay_days,
            "max_stay_days": self.max_stay_days,
            "max_price": self.max_price,
            "trip_modes": self.trip_modes,
            "countries": self.countries,
            "cabin": self.cabin,
            "adults": self.adults,
            "children": self.children,
        }


@dataclass
class ValidationResult:
    valid: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    clarifications: list[str] = field(default_factory=list)
    estimated_queries_smart: int = 0
    estimated_queries_exhaustive: int = 0


@dataclass
class SearchStats:
    total_queries: int = 0
    errors: int = 0
    rt_count: int = 0
    oj_count: int = 0
    duration_ms: int = 0


@dataclass
class SearchResult:
    offers: list[dict[str, Any]]
    aggregations: dict[str, Any]
    stats: SearchStats
    meta: dict[str, Any] = field(default_factory=dict)
    ow_cache_built: bool = False


class RollingGoClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept-Language": "zh_CN",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}: {e.read().decode()}"}
        except Exception as e:
            return {"error": str(e)}

    def search_airports(self, keyword: str) -> dict[str, Any]:
        return self._post("/api/mcp/airportsearch", {"keyword": keyword})

    def search_flights(
        self,
        from_city: str,
        to_city: str,
        from_date: str,
        trip_type: str,
        ret_date: str | None = None,
        adults: int = 1,
        children: int = 0,
        cabin: str = "ECONOMY",
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "adultNumber": adults,
            "childNumber": children,
            "cabinGrade": cabin,
            "fromCity": from_city,
            "toCity": to_city,
            "fromDate": from_date,
            "tripType": trip_type,
        }
        if ret_date:
            body["retDate"] = ret_date
        return self._post("/api/mcp/flightsearch", body)


def stay_days(out: date, ret: date) -> int:
    return (ret - out).days


def date_range(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def stay_in_bounds(intent: SearchIntent, out: date, ret: date) -> bool:
    sd = stay_days(out, ret)
    if sd < intent.min_stay_days:
        return False
    if intent.max_stay_days is not None and sd > intent.max_stay_days:
        return False
    return True


def valid_date_pairs(intent: SearchIntent) -> list[tuple[date, date]]:
    start = date.fromisoformat(intent.date_start)
    end = date.fromisoformat(intent.date_end)
    pairs: list[tuple[date, date]] = []
    days = list(date_range(start, end))
    for out in days:
        for ret in days:
            if stay_in_bounds(intent, out, ret):
                pairs.append((out, ret))
    return pairs


def _country_api_keywords(country: str) -> list[str]:
    country = country.strip()
    keywords = [country]
    catalog = load_country_catalog()
    entry = catalog.get("countries", {}).get(country)
    if entry:
        for key in ("name_en", "iso"):
            val = entry.get(key)
            if val:
                keywords.append(str(val))
    else:
        low = country.lower()
        for zh, info in catalog.get("countries", {}).items():
            if low in (zh.lower(), str(info.get("name_en", "")).lower(), str(info.get("iso", "")).lower()):
                keywords.extend([zh, info.get("name_en", ""), info.get("iso", "")])
                break
    return list(dict.fromkeys(k.strip() for k in keywords if k and str(k).strip()))


def _search_airports_city_codes(client: RollingGoClient, keywords: list[str]) -> list[str]:
    codes: list[str] = []
    seen: set[str] = set()
    for kw in keywords:
        data = client.search_airports(kw)
        for item in data.get("airPortInformationList") or []:
            cc = (item.get("cityCode") or "").strip().upper()
            if cc and cc not in seen:
                seen.add(cc)
                codes.append(cc)
    return codes


def get_country_city_codes(country: str, mode: SearchMode = "exhaustive") -> dict[str, Any]:
    codes = resolve_country_cities(country, mode, client=None)
    catalog = load_country_catalog()
    entry = catalog.get("countries", {}).get(country) or {}
    labels = entry.get("labels") or {}
    return {
        "country": country,
        "mode": mode,
        "count": len(codes),
        "codes": codes,
        "labels": {code: labels.get(code, DESTINATIONS.get(code, code)) for code in codes},
        "in_catalog": country in catalog.get("countries", {}),
    }


def resolve_country_cities(
    country: str,
    mode: SearchMode,
    client: RollingGoClient | None = None,
) -> list[str]:
    cache_key = f"{country}:{mode}"
    if cache_key in _country_city_cache:
        return _country_city_cache[cache_key]

    catalog = load_country_catalog()
    entry = catalog.get("countries", {}).get(country)
    if entry:
        pool = list(entry.get("exhaustive") or [])
        if mode == "smart":
            hot = [c for c in entry.get("hot") or [] if c in pool]
            codes = hot or pool[:SMART_UNKNOWN_COUNTRY_LIMIT]
        else:
            codes = pool
        _country_city_cache[cache_key] = codes
        return codes

    if not client:
        return []

    keywords = _country_api_keywords(country)
    codes = _search_airports_city_codes(client, keywords)
    if mode == "smart":
        codes = codes[:SMART_UNKNOWN_COUNTRY_LIMIT]
    _country_city_cache[cache_key] = codes
    return codes


def resolve_destinations(
    intent: SearchIntent,
    mode: SearchMode,
    client: RollingGoClient | None = None,
) -> list[str]:
    codes: set[str] = set()
    for code in intent.destinations:
        c = (code or "").strip().upper()
        if len(c) == 3:
            codes.add(c)
    for country in intent.countries:
        for code in resolve_country_cities(country, mode, client):
            codes.add(code)
    if not codes and mode == "exhaustive":
        codes.update(DESTINATIONS.keys())
    if not codes and mode == "smart":
        for country in ("泰国", "菲律宾", "马来西亚", "印度尼西亚"):
            codes.update(resolve_country_cities(country, "smart", client))
    return sorted(codes)


def resolve_origins(intent: SearchIntent) -> list[str]:
    codes = [o.upper().strip() for o in intent.origins if o and len(o.strip()) == 3]
    if codes:
        return list(dict.fromkeys(codes))
    return ["BJS", "TSN"]


def estimate_query_count(
    intent: SearchIntent,
    mode: SearchMode,
    client: RollingGoClient | None = None,
) -> int:
    origins = resolve_origins(intent)
    dests = resolve_destinations(intent, mode, client)
    pairs = valid_date_pairs(intent)
    if not origins or not dests or not pairs:
        return 0
    out_days = sorted({out.isoformat() for out, _ in pairs})
    ret_days = sorted({ret.isoformat() for _, ret in pairs})
    rt = len(origins) * len(dests) * len(pairs)
    ow = 0
    if "open_jaw" in intent.trip_modes:
        ow = len(origins) * len(dests) * len(out_days) + len(dests) * len(origins) * len(ret_days)
    if "round_trip" not in intent.trip_modes:
        rt = 0
    if "open_jaw" not in intent.trip_modes:
        ow = 0
    return rt + ow


def validate_intent(intent: SearchIntent, client: RollingGoClient | None = None) -> ValidationResult:
    result = ValidationResult(valid=True)
    origins = resolve_origins(intent)
    if not origins:
        result.errors.append("请至少指定一个出发地机场编码")
    try:
        start = date.fromisoformat(intent.date_start)
        end = date.fromisoformat(intent.date_end)
    except ValueError:
        result.errors.append("日期格式无效，请使用 YYYY-MM-DD")
        start = end = None
    if start and end and start > end:
        result.errors.append("出发日期不能晚于结束日期")
    today = date.today()
    if start and start < today:
        result.errors.append("出发日期不能早于今天")
    if end and end < today:
        result.errors.append("结束日期不能早于今天")
    if (
        intent.max_stay_days is not None
        and intent.min_stay_days > intent.max_stay_days
    ):
        result.errors.append(
            f"最少停留 {intent.min_stay_days} 天不能大于最多停留 {intent.max_stay_days} 天"
        )
    if start and end:
        pairs = valid_date_pairs(intent)
        if not pairs:
            bounds = [f"最少停留 {intent.min_stay_days} 天"]
            if intent.max_stay_days is not None:
                bounds.append(f"最多停留 {intent.max_stay_days} 天")
            result.errors.append(
                f"在 {intent.date_start}~{intent.date_end} 内无法满足{'、'.join(bounds)}"
            )
    dests_smart = resolve_destinations(intent, "smart", client)
    dests_ex = resolve_destinations(intent, "exhaustive", client)
    if not dests_smart and not dests_ex:
        result.clarifications.append("请指定目的地城市或国家（如泰国、菲律宾）")
    catalog_countries = load_country_catalog().get("countries", {})
    for country in intent.countries:
        if country not in catalog_countries:
            cities = resolve_country_cities(country, "exhaustive", client)
            if not cities:
                result.warnings.append(
                    f"自定义国家「{country}」未解析到机场城市，请改填具体目的地或检查拼写"
                )
    if not intent.trip_modes:
        result.clarifications.append("请选择行程类型：往返联票、开口程，或两者都要")
    if intent.max_price and intent.max_price < 500:
        result.warnings.append("预算过低，可能难以找到国际航线")
    jp = [c for c in resolve_destinations(intent, "exhaustive", client) if COUNTRY_BY_CODE.get(c) == "日本"]
    if jp and intent.max_price and intent.max_price <= 3000:
        result.warnings.append("日本航线在同等预算下 rarely 命中低价，建议放宽预算或移除日本")
    result.estimated_queries_smart = estimate_query_count(intent, "smart", client)
    result.estimated_queries_exhaustive = estimate_query_count(intent, "exhaustive", client)
    if result.errors or result.clarifications:
        result.valid = False
    return result


def fmt_seg(segs: list[dict[str, Any]]) -> str:
    if not segs:
        return ""
    return " | ".join(
        f"{s['flightNumber']} {s['depAirport']}→{s['arrAirport']} {s['depTime'][5:16]}"
        for s in segs
    )


def seg_list(segs: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows = []
    for s in segs or []:
        dep = s.get("depTime", "")
        rows.append(
            {
                "flight": s.get("flightNumber", ""),
                "from": s.get("depAirport", ""),
                "to": s.get("arrAirport", ""),
                "dep": dep.replace("T", " ")[:16] if dep else "",
            }
        )
    return rows


def _cheapest(data: dict[str, Any]) -> dict[str, Any] | None:
    flights = data.get("flightInformationList") or []
    if not flights or "error" in data:
        return None
    return min(flights, key=lambda x: x["totalAdultPrice"])


def _offer_id() -> str:
    import uuid

    return f"offer_{uuid.uuid4().hex[:8]}"


def build_code_to_country(codes: Iterable[str]) -> dict[str, str]:
    """由 country_city_codes 目录反查城市 code → 国家名。"""
    out: dict[str, str] = {}
    for code in codes:
        if not code:
            continue
        country = COUNTRY_BY_CODE.get(code)
        if country:
            out[code] = country
    return out


def build_search_meta(dests: list[str], offers: list[dict[str, Any]]) -> dict[str, Any]:
    codes: set[str] = set(dests)
    for o in offers:
        for key in ("out_dest", "dest", "ret_dest"):
            c = o.get(key)
            if c:
                codes.add(str(c))
    return {"code_to_country": build_code_to_country(codes)}


def aggregate(offers: list[dict[str, Any]]) -> dict[str, Any]:
    if not offers:
        return {
            "by_price_bucket": [],
            "by_stay_days": [],
            "by_destination": [],
            "by_origin": [],
            "by_trip_type": [],
            "recommendations": {},
        }
    buckets: dict[str, int] = {}
    for o in offers:
        b = int(o["price"] // 100) * 100
        key = f"{b}-{b + 99}"
        buckets[key] = buckets.get(key, 0) + 1
    stay: dict[int, dict[str, Any]] = {}
    for o in offers:
        d = o["stay_days"]
        if d not in stay or o["price"] < stay[d]["min_price"]:
            stay[d] = {"days": d, "count": 0, "min_price": o["price"]}
        stay[d]["count"] += 1
    dest: dict[str, dict[str, Any]] = {}
    for o in offers:
        code = o.get("out_dest") or o.get("dest", "")
        name = o.get("out_dest_name") or DESTINATIONS.get(code, code)
        if code not in dest or o["price"] < dest[code]["min_price"]:
            dest[code] = {"code": code, "name": name, "count": 0, "min_price": o["price"]}
        dest[code]["count"] += 1
    origin: dict[str, dict[str, Any]] = {}
    for o in offers:
        code = o["origin"]
        if code not in origin or o["price"] < origin[code]["min_price"]:
            origin[code] = {
                "code": code,
                "name": o.get("origin_name", ORIGINS.get(code, code)),
                "count": 0,
                "min_price": o["price"],
            }
        origin[code]["count"] += 1
    rt = sum(1 for o in offers if o["trip_type"] == "round_trip")
    oj = sum(1 for o in offers if o["trip_type"] == "open_jaw")
    sorted_offers = sorted(offers, key=lambda x: x["price"])
    bookable = [o for o in sorted_offers if o.get("bookable")]
    longest = max(offers, key=lambda x: (x["stay_days"], -x["price"]))
    return {
        "by_price_bucket": [{"bucket": k, "count": v} for k, v in sorted(buckets.items())],
        "by_stay_days": sorted(stay.values(), key=lambda x: x["days"]),
        "by_destination": sorted(dest.values(), key=lambda x: x["min_price"]),
        "by_origin": sorted(origin.values(), key=lambda x: x["min_price"]),
        "by_trip_type": [
            {"type": "round_trip", "count": rt},
            {"type": "open_jaw", "count": oj},
        ],
        "recommendations": {
            "cheapest": sorted_offers[0]["id"],
            "longest_stay": longest["id"],
            "best_round_trip": bookable[0]["id"] if bookable else None,
        },
    }


def search(
    client: RollingGoClient,
    intent: SearchIntent,
    mode: SearchMode = "smart",
    on_progress: Callable[[int, int], None] | None = None,
    on_offer: Callable[[dict[str, Any]], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> SearchResult:
    import time

    t0 = time.time()
    origins = resolve_origins(intent)
    dests = resolve_destinations(intent, mode, client)
    pairs = valid_date_pairs(intent)
    out_days = sorted({out.isoformat() for out, _ in pairs})
    ret_days = sorted({ret.isoformat() for _, ret in pairs})

    rt_tasks: list[tuple[str, str, str, str]] = []
    if "round_trip" in intent.trip_modes:
        for origin in origins:
            for dest in dests:
                for out, ret in pairs:
                    rt_tasks.append((origin, dest, out.isoformat(), ret.isoformat()))

    ow_out_tasks: list[tuple[str, str, str]] = []
    ow_ret_tasks: list[tuple[str, str, str]] = []
    if "open_jaw" in intent.trip_modes:
        for origin in origins:
            for dest in dests:
                for d in out_days:
                    ow_out_tasks.append((origin, dest, d))
        for dest in dests:
            for origin in origins:
                for d in ret_days:
                    ow_ret_tasks.append((dest, origin, d))

    total = len(rt_tasks) + len(ow_out_tasks) + len(ow_ret_tasks)
    done = 0
    errors = 0
    offers: list[dict[str, Any]] = []
    ow_out_cache: dict[tuple[str, str, str], float] = {}
    ow_ret_cache: dict[tuple[str, str, str], float] = {}
    ow_out_detail: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    ow_ret_detail: dict[tuple[str, str, str], list[dict[str, str]]] = {}

    def emit_offer(offer: dict[str, Any]) -> None:
        if on_offer:
            on_offer(offer)

    def tick():
        nonlocal done
        done += 1
        if on_progress:
            on_progress(done, total)

    def run_rt(task: tuple[str, str, str, str]):
        origin, dest, out, ret = task
        return (
            "rt",
            task,
            client.search_flights(
                origin, dest, out, "ROUND_TRIP", ret, intent.adults, intent.children, intent.cabin
            ),
        )

    def run_ow(task: tuple[str, str, str], kind: str):
        frm, to, d = task
        return (
            kind,
            task,
            client.search_flights(frm, to, d, "ONE_WAY", None, intent.adults, intent.children, intent.cabin),
        )

    jobs: list[tuple[str, Any]] = [("rt", t) for t in rt_tasks]
    jobs += [("ow_out", t) for t in ow_out_tasks]
    jobs += [("ow_ret", t) for t in ow_ret_tasks]

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futures = {}
        for kind, task in jobs:
            if kind == "rt":
                futures[ex.submit(run_rt, task)] = ("rt", task)
            elif kind == "ow_out":
                futures[ex.submit(run_ow, task, "out")] = ("ow_out", task)
            else:
                futures[ex.submit(run_ow, task, "ret")] = ("ow_ret", task)

        for fut in as_completed(futures):
            if should_cancel and should_cancel():
                for pending in futures:
                    pending.cancel()
                break
            kind, task = futures[fut]
            try:
                result_kind, result_task, data = fut.result()
            except Exception:
                errors += 1
                tick()
                continue
            tick()
            if "error" in data:
                errors += 1
                continue
            best = _cheapest(data)
            if not best:
                continue
            price = best["totalAdultPrice"]
            if intent.max_price is not None and price > intent.max_price:
                if result_kind == "rt":
                    continue
            if result_kind == "rt":
                origin, dest, out, ret = result_task
                sd = stay_days(date.fromisoformat(out), date.fromisoformat(ret))
                if intent.max_price is not None and price > intent.max_price:
                    continue
                offer = {
                        "id": _offer_id(),
                        "trip_type": "round_trip",
                        "price": price,
                        "currency": best.get("currency", "CNY"),
                        "origin": origin,
                        "origin_name": ORIGINS.get(origin, origin),
                        "dest": dest,
                        "dest_name": DESTINATIONS.get(dest, dest),
                        "out_dest": dest,
                        "out_dest_name": DESTINATIONS.get(dest, dest),
                        "ret_dest": dest,
                        "ret_dest_name": DESTINATIONS.get(dest, dest),
                        "route": f"{ORIGINS.get(origin, origin)}↔{DESTINATIONS.get(dest, dest)}",
                        "ret_origin": origin,
                        "ret_origin_name": ORIGINS.get(origin, origin),
                        "out_date": out,
                        "ret_date": ret,
                        "stay_days": sd,
                        "bookable": True,
                        "segments_out": seg_list(best.get("fromSegments", [])),
                        "segments_ret": seg_list(best.get("retSegments", [])),
                        "summary_out": fmt_seg(best.get("fromSegments", [])),
                        "summary_ret": fmt_seg(best.get("retSegments", [])),
                        "detail": "去: "
                        + fmt_seg(best.get("fromSegments", []))
                        + " | 回: "
                        + fmt_seg(best.get("retSegments", [])),
                        "price_out": price,
                        "price_ret": None,
                    }
                offers.append(offer)
                emit_offer(offer)
            elif result_kind == "out":
                ow_out_cache[result_task] = price
                ow_out_detail[result_task] = seg_list(best.get("fromSegments", []))
            else:
                ow_ret_cache[result_task] = price
                ow_ret_detail[result_task] = seg_list(best.get("fromSegments", []))

    if "open_jaw" in intent.trip_modes and not (should_cancel and should_cancel()):
        for origin in origins:
            if should_cancel and should_cancel():
                break
            for out_dest in dests:
                for ret_dest in dests:
                    for ret_origin in origins:
                        for out_d in out_days:
                            for ret_d in ret_days:
                                if not stay_in_bounds(
                                    intent,
                                    date.fromisoformat(out_d),
                                    date.fromisoformat(ret_d),
                                ):
                                    continue
                                out_p = ow_out_cache.get((origin, out_dest, out_d))
                                ret_p = ow_ret_cache.get((ret_dest, ret_origin, ret_d))
                                if out_p is None or ret_p is None:
                                    continue
                                total_p = out_p + ret_p
                                if intent.max_price is not None and total_p > intent.max_price:
                                    continue
                                sd = stay_days(date.fromisoformat(out_d), date.fromisoformat(ret_d))
                                out_detail = ow_out_detail.get((origin, out_dest, out_d), [])
                                ret_detail = ow_ret_detail.get((ret_dest, ret_origin, ret_d), [])
                                sum_out = " | ".join(
                                    f"{s['flight']} {s['from']}→{s['to']} {s['dep']}" for s in out_detail
                                )
                                sum_ret = " | ".join(
                                    f"{s['flight']} {s['from']}→{s['to']} {s['dep']}" for s in ret_detail
                                )
                                offer = {
                                        "id": _offer_id(),
                                        "trip_type": "open_jaw",
                                        "price": total_p,
                                        "currency": "CNY",
                                        "origin": origin,
                                        "origin_name": ORIGINS.get(origin, origin),
                                        "out_dest": out_dest,
                                        "out_dest_name": DESTINATIONS.get(out_dest, out_dest),
                                        "ret_dest": ret_dest,
                                        "ret_dest_name": DESTINATIONS.get(ret_dest, ret_dest),
                                        "ret_origin": ret_origin,
                                        "ret_origin_name": ORIGINS.get(ret_origin, ret_origin),
                                        "route": f"{ORIGINS.get(origin, origin)}→{DESTINATIONS.get(out_dest, out_dest)} / {DESTINATIONS.get(ret_dest, ret_dest)}→{ORIGINS.get(ret_origin, ret_origin)}",
                                        "out_date": out_d,
                                        "ret_date": ret_d,
                                        "stay_days": sd,
                                        "bookable": False,
                                        "segments_out": out_detail,
                                        "segments_ret": ret_detail,
                                        "summary_out": sum_out,
                                        "summary_ret": sum_ret,
                                        "detail": f"去 ¥{out_p}: {sum_out} | 回 ¥{ret_p}: {sum_ret}",
                                        "price_out": out_p,
                                        "price_ret": ret_p,
                                    }
                                offers.append(offer)
                                emit_offer(offer)

    offers.sort(key=lambda x: x["price"])
    duration_ms = int((time.time() - t0) * 1000)
    stats = SearchStats(
        total_queries=total,
        errors=errors,
        rt_count=sum(1 for o in offers if o["trip_type"] == "round_trip"),
        oj_count=sum(1 for o in offers if o["trip_type"] == "open_jaw"),
        duration_ms=duration_ms,
    )
    meta = build_search_meta(dests, offers)
    return SearchResult(
        offers=offers,
        aggregations=aggregate(offers),
        stats=stats,
        meta=meta,
        ow_cache_built=True,
    )


def resolve_city_codes(client: RollingGoClient, names: list[str]) -> list[str]:
    codes: list[str] = []
    for name in names:
        if name in DESTINATIONS:
            codes.append(name)
            continue
        for code, label in DESTINATIONS.items():
            if name == label:
                codes.append(code)
                break
        else:
            data = client.search_airports(name)
            for item in data.get("airPortInformationList") or []:
                cc = item.get("cityCode")
                if cc and cc not in codes:
                    codes.append(cc)
    return codes
