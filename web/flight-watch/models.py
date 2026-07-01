"""Watch 规则与查价结果模型。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

TripMode = Literal["round_trip", "one_way", "multi_leg", "open_jaw"]
PricingMode = Literal["auto", "same_ticket", "split_one_way"]


@dataclass
class Leg:
    from_city: str
    to_city: str
    date: str

    def to_dict(self) -> dict[str, str]:
        return {"from_city": self.from_city, "to_city": self.to_city, "date": self.date}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Leg:
        return cls(
            from_city=str(data["from_city"]).upper(),
            to_city=str(data["to_city"]).upper(),
            date=str(data["date"]),
        )


@dataclass
class WatchAlerts:
    max_price: float
    drop_abs: float = 200.0
    drop_pct: float = 5.0
    cooldown_hours: int = 24

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_price": self.max_price,
            "drop_abs": self.drop_abs,
            "drop_pct": self.drop_pct,
            "cooldown_hours": self.cooldown_hours,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WatchAlerts:
        return cls(
            max_price=float(data["max_price"]),
            drop_abs=float(data.get("drop_abs") or 200),
            drop_pct=float(data.get("drop_pct") or 5),
            cooldown_hours=int(data.get("cooldown_hours") or 24),
        )


@dataclass
class WatchSchedule:
    interval_hours: int = 12
    active_until: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "interval_hours": self.interval_hours,
            "active_until": self.active_until,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WatchSchedule:
        return cls(
            interval_hours=int(data.get("interval_hours") or 12),
            active_until=data.get("active_until") or None,
        )


@dataclass
class WatchFilters:
    carriers: list[str] = field(default_factory=list)
    cabin: str = "ECONOMY"

    def to_dict(self) -> dict[str, Any]:
        return {"carriers": self.carriers, "cabin": self.cabin}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> WatchFilters:
        data = data or {}
        carriers = data.get("carriers") or []
        return cls(
            carriers=[str(c).upper() for c in carriers],
            cabin=str(data.get("cabin") or "ECONOMY"),
        )


@dataclass
class Watch:
    id: str
    name: str
    enabled: bool
    trip_mode: TripMode
    legs: list[Leg]
    return_date: str | None
    pricing_mode: PricingMode
    sales_region: str | None
    currency: str
    filters: WatchFilters
    alerts: WatchAlerts
    schedule: WatchSchedule
    reference_price: float | None = None
    notes: str | None = None
    failure_count: int = 0
    failure_reason: str | None = None
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "enabled": self.enabled,
            "trip_mode": self.trip_mode,
            "legs": [l.to_dict() for l in self.legs],
            "return_date": self.return_date,
            "pricing_mode": self.pricing_mode,
            "sales_region": self.sales_region,
            "currency": self.currency,
            "filters": self.filters.to_dict(),
            "alerts": self.alerts.to_dict(),
            "schedule": self.schedule.to_dict(),
            "reference_price": self.reference_price,
            "notes": self.notes,
            "failure_count": self.failure_count,
            "failure_reason": self.failure_reason,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> Watch:
        import json

        legs_raw = json.loads(row["legs_json"])
        return cls(
            id=row["id"],
            name=row["name"],
            enabled=bool(row["enabled"]),
            trip_mode=row["trip_mode"],
            legs=[Leg.from_dict(x) for x in legs_raw],
            return_date=row.get("return_date"),
            pricing_mode=row.get("pricing_mode") or "auto",
            sales_region=row.get("sales_region"),
            currency=row.get("currency") or "CNY",
            filters=WatchFilters.from_dict(json.loads(row.get("filters_json") or "{}")),
            alerts=WatchAlerts.from_dict(json.loads(row["alerts_json"])),
            schedule=WatchSchedule.from_dict(json.loads(row["schedule_json"])),
            reference_price=row.get("reference_price"),
            notes=row.get("notes"),
            failure_count=int(row.get("failure_count") or 0),
            failure_reason=row.get("failure_reason"),
            created_at=row.get("created_at") or "",
            updated_at=row.get("updated_at") or "",
        )


@dataclass
class QuoteResult:
    price: float | None
    currency: str
    provider: str
    bookable: bool
    legs_summary: str
    error: str | None = None
    raw: dict[str, Any] | None = None

    def success(self) -> bool:
        return self.price is not None and self.error is None


@dataclass
class NotifyState:
    watch_id: str
    last_notified_price: float | None = None
    last_notified_at: str | None = None
    last_snapshot_price: float | None = None
