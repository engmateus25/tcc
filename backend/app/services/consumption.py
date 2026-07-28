import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

from firebase_admin import firestore

from .filling_cycles import FILLING_CYCLES_COLLECTION
from .firestore import (
    _get_period_range,
    _init_firebase_admin_once,
    firestore_operation_timeout_seconds,
)


DEFAULT_VOLUME_BETWEEN_SENSORS_LITERS = 500.0
DEFAULT_WATER_PRICE_PER_CUBIC_METER_BRL = 8.0


def load_consumption_config() -> Dict[str, float]:
    return {
        "reservoir_volume_between_sensors_liters": _env_float(
            "RESERVOIR_VOLUME_BETWEEN_SENSORS_LITERS",
            DEFAULT_VOLUME_BETWEEN_SENSORS_LITERS,
        ),
        "water_price_per_cubic_meter_brl": _env_float(
            "WATER_PRICE_PER_CUBIC_METER_BRL",
            DEFAULT_WATER_PRICE_PER_CUBIC_METER_BRL,
        ),
    }


def fetch_filling_cycles(period: str) -> List[Dict[str, Any]]:
    _init_firebase_admin_once()
    db = firestore.client()
    start, end = _get_period_range(period)
    timeout = firestore_operation_timeout_seconds()

    query = (
        db.collection(FILLING_CYCLES_COLLECTION)
        .where(filter=firestore.FieldFilter("ended_at", ">=", start))
        .where(filter=firestore.FieldFilter("ended_at", "<=", end))
        .order_by("ended_at")
    )

    cycles: List[Dict[str, Any]] = []
    for doc in query.stream(retry=None, timeout=timeout):
        data = doc.to_dict() or {}
        data["id"] = data.get("id") or data.get("cycle_id") or doc.id
        cycles.append(data)
    return cycles


def get_consumption_summary(period: str = "7d") -> Dict[str, Any]:
    return build_consumption_summary(fetch_filling_cycles(period), period=period)


def build_consumption_summary(
    cycles: Iterable[Dict[str, Any]],
    *,
    period: str = "7d",
    volume_between_sensors_liters: float | None = None,
    water_price_per_cubic_meter_brl: float | None = None,
) -> Dict[str, Any]:
    config = load_consumption_config()
    volume_liters = (
        volume_between_sensors_liters
        if volume_between_sensors_liters is not None
        else config["reservoir_volume_between_sensors_liters"]
    )
    price_per_m3 = (
        water_price_per_cubic_meter_brl
        if water_price_per_cubic_meter_brl is not None
        else config["water_price_per_cubic_meter_brl"]
    )

    valid_cycles = [cycle for cycle in cycles if bool(cycle.get("valid", True))]
    cycle_count = len(valid_cycles)
    total_liters = cycle_count * max(0.0, volume_liters)
    total_cubic_meters = total_liters / 1000.0
    total_cost_brl = total_cubic_meters * max(0.0, price_per_m3)
    days = max(1, _period_days(period))

    daily: Dict[str, Dict[str, Any]] = {}
    for cycle in valid_cycles:
        ended_at = _normalize_datetime(cycle.get("ended_at"))
        if ended_at is None:
            continue
        key = ended_at.strftime("%Y-%m-%d")
        item = daily.setdefault(
            key,
            {"date": key, "cycles": 0, "liters": 0.0, "cost_brl": 0.0},
        )
        item["cycles"] += 1
        item["liters"] += volume_liters
        item["cost_brl"] = (item["liters"] / 1000.0) * price_per_m3

    return {
        "period": period,
        "cycle_count": cycle_count,
        "volume_between_sensors_liters": volume_liters,
        "total_liters": total_liters,
        "total_cubic_meters": total_cubic_meters,
        "water_price_per_cubic_meter_brl": price_per_m3,
        "total_cost_brl": total_cost_brl,
        "average_liters_per_day": total_liters / days,
        "daily": list(sorted(daily.values(), key=lambda item: item["date"])),
        "estimated": True,
        "basis": "valid_filling_cycles",
    }


def _period_days(period: str) -> int:
    text = (period or "").strip().lower()
    if text.endswith("d") and text[:-1].isdigit():
        return int(text[:-1])
    return 7


def _normalize_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return None


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default
