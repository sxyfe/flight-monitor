#!/usr/bin/env python3
"""穷举搜索东南亚+日本特价机票（独立脚本，京津出发，urllib 直调 RollingGo）。

可单独拷贝运行，不依赖 flight_search_engine。
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

API_URL = "https://mcp.rollinggo.cn/api/mcp/flightsearch"
MAX_PRICE = 3000
MIN_STAY_DAYS = 7
CONCURRENCY = 6
OUTPUT = Path(__file__).parent / "exhaustive_results.json"

DATE_START = date(2026, 9, 25)
DATE_END = date(2026, 10, 7)

ORIGINS = {
    "BJS": "北京",
    "TSN": "天津",
    "SJW": "石家庄",
}

DESTINATIONS_BY_COUNTRY: dict[str, dict[str, dict]] = {
    "泰国": {
        "BKK": {"name": "曼谷", "airports": ["BKK(素万那普)", "DMK(廊曼)"]},
        "HKT": {"name": "普吉", "airports": ["HKT"]},
        "CNX": {"name": "清迈", "airports": ["CNX"]},
        "KBV": {"name": "甲米", "airports": ["KBV"]},
        "USM": {"name": "苏梅岛", "airports": ["USM"]},
        "HDY": {"name": "合艾", "airports": ["HDY"]},
        "CEI": {"name": "清莱", "airports": ["CEI"]},
        "UTH": {"name": "乌隆他尼", "airports": ["UTH"]},
        "HHQ": {"name": "华欣", "airports": ["HHQ"]},
        "UBP": {"name": "乌汶", "airports": ["UBP"]},
        "UTP": {"name": "乌塔堡", "airports": ["UTP"]},
    },
    "菲律宾": {
        "MNL": {"name": "马尼拉", "airports": ["MNL"]},
        "CEB": {"name": "宿务", "airports": ["CEB"]},
        "DVO": {"name": "达沃", "airports": ["DVO"]},
        "KLO": {"name": "卡利博", "airports": ["KLO"]},
        "CRK": {"name": "克拉克", "airports": ["CRK"]},
        "BXU": {"name": "长滩岛", "airports": ["BXU"]},
        "BGC": {"name": "巴拉望", "airports": ["BGC"]},
        "USU": {"name": "苏禄", "airports": ["USU"]},
    },
    "印度尼西亚": {
        "JKT": {"name": "雅加达", "airports": ["CGK"]},
        "DPS": {"name": "巴厘岛", "airports": ["DPS"]},
        "SUB": {"name": "泗水", "airports": ["SUB"]},
        "MES": {"name": "棉兰", "airports": ["KNO"]},
        "JOG": {"name": "日惹", "airports": ["YIA"]},
        "BDO": {"name": "万隆", "airports": ["BDO"]},
        "LOP": {"name": "龙目岛", "airports": ["LOP"]},
        "MDC": {"name": "美娜多", "airports": ["MDC"]},
        "TKG": {"name": "丹戎槟榔", "airports": ["TKG"]},

    },
    "马来西亚": {
        "KUL": {"name": "吉隆坡", "airports": ["KUL"]},
        "KCH": {"name": "古晋", "airports": ["KCH"]},
        "JHB": {"name": "新山", "airports": ["JHB"]},
        "KBR": {"name": "哥打巴鲁", "airports": ["KBR"]},
        "TGG": {"name": "哥打基纳巴卢", "airports": ["TGG"]},
        "KUA": {"name": "瓜拉丁加奴", "airports": ["KUA"]},
        "BKI": {"name": "亚庇", "airports": ["BKI"]},
        "MZV": {"name": "山打根", "airports": ["MZV"]},
        "LBU": {"name": "斗湖", "airports": ["LBU"]},
        "TWU": {"name": "仙本那", "airports": ["TWU"]},
        "BBN": {"name": "纳闽", "airports": ["BBN"]},
    },
    "日本": {
        "TYO": {"name": "东京", "airports": ["NRT", "HND"]},
        "OSA": {"name": "大阪", "airports": ["KIX", "ITM"]},
        "NGO": {"name": "名古屋", "airports": ["NGO"]},
        "FUK": {"name": "福冈", "airports": ["FUK"]},
        "SPK": {"name": "札幌", "airports": ["CTS"]},
        "OKA": {"name": "冲绳", "airports": ["OKA"]},
        "HIJ": {"name": "广岛", "airports": ["HIJ"]},
        "SDJ": {"name": "仙台", "airports": ["SDJ"]},
        "KMJ": {"name": "熊本", "airports": ["KMJ"]},
        "KOJ": {"name": "鹿儿岛", "airports": ["KOJ"]},
        "KMQ": {"name": "小松", "airports": ["KMQ"]},
        "MMY": {"name": "宫古岛", "airports": ["MMY"]},
        "KUH": {"name": "下地岛", "airports": ["KUH"]},
        "SHM": {"name": "下关", "airports": ["SHM"]},
    },
}

DESTINATIONS: dict[str, str] = {
    code: info["name"]
    for cities in DESTINATIONS_BY_COUNTRY.values()
    for code, info in cities.items()
}


def load_token() -> str:
    mcp = Path.home() / ".cursor/mcp.json"
    data = json.loads(mcp.read_text())
    return data["mcpServers"]["RollingGo-Flight"]["headers"]["Authorization"].split(" ", 1)[1]


def stay_days(out: date, ret: date) -> int:
    return (ret - out).days


def valid_date_pairs() -> list[tuple[date, date]]:
    pairs: list[tuple[date, date]] = []
    d = DATE_START
    days: list[date] = []
    while d <= DATE_END:
        days.append(d)
        d += timedelta(days=1)
    for out in days:
        for ret in days:
            if stay_days(out, ret) >= MIN_STAY_DAYS:
                pairs.append((out, ret))
    return pairs


def fmt_seg(segs: list[dict]) -> str:
    if not segs:
        return ""
    return " | ".join(
        f"{s['flightNumber']} {s['depAirport']}→{s['arrAirport']} {s['depTime'][5:16]}"
        for s in segs
    )


def seg_list(segs: list[dict]) -> list[dict]:
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


def search_flights(token: str, from_city: str, to_city: str, from_date: str, trip_type: str, ret_date: str | None = None) -> dict:
    body: dict = {
        "adultNumber": 1,
        "childNumber": 0,
        "cabinGrade": "ECONOMY",
        "fromCity": from_city,
        "toCity": to_city,
        "fromDate": from_date,
        "tripType": trip_type,
    }
    if ret_date:
        body["retDate"] = ret_date
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept-Language": "zh_CN",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}"}
    except Exception as e:
        return {"error": str(e)}


def cheapest(data: dict) -> dict | None:
    flights = data.get("flightInformationList") or []
    if not flights or "error" in data:
        return None
    return min(flights, key=lambda x: x["totalAdultPrice"])


def main():
    token = load_token()
    origins = list(ORIGINS.keys())
    dests = list(DESTINATIONS.keys())
    pairs = valid_date_pairs()
    out_days = sorted({out.isoformat() for out, _ in pairs})
    ret_days = sorted({ret.isoformat() for _, ret in pairs})

    rt_tasks: list[tuple[str, str, str, str]] = []
    for origin in origins:
        for dest in dests:
            for out, ret in pairs:
                rt_tasks.append((origin, dest, out.isoformat(), ret.isoformat()))

    ow_out_tasks: list[tuple[str, str, str]] = []
    ow_ret_tasks: list[tuple[str, str, str]] = []
    for origin in origins:
        for dest in dests:
            for d in out_days:
                ow_out_tasks.append((origin, dest, d))
    for dest in dests:
        for origin in origins:
            for d in ret_days:
                ow_ret_tasks.append((dest, origin, d))

    total = len(rt_tasks) + len(ow_out_tasks) + len(ow_ret_tasks)
    print(f"预估查询: {total}", flush=True)

    done = 0
    errors = 0
    rt_hits: list[dict] = []
    oj_hits: list[dict] = []
    ow_out_cache: dict[tuple[str, str, str], float] = {}
    ow_ret_cache: dict[tuple[str, str, str], float] = {}
    ow_out_detail: dict[tuple[str, str, str], list] = {}
    ow_ret_detail: dict[tuple[str, str, str], list] = {}

    def tick():
        nonlocal done
        done += 1
        if done % 100 == 0:
            print(f"进度: {done}/{total}", flush=True)

    def run_rt(task: tuple[str, str, str, str]):
        origin, dest, out, ret = task
        return ("rt", task, search_flights(token, origin, dest, out, "ROUND_TRIP", ret))

    def run_ow(task: tuple[str, str, str], kind: str):
        frm, to, d = task
        return (kind, task, search_flights(token, frm, to, d, "ONE_WAY"))

    jobs: list[tuple[str, object]] = [("rt", t) for t in rt_tasks]
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
            best = cheapest(data)
            if not best:
                continue
            price = best["totalAdultPrice"]
            if result_kind == "rt":
                if price > MAX_PRICE:
                    continue
                origin, dest, out, ret = result_task
                sd = stay_days(date.fromisoformat(out), date.fromisoformat(ret))
                rt_hits.append(
                    {
                        "trip_type": "round_trip",
                        "price": price,
                        "origin": origin,
                        "origin_name": ORIGINS[origin],
                        "dest": dest,
                        "dest_name": DESTINATIONS[dest],
                        "out_date": out,
                        "ret_date": ret,
                        "stay_days": sd,
                        "bookable": True,
                        "detail": "去: "
                        + fmt_seg(best.get("fromSegments", []))
                        + " | 回: "
                        + fmt_seg(best.get("retSegments", [])),
                        "segments_out": seg_list(best.get("fromSegments", [])),
                        "segments_ret": seg_list(best.get("retSegments", [])),
                    }
                )
            elif result_kind == "out":
                ow_out_cache[result_task] = price
                ow_out_detail[result_task] = seg_list(best.get("fromSegments", []))
            else:
                ow_ret_cache[result_task] = price
                ow_ret_detail[result_task] = seg_list(best.get("fromSegments", []))

    for origin in origins:
        for out_dest in dests:
            for ret_dest in dests:
                for ret_origin in origins:
                    for out_d in out_days:
                        for ret_d in ret_days:
                            if stay_days(date.fromisoformat(out_d), date.fromisoformat(ret_d)) < MIN_STAY_DAYS:
                                continue
                            out_p = ow_out_cache.get((origin, out_dest, out_d))
                            ret_p = ow_ret_cache.get((ret_dest, ret_origin, ret_d))
                            if out_p is None or ret_p is None:
                                continue
                            total_p = out_p + ret_p
                            if total_p > MAX_PRICE:
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
                            oj_hits.append(
                                {
                                    "trip_type": "open_jaw",
                                    "price": total_p,
                                    "origin": origin,
                                    "origin_name": ORIGINS[origin],
                                    "out_dest": out_dest,
                                    "out_dest_name": DESTINATIONS[out_dest],
                                    "ret_dest": ret_dest,
                                    "ret_dest_name": DESTINATIONS[ret_dest],
                                    "ret_origin": ret_origin,
                                    "ret_origin_name": ORIGINS[ret_origin],
                                    "route": f"{ORIGINS[origin]}→{DESTINATIONS[out_dest]} / {DESTINATIONS[ret_dest]}→{ORIGINS[ret_origin]}",
                                    "out_date": out_d,
                                    "ret_date": ret_d,
                                    "stay_days": sd,
                                    "bookable": False,
                                    "detail": f"去 ¥{out_p}: {sum_out} | 回 ¥{ret_p}: {sum_ret}",
                                    "price_out": out_p,
                                    "price_ret": ret_p,
                                }
                            )

    rt_hits.sort(key=lambda x: x["price"])
    oj_hits.sort(key=lambda x: x["price"])

    summary = {
        "max_price": MAX_PRICE,
        "min_stay_days": MIN_STAY_DAYS,
        "date_range": [DATE_START.isoformat(), DATE_END.isoformat()],
        "origins": ORIGINS,
        "destinations_by_country": DESTINATIONS_BY_COUNTRY,
        "errors": errors,
        "rt_hits": rt_hits,
        "oj_hits": oj_hits,
        "rt_cheapest": rt_hits[:20],
        "oj_cheapest": oj_hits[:20],
        "stats": {
            "total_queries": total,
            "errors": errors,
            "rt_count": len(rt_hits),
            "oj_count": len(oj_hits),
        },
    }
    OUTPUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n往返命中: {len(rt_hits)} | 开口程命中: {len(oj_hits)}", flush=True)
    print(f"详细结果: {OUTPUT}", flush=True)


if __name__ == "__main__":
    main()
