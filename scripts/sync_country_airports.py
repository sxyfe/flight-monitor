#!/usr/bin/env python3
"""从 OurAirports 生成五国民航城市编码目录 country_city_codes.json。"""
from __future__ import annotations

import csv
import json
import math
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUTPUT_PATHS = [
    DATA_DIR / "country_city_codes.json",
    ROOT.parent
    / ".cursor/skills/flight-monitor-agent/scripts/data/country_city_codes.json",
]

OURAIRPORTS_CSV = "https://davidmegginson.github.io/ourairports-data/airports.csv"
OURAIRPORTS_COUNTRIES = "https://davidmegginson.github.io/ourairports-data/countries.csv"

HOT_LIMIT = 8
EXHAUSTIVE_FRACTION = 0.5

# 中文国名 → ISO 3166-1 alpha-2
COUNTRY_ZH_TO_ISO: dict[str, str] = {
    "泰国": "TH",
    "菲律宾": "PH",
    "印度尼西亚": "ID",
    "马来西亚": "MY",
    "日本": "JP",
}

# 机场 IATA → RollingGo 查价用 cityCode（都市圈合并）
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
    "CRK": "CRK",
    "MNL": "MNL",
    "SGL": "MNL",
}

# 热度种子序（靠前更热门；未列出者按大型/中型机场分值排序）
POPULARITY_SEED: dict[str, list[str]] = {
    "泰国": [
        "BKK", "HKT", "CNX", "USM", "KBV", "HDY", "UTP", "CEI",
        "UTH", "URT", "KKC", "NST", "HHQ", "LPT",
    ],
    "菲律宾": [
        "MNL", "CEB", "CRK", "DVO", "ILO", "PPS", "KLO", "BCD",
        "CGY", "ILO", "GES", "MPH", "TAG",
    ],
    "印度尼西亚": [
        "JKT", "DPS", "SUB", "UPG", "MES", "YIA", "BPN", "SRG",
        "PLM", "LOP", "BDO", "JOG", "PDG", "AMQ", "MDC",
    ],
    "马来西亚": [
        "KUL", "PEN", "LGK", "JHB", "KCH", "BKI", "TWU", "MYY",
        "SBW", "TGG", "AOR", "LBU",
    ],
    "日本": [
        "TYO", "OSA", "FUK", "NGO", "SPK", "OKA", "HIJ", "SDJ",
        "KMJ", "KOJ", "KMQ", "NGS", "AOJ", "HKD", "MYJ", "TAK",
    ],
}

ALLOWED_TYPES = frozenset({"large_airport", "medium_airport"})


def _download_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=120) as resp:
        return resp.read().decode("utf-8")


def _city_code(iata: str) -> str:
    code = (iata or "").strip().upper()
    if not code:
        return ""
    return AIRPORT_IATA_TO_CITY_CODE.get(code, code)


def _label_from_row(row: dict[str, str]) -> str:
    municipality = (row.get("municipality") or "").strip()
    name = (row.get("name") or "").strip()
    if municipality:
        return municipality.replace("（", "(").split("(")[0].strip()
    if name:
        return name.split(" ")[0].split("机场")[0].strip()
    return row.get("iata_code", "").strip()


def _type_score(airport_type: str) -> int:
    return 100 if airport_type == "large_airport" else 50


def _rank_cities(zh: str, cities: dict[str, tuple[str, int]]) -> list[str]:
    seed = POPULARITY_SEED.get(zh, [])

    def sort_key(city: str) -> tuple:
        label, score = cities[city]
        if city in seed:
            return (0, seed.index(city), city)
        return (1, -score, city)

    return sorted(cities.keys(), key=sort_key)


def _split_exhaustive_hot(ranked: list[str]) -> tuple[list[str], list[str]]:
    n = len(ranked)
    if n == 0:
        return [], []
    hot = ranked[: min(HOT_LIMIT, n)]
    ex_n = max(len(hot), math.ceil(n * EXHAUSTIVE_FRACTION))
    exhaustive = ranked[:ex_n]
    return exhaustive, hot


def build_catalog(airports_csv: str, countries_csv: str) -> dict:
    iso_to_en: dict[str, str] = {}
    reader = csv.DictReader(countries_csv.splitlines())
    for row in reader:
        code = (row.get("code") or "").strip()
        name = (row.get("name") or "").strip()
        if code and name:
            iso_to_en[code] = name

    by_country: dict[str, dict[str, tuple[str, int]]] = {zh: {} for zh in COUNTRY_ZH_TO_ISO}

    reader = csv.DictReader(airports_csv.splitlines())
    for row in reader:
        iso = (row.get("iso_country") or "").strip()
        zh = next((z for z, i in COUNTRY_ZH_TO_ISO.items() if i == iso), None)
        if not zh:
            continue
        airport_type = row.get("type") or ""
        if airport_type not in ALLOWED_TYPES:
            continue
        if (row.get("scheduled_service") or "").lower() != "yes":
            continue
        iata = (row.get("iata_code") or "").strip().upper()
        if len(iata) != 3:
            continue
        city = _city_code(iata)
        if not city:
            continue
        label = _label_from_row(row)
        score = _type_score(airport_type)
        prev = by_country[zh].get(city)
        if not prev or score > prev[1] or (score == prev[1] and len(label) < len(prev[0])):
            by_country[zh][city] = (label, score)

    countries: dict[str, dict] = {}
    for zh, iso in COUNTRY_ZH_TO_ISO.items():
        ranked = _rank_cities(zh, by_country[zh])
        exhaustive, hot = _split_exhaustive_hot(ranked)
        labels = {code: by_country[zh][code][0] for code in ranked}
        countries[zh] = {
            "iso": iso,
            "name_en": iso_to_en.get(iso, ""),
            "exhaustive": exhaustive,
            "hot": hot,
            "labels": {code: labels[code] for code in exhaustive},
        }

    return {
        "meta": {
            "version": 2,
            "source": "OurAirports",
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "airports_url": OURAIRPORTS_CSV,
            "filter": "large_airport|medium_airport, scheduled_service=yes, iata_code present",
            "ranking": f"POPULARITY_SEED + airport type; exhaustive=top {int(EXHAUSTIVE_FRACTION * 100)}%; hot=top {HOT_LIMIT}",
        },
        "countries": countries,
    }


def main() -> None:
    print("Downloading OurAirports CSV…")
    airports_csv = _download_text(OURAIRPORTS_CSV)
    countries_csv = _download_text(OURAIRPORTS_COUNTRIES)
    catalog = build_catalog(airports_csv, countries_csv)

    for path in OUTPUT_PATHS:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {path}")

    for zh, entry in catalog["countries"].items():
        print(
            f"  {zh}: ranked={len(entry['labels'])}, "
            f"exhaustive={len(entry['exhaustive'])}, hot={len(entry['hot'])}"
        )


if __name__ == "__main__":
    main()
