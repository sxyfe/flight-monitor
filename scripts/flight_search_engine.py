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
class MatrixSearchIntent:
    origins: list[str]
    destinations: list[str]
    out_date_start: str
    out_date_end: str
    ret_date_start: str
    ret_date_end: str
    min_stay_days: int = 1
    max_stay_days: int | None = None
    origin_labels: dict[str, str] = field(default_factory=dict)
    dest_labels: dict[str, str] = field(default_factory=dict)
    cabin: str = "ECONOMY"
    adults: int = 1
    children: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MatrixSearchIntent:
        out_date = str(data.get("out_date") or "").strip()
        ret_date = str(data.get("ret_date") or "").strip()
        out_date_start = str(data.get("out_date_start") or out_date or "")
        ret_date_end = str(data.get("ret_date_end") or ret_date or "")
        out_date_end = str(data.get("out_date_end") or "").strip()
        ret_date_start = str(data.get("ret_date_start") or "").strip()
        # 双日期 UI：去程日起 ~ 返程日止，两轴共用同一窗口并穷举组合
        if out_date and ret_date:
            if not out_date_end:
                out_date_end = ret_date
            if not ret_date_start:
                ret_date_start = out_date
        else:
            if not out_date_end:
                out_date_end = out_date_start
            if not ret_date_start:
                ret_date_start = ret_date_end
        return cls(
            origins=list(data.get("origins") or []),
            destinations=list(data.get("destinations") or []),
            out_date_start=out_date_start,
            out_date_end=out_date_end,
            ret_date_start=ret_date_start,
            ret_date_end=ret_date_end,
            min_stay_days=int(data.get("min_stay_days") or 1),
            max_stay_days=(
                int(data["max_stay_days"])
                if data.get("max_stay_days") not in (None, "")
                else None
            ),
            origin_labels=dict(data.get("origin_labels") or {}),
            dest_labels=dict(data.get("dest_labels") or {}),
            cabin=str(data.get("cabin") or "ECONOMY"),
            adults=int(data.get("adults") or 1),
            children=int(data.get("children") or 0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "origins": self.origins,
            "destinations": self.destinations,
            "out_date_start": self.out_date_start,
            "out_date_end": self.out_date_end,
            "ret_date_start": self.ret_date_start,
            "ret_date_end": self.ret_date_end,
            "min_stay_days": self.min_stay_days,
            "max_stay_days": self.max_stay_days,
            "origin_labels": self.origin_labels,
            "dest_labels": self.dest_labels,
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
    api_failures: int = 0
    api_failure_message: str = ""
    pricing_service_abnormal: bool = False
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
                "Accept": "application/json",
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
        """RollingGo MCP searchAirports：POST /api/mcp/airportsearch {"keyword": "..."}"""
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


def normalize_rollinggo_airport_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in data.get("airPortInformationList") or []:
        items.append(
            {
                "cityCode": item.get("cityCode"),
                "cityName": item.get("cityName"),
                "airportCode": item.get("airportCode"),
                "airportName": item.get("airportName"),
                "countryCode": item.get("countryCode"),
                "countryName": item.get("countryName"),
            }
        )
    return items


def is_rollinggo_airport_auth_error(data: dict[str, Any]) -> bool:
    err = str(data.get("error") or "")
    if "401" in err or "403" in err:
        return True
    if data.get("success") is False:
        msg = str(data.get("message") or "")
        return any(x in msg for x in ("401", "403", "认证", "授权", "token", "Token", "Unauthorized"))
    return False


def search_airports_for_picker(
    client: RollingGoClient | None,
    keyword: str,
    *,
    alt_client: RollingGoClient | None = None,
) -> dict[str, Any]:
    """优先 RollingGo airportsearch（MCP keyword），失败则公开 API + OurAirports 回退。"""
    from airport_local_search import search_fallback_airports

    kw = keyword.strip()
    if not kw:
        return {"items": [], "source": "none"}

    last_data: dict[str, Any] = {}
    auth_failed = False

    for attempt_client in (client, alt_client):
        if not attempt_client:
            continue
        data = attempt_client.search_airports(kw)
        last_data = data
        if "error" in data:
            auth_failed = auth_failed or is_rollinggo_airport_auth_error(data)
            continue
        if data.get("success") is False:
            auth_failed = auth_failed or is_rollinggo_airport_auth_error(data)
            continue
        items = normalize_rollinggo_airport_items(data)
        if items:
            return {"items": items, "source": "rollinggo"}

    fallback_items, fb_source = search_fallback_airports(kw)
    if fallback_items:
        out: dict[str, Any] = {"items": fallback_items, "source": fb_source}
        if auth_failed:
            out["warning"] = (
                "RollingGo 不可用；中文城市名需配置有效 API Key，"
                "当前仅支持英文/机场三字码（OurAirports / rotatepilot）"
            )
        elif client or alt_client:
            out["warning"] = "RollingGo 未返回结果，已使用免费公开数据源回退"
        return out

    err = last_data.get("error") or last_data.get("message") or "机场搜索失败"
    if auth_failed and not (client or alt_client):
        err = "RollingGo API Key 未配置，请在设置页填写（中文搜索需有效 Key）"
    elif auth_failed:
        err = (
            "RollingGo 认证失败；中文城市名需有效 Key，"
            "或改用英文/机场三字码（如 Beijing、PEK）"
        )
    return {"items": [], "source": "none", "error": str(err), "auth_failed": auth_failed}


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


def _resolve_matrix_codes(codes: list[str]) -> list[str]:
    return list(dict.fromkeys(c.upper().strip() for c in codes if c and len(c.strip()) == 3))


def _matrix_label(code: str, labels: dict[str, str], fallback: dict[str, str]) -> str:
    return labels.get(code) or fallback.get(code, code)


def matrix_stay_in_bounds(intent: MatrixSearchIntent, out: date, ret: date) -> bool:
    if ret <= out:
        return False
    sd = stay_days(out, ret)
    if sd < intent.min_stay_days:
        return False
    if intent.max_stay_days is not None and sd > intent.max_stay_days:
        return False
    return True


def matrix_valid_date_pairs(intent: MatrixSearchIntent) -> list[tuple[date, date]]:
    out_start = date.fromisoformat(intent.out_date_start)
    out_end = date.fromisoformat(intent.out_date_end)
    ret_start = date.fromisoformat(intent.ret_date_start)
    ret_end = date.fromisoformat(intent.ret_date_end)
    pairs: list[tuple[date, date]] = []
    for out in date_range(out_start, out_end):
        for ret in date_range(ret_start, ret_end):
            if matrix_stay_in_bounds(intent, out, ret):
                pairs.append((out, ret))
    return pairs


def validate_matrix_intent(intent: MatrixSearchIntent) -> ValidationResult:
    result = ValidationResult(valid=True)
    origins = _resolve_matrix_codes(intent.origins)
    dests = _resolve_matrix_codes(intent.destinations)
    if not origins:
        result.errors.append("请至少选择一个出发地")
    if not dests:
        result.errors.append("请至少选择一个目的地")
    today = date.today()
    window_mode = (
        intent.out_date_start == intent.ret_date_start
        and intent.out_date_end == intent.ret_date_end
    )

    def parse_axis(label: str, start_s: str, end_s: str) -> tuple[date | None, date | None]:
        if not start_s or not end_s:
            result.errors.append(f"请填写{label}日期")
            return None, None
        try:
            start = date.fromisoformat(start_s)
            end = date.fromisoformat(end_s)
        except ValueError:
            result.errors.append(f"{label}日期格式无效，请使用 YYYY-MM-DD")
            return None, None
        if start > end:
            result.errors.append(f"{label}开始日期不能晚于结束日期")
        if start < today:
            result.errors.append(f"{label}日期不能早于今天")
        if end < today:
            result.errors.append(f"{label}日期不能早于今天")
        return start, end

    if window_mode:
        ws, we = intent.out_date_start, intent.ret_date_end
        if not ws:
            result.errors.append("请填写去程日期")
        if not we:
            result.errors.append("请填写返程日期")
        if ws and we:
            try:
                start = date.fromisoformat(ws)
                end = date.fromisoformat(we)
            except ValueError:
                result.errors.append("日期格式无效，请使用 YYYY-MM-DD")
            else:
                if start > end:
                    result.errors.append("去程日期不能晚于返程日期")
                if start < today:
                    result.errors.append("去程日期不能早于今天")
                if end < today:
                    result.errors.append("返程日期不能早于今天")
    else:
        parse_axis("去程", intent.out_date_start, intent.out_date_end)
        parse_axis("返程", intent.ret_date_start, intent.ret_date_end)

    if (
        intent.max_stay_days is not None
        and intent.min_stay_days > intent.max_stay_days
    ):
        result.errors.append(
            f"最少停留 {intent.min_stay_days} 天不能大于最多停留 {intent.max_stay_days} 天"
        )

    if not result.errors:
        pairs = matrix_valid_date_pairs(intent)
        if not pairs:
            bounds = [f"最少停留 {intent.min_stay_days} 天"]
            if intent.max_stay_days is not None:
                bounds.append(f"最多停留 {intent.max_stay_days} 天")
            if window_mode:
                result.errors.append(
                    f"在 {intent.out_date_start}~{intent.ret_date_end} 内无有效去程×返程组合"
                    f"（需返程晚于去程且满足{'、'.join(bounds)}）"
                )
            else:
                result.errors.append(
                    f"去程 {intent.out_date_start}~{intent.out_date_end} 与返程 "
                    f"{intent.ret_date_start}~{intent.ret_date_end} 内无有效日期组合（需返程晚于去程且满足{'、'.join(bounds)}）"
                )

    est = estimate_matrix_query_count(intent) if not result.errors else 0
    result.estimated_queries_smart = est
    result.estimated_queries_exhaustive = est
    if est > HIGH_COST_THRESHOLD:
        result.warnings.append(f"矩阵搜索预计 {est} 次 API 查询，耗时可能较长")

    if result.errors:
        result.valid = False
    return result


def estimate_matrix_query_count(intent: MatrixSearchIntent) -> int:
    origins = _resolve_matrix_codes(intent.origins)
    dests = _resolve_matrix_codes(intent.destinations)
    pairs = matrix_valid_date_pairs(intent)
    if not origins or not dests or not pairs:
        return 0
    out_days = {out.isoformat() for out, _ in pairs}
    ret_days = {ret.isoformat() for _, ret in pairs}
    route_count = len(origins) * len(dests)
    rt_count = route_count * len(pairs)
    ow_out_count = route_count * len(out_days)
    ow_ret_count = route_count * len(ret_days)
    return rt_count + ow_out_count + ow_ret_count


def build_matrix_meta(intent: MatrixSearchIntent, offers: list[dict[str, Any]]) -> dict[str, Any]:
    origins = _resolve_matrix_codes(intent.origins)
    dests = _resolve_matrix_codes(intent.destinations)
    pairs = matrix_valid_date_pairs(intent)
    out_days = sorted({out.isoformat() for out, _ in pairs})
    ret_days = sorted({ret.isoformat() for _, ret in pairs})
    routes = []
    for origin in origins:
        for dest in dests:
            routes.append(
                {
                    "origin": origin,
                    "dest": dest,
                    "origin_name": _matrix_label(origin, intent.origin_labels, ORIGINS),
                    "dest_name": _matrix_label(dest, intent.dest_labels, DESTINATIONS),
                }
            )
    return {
        "search_type": "matrix",
        "route_count": len(routes),
        "routes": routes,
        "out_days": out_days,
        "ret_days": ret_days,
        "out_date_start": intent.out_date_start,
        "out_date_end": intent.out_date_end,
        "ret_date_start": intent.ret_date_start,
        "ret_date_end": intent.ret_date_end,
        "min_stay_days": intent.min_stay_days,
        "max_stay_days": intent.max_stay_days,
        "code_to_country": build_code_to_country(dests),
    }


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


def flight_response_failed(data: dict[str, Any]) -> bool:
    """RollingGo 查价 API 业务失败（HTTP 200 但 success=false）。"""
    if "error" in data:
        return False
    return data.get("success") is False


def flight_response_message(data: dict[str, Any]) -> str:
    if "error" in data:
        return str(data["error"])
    msg = data.get("message")
    if msg:
        return str(msg)
    return "查价服务异常"


def finalize_pricing_status(stats: SearchStats, offers_count: int, completed: int) -> None:
    responded = max(completed - stats.errors, 0)
    stats.pricing_service_abnormal = (
        offers_count == 0
        and stats.api_failures > 0
        and stats.api_failures >= responded
    )


def probe_flight_pricing(client: RollingGoClient) -> tuple[bool, str]:
    """连通性探针：机场搜索通过后，再测一条往返查价。"""
    out = (date.today() + timedelta(days=30)).isoformat()
    ret = (date.today() + timedelta(days=37)).isoformat()
    data = client.search_flights("BJS", "BKK", out, "ROUND_TRIP", ret)
    if "error" in data:
        return False, str(data["error"])
    if flight_response_failed(data):
        return False, flight_response_message(data)
    return True, "RollingGo 查价正常"


def _cheapest(data: dict[str, Any]) -> dict[str, Any] | None:
    flights = data.get("flightInformationList") or []
    if not flights or "error" in data or flight_response_failed(data):
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
    api_failures = 0
    api_failure_message = ""
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
            if flight_response_failed(data):
                api_failures += 1
                if not api_failure_message:
                    api_failure_message = flight_response_message(data)
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
        api_failures=api_failures,
        api_failure_message=api_failure_message,
        rt_count=sum(1 for o in offers if o["trip_type"] == "round_trip"),
        oj_count=sum(1 for o in offers if o["trip_type"] == "open_jaw"),
        duration_ms=duration_ms,
    )
    finalize_pricing_status(stats, len(offers), done)
    meta = build_search_meta(dests, offers)
    if api_failures:
        meta["api_failures"] = api_failures
        meta["api_failure_message"] = api_failure_message
    if stats.pricing_service_abnormal:
        meta["pricing_service_abnormal"] = True
        meta["pricing_service_message"] = api_failure_message or "查价服务异常"
    return SearchResult(
        offers=offers,
        aggregations=aggregate(offers),
        stats=stats,
        meta=meta,
        ow_cache_built=True,
    )


def _build_matrix_offer(
    intent: MatrixSearchIntent,
    origin: str,
    dest: str,
    out: str,
    ret: str,
    rt_best: dict[str, Any] | None,
    ow_out_price: float | None,
    ow_ret_price: float | None,
    ow_out_detail: list[dict[str, str]] | None,
    ow_ret_detail: list[dict[str, str]] | None,
) -> dict[str, Any] | None:
    """取往返联票与去程+返程单程最低价，构建矩阵单元报价。"""
    candidates: list[tuple[str, float, dict[str, Any] | None]] = []
    if rt_best is not None:
        candidates.append(("rt", rt_best["totalAdultPrice"], rt_best))
    if ow_out_price is not None and ow_ret_price is not None:
        candidates.append(("ow", ow_out_price + ow_ret_price, None))
    if not candidates:
        return None

    kind, price, rt_data = min(candidates, key=lambda x: x[1])
    sd = stay_days(date.fromisoformat(out), date.fromisoformat(ret))
    origin_name = _matrix_label(origin, intent.origin_labels, ORIGINS)
    dest_name = _matrix_label(dest, intent.dest_labels, DESTINATIONS)
    out_detail = ow_out_detail or []
    ret_detail = ow_ret_detail or []
    sum_out = " | ".join(f"{s['flight']} {s['from']}→{s['to']} {s['dep']}" for s in out_detail)
    sum_ret = " | ".join(f"{s['flight']} {s['from']}→{s['to']} {s['dep']}" for s in ret_detail)

    if kind == "rt" and rt_data is not None:
        return {
            "id": _offer_id(),
            "trip_type": "round_trip",
            "price": price,
            "currency": rt_data.get("currency", "CNY"),
            "origin": origin,
            "origin_name": origin_name,
            "dest": dest,
            "dest_name": dest_name,
            "out_dest": dest,
            "out_dest_name": dest_name,
            "ret_dest": dest,
            "ret_dest_name": dest_name,
            "route": f"{origin_name} ⇄ {dest_name}",
            "ret_origin": origin,
            "ret_origin_name": origin_name,
            "out_date": out,
            "ret_date": ret,
            "stay_days": sd,
            "bookable": True,
            "segments_out": seg_list(rt_data.get("fromSegments", [])),
            "segments_ret": seg_list(rt_data.get("retSegments", [])),
            "summary_out": fmt_seg(rt_data.get("fromSegments", [])),
            "summary_ret": fmt_seg(rt_data.get("retSegments", [])),
            "detail": "去: "
            + fmt_seg(rt_data.get("fromSegments", []))
            + " | 回: "
            + fmt_seg(rt_data.get("retSegments", [])),
            "price_out": price,
            "price_ret": None,
        }

    return {
        "id": _offer_id(),
        "trip_type": "round_trip",
        "price": price,
        "currency": "CNY",
        "origin": origin,
        "origin_name": origin_name,
        "dest": dest,
        "dest_name": dest_name,
        "out_dest": dest,
        "out_dest_name": dest_name,
        "ret_dest": dest,
        "ret_dest_name": dest_name,
        "route": f"{origin_name} ⇄ {dest_name}",
        "ret_origin": origin,
        "ret_origin_name": origin_name,
        "out_date": out,
        "ret_date": ret,
        "stay_days": sd,
        "bookable": False,
        "segments_out": out_detail,
        "segments_ret": ret_detail,
        "summary_out": sum_out,
        "summary_ret": sum_ret,
        "detail": f"去 ¥{ow_out_price}: {sum_out} | 回 ¥{ow_ret_price}: {sum_ret}",
        "price_out": ow_out_price,
        "price_ret": ow_ret_price,
    }


def _matrix_process_response(
    result_kind: str,
    result_task: Any,
    data: dict[str, Any],
    *,
    rt_cache: dict[tuple[str, str, str, str], dict[str, Any] | None],
    ow_out_cache: dict[tuple[str, str, str], float],
    ow_ret_cache: dict[tuple[str, str, str], float],
    ow_out_detail: dict[tuple[str, str, str], list[dict[str, str]]],
    ow_ret_detail: dict[tuple[str, str, str], list[dict[str, str]]],
) -> tuple[bool, str]:
    """处理单次查价响应，写入缓存。返回 (is_api_failure, failure_message)。"""
    if "error" in data:
        if result_kind == "rt":
            rt_cache[result_task] = None
        return False, ""
    if flight_response_failed(data):
        if result_kind == "rt":
            rt_cache[result_task] = None
        return True, flight_response_message(data)
    best = _cheapest(data)
    if result_kind == "rt":
        rt_cache[result_task] = best
    elif result_kind == "out" and best:
        ow_out_cache[result_task] = best["totalAdultPrice"]
        ow_out_detail[result_task] = seg_list(best.get("fromSegments", []))
    elif result_kind == "ret" and best:
        ow_ret_cache[result_task] = best["totalAdultPrice"]
        ow_ret_detail[result_task] = seg_list(best.get("fromSegments", []))
    return False, ""


def _dedupe_matrix_offers(offers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for o in offers:
        key = (o["origin"], o["dest"], o["out_date"], o["ret_date"])
        if key not in best or o["price"] < best[key]["price"]:
            best[key] = o
    return sorted(best.values(), key=lambda x: x["price"])


def search_matrix(
    client: RollingGoClient,
    intent: MatrixSearchIntent,
    on_progress: Callable[[int, int], None] | None = None,
    on_offer: Callable[[dict[str, Any]], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> SearchResult:
    import time

    t0 = time.time()
    origins = _resolve_matrix_codes(intent.origins)
    dests = _resolve_matrix_codes(intent.destinations)
    pairs = matrix_valid_date_pairs(intent)
    out_days = sorted({out.isoformat() for out, _ in pairs})
    ret_days = sorted({ret.isoformat() for _, ret in pairs})

    rt_tasks: list[tuple[str, str, str, str]] = []
    ow_out_tasks: list[tuple[str, str, str]] = []
    ow_ret_tasks: list[tuple[str, str, str]] = []
    for origin in origins:
        for dest in dests:
            for out, ret in pairs:
                rt_tasks.append((origin, dest, out.isoformat(), ret.isoformat()))
            for out_d in out_days:
                ow_out_tasks.append((origin, dest, out_d))
            for ret_d in ret_days:
                ow_ret_tasks.append((dest, origin, ret_d))

    total = len(rt_tasks) + len(ow_out_tasks) + len(ow_ret_tasks)
    done = 0
    errors = 0
    api_failures = 0
    api_failure_message = ""
    offers: list[dict[str, Any]] = []
    emitted_best: dict[tuple[str, str, str, str], float] = {}
    rt_cache: dict[tuple[str, str, str, str], dict[str, Any] | None] = {}
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

    def maybe_emit(task: tuple[str, str, str, str], offer: dict[str, Any] | None) -> None:
        if not offer:
            return
        prev = emitted_best.get(task)
        if prev is not None and offer["price"] >= prev:
            return
        offers.append(offer)
        emitted_best[task] = offer["price"]
        emit_offer(offer)

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

    def handle_response(result_kind: str, result_task: Any, data: dict[str, Any]) -> None:
        nonlocal api_failures, api_failure_message, errors
        if "error" in data:
            errors += 1
        failed, msg = _matrix_process_response(
            result_kind,
            result_task,
            data,
            rt_cache=rt_cache,
            ow_out_cache=ow_out_cache,
            ow_ret_cache=ow_ret_cache,
            ow_out_detail=ow_out_detail,
            ow_ret_detail=ow_ret_detail,
        )
        if failed:
            api_failures += 1
            if msg and not api_failure_message:
                api_failure_message = msg

    # 阶段 1：往返联票（优先，命中即推送，避免长时间 0 命中）
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futures = {ex.submit(run_rt, t): t for t in rt_tasks}
        for fut in as_completed(futures):
            if should_cancel and should_cancel():
                for pending in futures:
                    pending.cancel()
                break
            task = futures[fut]
            try:
                result_kind, result_task, data = fut.result()
            except Exception:
                errors += 1
                rt_cache[task] = None
                tick()
                continue
            tick()
            handle_response(result_kind, result_task, data)
            rt_best = rt_cache.get(task)
            if rt_best:
                origin, dest, out, ret = task
                maybe_emit(
                    task,
                    _build_matrix_offer(
                        intent, origin, dest, out, ret, rt_best, None, None, None, None
                    ),
                )

    cancelled = bool(should_cancel and should_cancel())

    # 阶段 2：单程补查（联票未命中或需对比最低价时才真正用到）
    if not cancelled:
        ow_jobs: list[tuple[str, tuple[str, str, str]]] = [
            ("out", t) for t in ow_out_tasks
        ] + [("ret", t) for t in ow_ret_tasks]
        with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
            futures = {
                ex.submit(run_ow, task, kind): (kind, task) for kind, task in ow_jobs
            }
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
                handle_response(result_kind, result_task, data)

    # 阶段 3：联票 vs 单程相加取最低，补全空格子
    for origin, dest, out, ret in rt_tasks:
        task = (origin, dest, out, ret)
        offer = _build_matrix_offer(
            intent,
            origin,
            dest,
            out,
            ret,
            rt_cache.get(task),
            ow_out_cache.get((origin, dest, out)),
            ow_ret_cache.get((dest, origin, ret)),
            ow_out_detail.get((origin, dest, out)),
            ow_ret_detail.get((dest, origin, ret)),
        )
        maybe_emit(task, offer)

    offers = _dedupe_matrix_offers(offers)
    duration_ms = int((time.time() - t0) * 1000)
    rt_offer_count = sum(1 for o in offers if o.get("bookable"))
    ow_offer_count = len(offers) - rt_offer_count
    stats = SearchStats(
        total_queries=total,
        errors=errors,
        api_failures=api_failures,
        api_failure_message=api_failure_message,
        rt_count=rt_offer_count,
        oj_count=ow_offer_count,
        duration_ms=duration_ms,
    )
    finalize_pricing_status(stats, len(offers), done)
    meta = build_matrix_meta(intent, offers)
    if api_failures:
        meta["api_failures"] = api_failures
        meta["api_failure_message"] = api_failure_message
    if stats.pricing_service_abnormal:
        meta["pricing_service_abnormal"] = True
        meta["pricing_service_message"] = api_failure_message or "查价服务异常"
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
