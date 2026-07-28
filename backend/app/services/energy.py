import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

from firebase_admin import firestore

from .firestore import (
    _get_period_range,
    _init_firebase_admin_once,
    firestore_operation_timeout_seconds,
)


COMMANDS_COLLECTION = os.getenv("FIRESTORE_COMMANDS_COLLECTION", "comandos")
DEFAULT_PUMP_POWER_KW = 0.75
DEFAULT_ELECTRICITY_PRICE_PER_KWH_BRL = 0.656


def load_energy_config() -> Dict[str, float]:
    return {
        "pump_power_kw": _env_float("PUMP_POWER_KW", DEFAULT_PUMP_POWER_KW),
        "electricity_price_per_kwh_brl": _env_float(
            "ELECTRICITY_PRICE_PER_KWH_BRL",
            DEFAULT_ELECTRICITY_PRICE_PER_KWH_BRL,
        ),
    }


def fetch_pump_command_events(period: str) -> List[Dict[str, Any]]:
    _init_firebase_admin_once()
    db = firestore.client()
    start, end = _get_period_range(period)
    timeout = firestore_operation_timeout_seconds()
    collection = db.collection(COMMANDS_COLLECTION)

    events: List[Dict[str, Any]] = []
    previous_query = (
        collection.where(filter=firestore.FieldFilter("timestamp", "<", start))
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(1)
    )
    for doc in previous_query.stream(retry=None, timeout=timeout):
        event = normalize_pump_event(doc.to_dict() or {}, doc_id=doc.id)
        if event:
            event["before_period"] = True
            events.append(event)

    period_query = (
        collection.where(filter=firestore.FieldFilter("timestamp", ">=", start))
        .where(filter=firestore.FieldFilter("timestamp", "<=", end))
        .order_by("timestamp")
    )
    for doc in period_query.stream(retry=None, timeout=timeout):
        event = normalize_pump_event(doc.to_dict() or {}, doc_id=doc.id)
        if event:
            events.append(event)
    return events


def get_energy_summary(period: str = "7d") -> Dict[str, Any]:
    return build_energy_summary(fetch_pump_command_events(period), period=period)


def build_energy_summary(
    events: Iterable[Dict[str, Any]],
    *,
    period: str = "7d",
    pump_power_kw: float | None = None,
    electricity_price_per_kwh_brl: float | None = None,
) -> Dict[str, Any]:
    config = load_energy_config()
    power_kw = pump_power_kw if pump_power_kw is not None else config["pump_power_kw"]
    price_per_kwh = (
        electricity_price_per_kwh_brl
        if electricity_price_per_kwh_brl is not None
        else config["electricity_price_per_kwh_brl"]
    )
    start, end = _get_period_range(period)
    normalized = sorted(
        [event for event in events if event.get("timestamp")],
        key=lambda item: item["timestamp"],
    )

    confirmed_events = [
        event
        for event in normalized
        if event.get("confirmed") is True
        and event.get("applied") is True
        and isinstance(event.get("pump_on"), bool)
    ]
    ignored_events = [
        event
        for event in normalized
        if event.get("applied") is False or event.get("overridden_by")
    ]

    current_on = False
    last_change_at = start
    total_on_seconds = 0.0
    intervals: List[Dict[str, Any]] = []
    open_interval_started_at: datetime | None = None

    for event in confirmed_events:
        timestamp = event["timestamp"]
        if timestamp < start:
            current_on = bool(event["pump_on"])
            open_interval_started_at = start if current_on else None
            continue
        if timestamp > end:
            break

        if current_on:
            seconds = max(0.0, (timestamp - last_change_at).total_seconds())
            total_on_seconds += seconds
            if open_interval_started_at:
                intervals.append(
                    {
                        "started_at": open_interval_started_at,
                        "ended_at": timestamp,
                        "duration_seconds": seconds,
                    }
                )

        current_on = bool(event["pump_on"])
        last_change_at = timestamp
        open_interval_started_at = timestamp if current_on else None

    if current_on:
        seconds = max(0.0, (end - last_change_at).total_seconds())
        total_on_seconds += seconds
        if open_interval_started_at:
            intervals.append(
                {
                    "started_at": open_interval_started_at,
                    "ended_at": end,
                    "duration_seconds": seconds,
                    "open_at_period_end": True,
                }
            )

    total_hours = total_on_seconds / 3600.0
    total_kwh = max(0.0, power_kw) * total_hours
    total_cost_brl = total_kwh * max(0.0, price_per_kwh)
    daily = _build_daily_energy(intervals, power_kw, price_per_kwh)

    return {
        "period": period,
        "pump_power_kw": power_kw,
        "electricity_price_per_kwh_brl": price_per_kwh,
        "total_on_seconds": total_on_seconds,
        "total_on_minutes": total_on_seconds / 60.0,
        "total_on_hours": total_hours,
        "total_kwh": total_kwh,
        "total_cost_brl": total_cost_brl,
        "confirmed_event_count": len(confirmed_events),
        "ignored_event_count": len(ignored_events),
        "intervals": intervals,
        "daily": daily,
        "events": [
            event
            for event in normalized
            if start <= event["timestamp"] <= end
        ],
        "estimated": True,
        "basis": "confirmed_pump_command_events",
    }


def normalize_pump_event(
    data: Dict[str, Any],
    *,
    doc_id: str | None = None,
) -> Dict[str, Any] | None:
    timestamp = _normalize_datetime(
        data.get("timestamp") or data.get("applied_at") or data.get("created_at")
    )
    pump_on = _read_optional_bool(data.get("applied_state"))
    if pump_on is None:
        pump_on = _read_optional_bool(data.get("pump_on"))
    if pump_on is None:
        pump_on = _parse_pump_state_from_text(data.get("bomba") or data.get("state"))

    confirmed = _read_optional_bool(data.get("confirmed"))
    applied = _read_optional_bool(data.get("applied"))
    if applied is None:
        applied = _read_optional_bool(data.get("state_changed"))

    return {
        "id": data.get("id") or doc_id,
        "command_id": data.get("command_id") or data.get("id") or doc_id,
        "timestamp": timestamp,
        "pump_on": pump_on,
        "requested_state": _read_optional_bool(data.get("requested_state")),
        "applied_state": pump_on,
        "confirmed": bool(confirmed),
        "applied": bool(applied),
        "state_changed": bool(_read_optional_bool(data.get("state_changed"))),
        "source": data.get("source") or data.get("acionamento") or "unknown",
        "priority": data.get("priority"),
        "overridden_by": data.get("overridden_by"),
        "reason": data.get("reason"),
        "raw_message": data.get("bomba"),
    }


def _read_optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("true", "1", "yes", "sim", "ligar", "ligada", "on"):
            return True
        if text in ("false", "0", "no", "nao", "não", "desligar", "desligada", "off"):
            return False
    return None


def _parse_pump_state_from_text(value: Any) -> bool | None:
    if not value:
        return None
    text = str(value).strip().lower()
    if "deslig" in text or " off" in text:
        return False
    if "lig" in text or " on" in text:
        return True
    return None


def _normalize_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return None


def _build_daily_energy(
    intervals: Iterable[Dict[str, Any]],
    power_kw: float,
    price_per_kwh: float,
) -> List[Dict[str, Any]]:
    daily: Dict[str, Dict[str, Any]] = {}
    for interval in intervals:
        started_at = _normalize_datetime(interval.get("started_at"))
        if started_at is None:
            continue
        key = started_at.strftime("%Y-%m-%d")
        item = daily.setdefault(
            key,
            {"date": key, "on_seconds": 0.0, "kwh": 0.0, "cost_brl": 0.0},
        )
        item["on_seconds"] += float(interval.get("duration_seconds") or 0.0)

    for item in daily.values():
        hours = item["on_seconds"] / 3600.0
        item["kwh"] = max(0.0, power_kw) * hours
        item["cost_brl"] = item["kwh"] * max(0.0, price_per_kwh)
    return list(sorted(daily.values(), key=lambda item: item["date"]))


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default
