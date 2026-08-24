import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Set

from firebase_admin import firestore
from google.api_core.exceptions import Conflict

from .firestore import _init_firebase_admin_once, firestore_operation_timeout_seconds


FILLING_CYCLES_COLLECTION = os.getenv(
    "FIRESTORE_FILLING_CYCLES_COLLECTION",
    "filling_cycles",
)


def is_cycle_start_event(event: Dict[str, Any]) -> bool:
    return _clean_text(event.get("sensor")) == "baixo" and _clean_text(event.get("estado")) == "desceu"


def is_cycle_end_event(event: Dict[str, Any]) -> bool:
    return _clean_text(event.get("sensor")) == "alto" and _clean_text(event.get("estado")) == "subiu"


def build_filling_cycle(
    start_event: Dict[str, Any],
    end_event: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    started_at = _normalize_datetime(start_event.get("timestamp"))
    ended_at = _normalize_datetime(end_event.get("timestamp"))
    if not started_at or not ended_at:
        return None

    fill_time_seconds = (ended_at - started_at).total_seconds()
    if fill_time_seconds <= 0:
        return None

    start_event_id = _event_identity(start_event)
    end_event_id = _event_identity(end_event)
    cycle_id = hashlib.sha256(
        f"{start_event_id}:{end_event_id}".encode("utf-8")
    ).hexdigest()

    return {
        "cycle_id": cycle_id,
        "start_event_id": start_event_id,
        "end_event_id": end_event_id,
        "started_at": started_at,
        "ended_at": ended_at,
        "pump_started_at": started_at if _is_pump_command_start(start_event) else None,
        "fill_time_seconds": fill_time_seconds,
        "valid": True,
        "device_id": end_event.get("device_id") or start_event.get("device_id"),
        "start_source": start_event.get("start_source") or _infer_start_source(start_event),
        "start_event_type": start_event.get("event_type") or _infer_event_type(start_event),
        "pump_mode": start_event.get("mode") or start_event.get("priority") or start_event.get("source"),
        "discard_reason": None,
        "metadata": {
            "start_sensor": start_event.get("sensor"),
            "start_estado": start_event.get("estado"),
            "start_command_id": start_event.get("command_id"),
            "start_applied": start_event.get("applied"),
            "start_confirmed": start_event.get("confirmed"),
            "end_sensor": end_event.get("sensor"),
            "end_estado": end_event.get("estado"),
        },
    }


def extract_filling_cycles(
    events: Iterable[Dict[str, Any]],
    *,
    invalid_event_ids: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
    invalid_event_ids = invalid_event_ids or set()
    tracker = FillingCycleTracker()
    cycles: List[Dict[str, Any]] = []

    ordered_events = [
        event for event in events if _normalize_datetime(event.get("timestamp")) is not None
    ]
    ordered_events.sort(key=lambda item: _normalize_datetime(item.get("timestamp")))

    for event in ordered_events:
        if _event_identity(event) in invalid_event_ids:
            continue
        cycle = tracker.process_event(event)
        if cycle:
            cycles.append(cycle)
    return cycles


def save_filling_cycle(cycle: Dict[str, Any]) -> Dict[str, Any]:
    _init_firebase_admin_once()
    db = firestore.client()
    ref = db.collection(FILLING_CYCLES_COLLECTION).document(cycle["cycle_id"])

    try:
        ref.create(
            {
                **cycle,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
            retry=None,
            timeout=firestore_operation_timeout_seconds(),
        )
    except Conflict:
        return _cycle_summary(cycle, duplicate=True)

    return _cycle_summary(cycle, duplicate=False)


@dataclass
class FillingCycleTracker:
    pending_start_by_device: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    completed_cycles: List[Dict[str, Any]] = field(default_factory=list)

    def process_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        device_key = str(event.get("device_id") or "default")

        if is_cycle_start_event(event):
            self.pending_start_by_device.setdefault(
                device_key,
                {
                    **event,
                    "start_source": event.get("start_source") or "sensor_low_fallback",
                    "event_type": event.get("event_type") or "sensor",
                },
            )
            return None

        if not is_cycle_end_event(event):
            return None

        start_event = self.pending_start_by_device.get(device_key)
        if not start_event:
            return None

        cycle = build_filling_cycle(start_event, event)
        if not cycle:
            return None

        self.pending_start_by_device.pop(device_key, None)
        self.completed_cycles.append(cycle)
        return cycle

    def process_command_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        device_key = str(event.get("device_id") or "default")
        if _is_pump_command_start(event):
            self.pending_start_by_device[device_key] = {
                **event,
                "start_source": "pump_command_confirmed",
                "event_type": "command",
            }
        elif _is_pump_command_stop(event):
            self.pending_start_by_device.pop(device_key, None)
        return None


def _cycle_summary(cycle: Dict[str, Any], *, duplicate: bool) -> Dict[str, Any]:
    return {
        "id": cycle["cycle_id"],
        "cycle_id": cycle["cycle_id"],
        "start_event_id": cycle["start_event_id"],
        "end_event_id": cycle["end_event_id"],
        "fill_time_seconds": cycle["fill_time_seconds"],
        "valid": cycle["valid"],
        "duplicate": duplicate,
    }


def _event_identity(event: Dict[str, Any]) -> str:
    for key in ("event_id", "raw_path", "document_id", "command_id"):
        value = event.get(key)
        if value:
            text = str(value).strip()
            if text:
                return text
    return "unknown"


def _is_pump_command_start(event: Dict[str, Any]) -> bool:
    return (
        _read_optional_bool(event.get("applied")) is True
        and _read_optional_bool(event.get("confirmed")) is True
        and _read_optional_bool(event.get("applied_state")) is True
    )


def _is_pump_command_stop(event: Dict[str, Any]) -> bool:
    return (
        _read_optional_bool(event.get("applied")) is True
        and _read_optional_bool(event.get("confirmed")) is True
        and _read_optional_bool(event.get("applied_state")) is False
    )


def _infer_start_source(event: Dict[str, Any]) -> str:
    if _is_pump_command_start(event):
        return "pump_command_confirmed"
    if is_cycle_start_event(event):
        return "sensor_low_fallback"
    return "unknown"


def _infer_event_type(event: Dict[str, Any]) -> str:
    if _is_pump_command_start(event) or _is_pump_command_stop(event):
        return "command"
    return "sensor"


def _clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip().lower()
    return text or None


def _read_optional_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("true", "1", "yes", "sim", "ligar", "ligada", "on"):
            return True
        if text in ("false", "0", "no", "nao", "não", "desligar", "desligada", "off"):
            return False
    return None


def _normalize_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return None
