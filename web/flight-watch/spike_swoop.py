#!/usr/bin/env python3
"""Spike: swoop-flights 2-leg 开口程查价样例。"""
from __future__ import annotations

from swoop import SORT_CHEAPEST, price_selector, search_legs, set_country
from swoop.builders import SearchLeg


def main() -> None:
    legs = [
        SearchLeg(date="2027-02-04", from_airport="PVG", to_airport="LAX"),
        SearchLeg(date="2027-02-14", from_airport="LAX", to_airport="NRT"),
    ]
    print("=== swoop-flights 2-leg open-jaw spike ===")
    for region in (None, "CN"):
        if region:
            print(f"\n--- set_country({region}) ---")
            try:
                set_country(region)
            except Exception as exc:
                print("set_country failed:", exc)
                continue
        else:
            print("\n--- default region ---")
        try:
            r = search_legs(legs, sort=SORT_CHEAPEST)
        except Exception as exc:
            print("search_legs error:", exc)
            continue
        print("price_range:", r.price_range, "results:", len(r.results))
        for i, item in enumerate(r.results[:3]):
            print(f"  [{i}] list={item.price} {item.currency} legs={len(item.legs)}")
            if item.selector:
                try:
                    b = price_selector(item.selector)
                    print(f"       price_selector={b.price if b else None} {b.currency if b else ''}")
                except Exception as exc:
                    print(f"       price_selector error: {exc}")


if __name__ == "__main__":
    main()
