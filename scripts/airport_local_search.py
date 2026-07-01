"""机场搜索回退：OurAirports 本地索引 + 公开免费 API（无内置中文映射）。"""
from __future__ import annotations

import csv
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).resolve().parent / "data"
_INDEX_PATH = _DATA_DIR / "airport_search_index.json"
_INDEX_VERSION = 3
OURAIRPORTS_CSV = "https://davidmegginson.github.io/ourairports-data/airports.csv"
OURAIRPORTS_COUNTRIES_CSV = "https://davidmegginson.github.io/ourairports-data/countries.csv"
_USER_AGENT = "flight-monitor-nl-search/1.0"

ALLOWED_TYPES = frozenset({"large_airport", "medium_airport"})

# 机场 IATA → RollingGo 查价 cityCode（与 sync_country_airports 一致，非中文映射）
AIRPORT_IATA_TO_CITY_CODE: dict[str, str] = {
    "DMK": "BKK",
    "CGK": "JKT",
    "HLP": "JKT",
    "SZB": "KUL",
    "XSP": "SIN",
    "NRT": "TYO",
    "HND": "TYO",
    "KIX": "OSA",
    "ITM": "OSA",
    "UKB": "OSA",
    "CTS": "SPK",
    "OKD": "SPK",
}

_index_cache: list[dict[str, Any]] | None = None
_country_name_by_iso: dict[str, str] | None = None


def _load_country_names() -> dict[str, str]:
    global _country_name_by_iso
    if _country_name_by_iso is not None:
        return _country_name_by_iso
    try:
        with urllib.request.urlopen(OURAIRPORTS_COUNTRIES_CSV, timeout=60) as resp:
            reader = csv.DictReader(resp.read().decode("utf-8").splitlines())
            _country_name_by_iso = {
                (row.get("code") or "").upper(): (row.get("name") or "").strip()
                for row in reader
                if (row.get("code") or "").strip()
            }
    except (urllib.error.URLError, TimeoutError, OSError):
        _country_name_by_iso = {}
    return _country_name_by_iso


def _city_code(iata: str) -> str:
    code = (iata or "").strip().upper()
    if not code:
        return ""
    return AIRPORT_IATA_TO_CITY_CODE.get(code, code)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _picker_item(
    city_code: str,
    city_name: str,
    airport_code: str,
    airport_name: str,
    extra_search: str = "",
    *,
    country_code: str = "",
    country_name: str = "",
) -> dict[str, Any]:
    cc = city_code.upper()
    ac = (airport_code or city_code).upper()
    iso = (country_code or "").upper()
    cname = (country_name or "").strip()
    parts = [cc, ac, city_name, airport_name, extra_search, iso, cname]
    item: dict[str, Any] = {
        "cityCode": cc,
        "cityName": city_name or cc,
        "airportCode": ac,
        "airportName": airport_name or city_name or cc,
        "searchText": _norm(" ".join(p for p in parts if p)),
    }
    if iso:
        item["countryCode"] = iso
    if cname:
        item["countryName"] = cname
    return item


def build_index_from_ourairports(csv_text: str) -> list[dict[str, Any]]:
    """从 OurAirports CSV 构建 city 级索引（scheduled large/medium）。"""
    by_city: dict[str, dict[str, Any]] = {}
    reader = csv.DictReader(csv_text.splitlines())
    for row in reader:
        if (row.get("type") or "") not in ALLOWED_TYPES:
            continue
        if (row.get("scheduled_service") or "").lower() != "yes":
            continue
        iata = (row.get("iata_code") or "").strip().upper()
        if len(iata) != 3:
            continue
        city = _city_code(iata)
        municipality = (row.get("municipality") or "").strip()
        name = (row.get("name") or "").strip()
        iso = (row.get("iso_country") or "").strip()
        label = municipality or name.split(" ")[0] or city
        score = 100 if row.get("type") == "large_airport" else 50
        prev = by_city.get(city)
        if not prev or score > prev["_score"]:
            by_city[city] = {
                "_score": score,
                "cityCode": city,
                "cityName": label,
                "airportCode": iata,
                "airportName": name or label,
                "iso": iso,
            }
    country_names = _load_country_names()
    items: list[dict[str, Any]] = []
    for row in by_city.values():
        iso = (row.get("iso") or "").upper()
        items.append(
            _picker_item(
                row["cityCode"],
                row["cityName"],
                row["airportCode"],
                row["airportName"],
                row.get("iso", ""),
                country_code=iso,
                country_name=country_names.get(iso, ""),
            )
        )
    return items


def ensure_index_file() -> Path:
    if _INDEX_PATH.exists():
        try:
            raw = json.loads(_INDEX_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and raw.get("version") == _INDEX_VERSION:
                return _INDEX_PATH
        except (json.JSONDecodeError, OSError):
            pass
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(OURAIRPORTS_CSV, timeout=120) as resp:
        csv_text = resp.read().decode("utf-8")
    items = build_index_from_ourairports(csv_text)
    _INDEX_PATH.write_text(
        json.dumps({"version": _INDEX_VERSION, "items": items}, ensure_ascii=False, indent=0),
        encoding="utf-8",
    )
    return _INDEX_PATH


def load_index() -> list[dict[str, Any]]:
    global _index_cache
    if _index_cache is not None:
        return _index_cache
    ensure_index_file()
    raw = json.loads(_INDEX_PATH.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "items" in raw:
        _index_cache = list(raw["items"])
    else:
        _index_cache = list(raw)
    return _index_cache


def _to_picker_result(entry: dict[str, Any]) -> dict[str, Any]:
    out = {
        k: entry[k]
        for k in ("cityCode", "cityName", "airportCode", "airportName")
        if k in entry
    }
    for k in ("countryCode", "countryName"):
        if entry.get(k):
            out[k] = entry[k]
    return out


def search_local_airports(keyword: str, *, limit: int = 20) -> list[dict[str, Any]]:
    """OurAirports 本地索引：英文城市/机场名、IATA 子串匹配。"""
    kw = keyword.strip()
    if not kw:
        return []
    index = load_index()
    kw_norm = _norm(kw)
    kw_upper = kw.strip().upper()

    matched: list[tuple[int, dict[str, Any]]] = []
    for e in index:
        score = 0
        cc = e["cityCode"]
        ac = e.get("airportCode") or cc
        if kw_upper == cc or kw_upper == ac:
            score = 100
        elif cc.startswith(kw_upper) or ac.startswith(kw_upper):
            score = 80
        elif kw_norm in (e.get("searchText") or ""):
            score = 60
        elif any(kw_norm in _norm(part) for part in (e.get("cityName"), e.get("airportName"))):
            score = 40
        if score:
            matched.append((score, e))

    matched.sort(key=lambda x: (-x[0], x[1]["cityCode"]))
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for _, e in matched:
        key = f"{e['cityCode']}|{e.get('airportCode')}"
        if key in seen:
            continue
        seen.add(key)
        out.append(_to_picker_result(e))
        if len(out) >= limit:
            break
    return out


def _http_json(url: str, *, timeout: float = 12) -> dict[str, Any] | None:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": _USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None


def search_rotatepilot_iata(code: str) -> dict[str, Any] | None:
    """rotatepilot.com 免费 API：按 IATA/ICAO 精确查单条。"""
    c = code.strip().upper()
    if len(c) != 3 or not c.isalpha():
        return None
    data = _http_json(f"https://rotatepilot.com/api/v1/airport/{c}")
    if not data or not data.get("iata"):
        return None
    iata = str(data["iata"]).upper()
    city = str(data.get("city") or iata).strip()
    name = str(data.get("name") or city).strip()
    country = str(data.get("country") or "").strip()
    return _to_picker_result(
        _picker_item(_city_code(iata), city, iata, name, country_name=country)
    )


def search_airportsapi_iata(code: str) -> dict[str, Any] | None:
    """airportsapi.com 免费 API：按 IATA 查单条（需 User-Agent）。"""
    c = code.strip().upper()
    if len(c) != 3 or not c.isalpha():
        return None
    data = _http_json(f"https://airportsapi.com/api/airports/{c}")
    if not data or not data.get("data"):
        return None
    attrs = data["data"].get("attributes") or {}
    iata = (attrs.get("iata_code") or c).upper()
    if len(iata) != 3:
        return None
    name = str(attrs.get("name") or iata).strip()
    city = name.split(" Airport")[0].split(" International")[0].strip() or iata
    return _to_picker_result(_picker_item(_city_code(iata), city, iata, name))


def search_fallback_airports(keyword: str, *, limit: int = 20) -> tuple[list[dict[str, Any]], str]:
    """
    RollingGo 不可用时的回退链：
    1. 三字码 → rotatepilot / airportsapi 精确查
    2. OurAirports 本地英文/IATA 子串
    """
    kw = keyword.strip()
    if not kw:
        return [], "none"

    if len(kw) == 3 and kw.isalpha():
        for fn, source in (
            (search_rotatepilot_iata, "rotatepilot"),
            (search_airportsapi_iata, "airportsapi"),
        ):
            item = fn(kw)
            if item:
                return [item], source

    local = search_local_airports(kw, limit=limit)
    if local:
        return local, "local"
    return [], "none"
