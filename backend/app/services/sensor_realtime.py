from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List

from .alerts_store import save_alerts
from .autocloud_fill_time import analyze_fill_time_cycle
from .filling_cycles import FillingCycleTracker, save_filling_cycle
from .firestore import fetch_recent_sensor_events_before, is_firestore_dependency_error
from .sensor_event_processing import (
    mark_sensor_event_failed,
    mark_sensor_event_processed,
    reserve_sensor_event_processing,
)
from .sensor_rules import (
    evaluate_sensor_event_rules,
    event_blocks_cycle_processing,
)


class SensorRealtimeEngine:
    """
    Processa eventos de sensor em tempo real.

    A ordem e intencional:
    1. regras deterministicas;
    2. persistencia deduplicada de alertas;
    3. extracao de ciclo baixo subiu -> alto subiu;
    4. analise temporal de fill_time_seconds.
    """

    def __init__(self, max_history_events: int = 200):
        self.lock = Lock()
        self.max_history_events = max_history_events
        self.recent_events: List[Dict[str, Any]] = []
        self.cycle_tracker = FillingCycleTracker()

    def process_event(
        self,
        event: Dict[str, Any],
        history: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        with self.lock:
            context_history = self._context_history(event, history or [])
            rule_alerts = evaluate_sensor_event_rules(event, context_history)
            blocks_cycle = event_blocks_cycle_processing(rule_alerts)

            cycle = None
            autocloud_result: Dict[str, Any] = {
                "used": False,
                "reason": "cycle_not_complete",
            }

            cycle_tracker = self.cycle_tracker
            if history:
                cycle_tracker = _build_cycle_tracker_from_history(context_history)

            historical_cycles = list(cycle_tracker.completed_cycles)
            if blocks_cycle:
                autocloud_result = {
                    "used": False,
                    "reason": "deterministic_rule_alert",
                }
            else:
                cycle = cycle_tracker.process_event(event)
                if cycle:
                    autocloud_result = analyze_fill_time_cycle(
                        cycle,
                        historical_cycles,
                    )

            self.cycle_tracker = cycle_tracker
            self._remember_event(event)

        alerts_to_save = list(rule_alerts)
        autocloud_alert = autocloud_result.get("alert")
        if autocloud_alert:
            alerts_to_save.append(autocloud_alert)

        alerts_created = save_alerts(alerts_to_save) if alerts_to_save else []
        cycle_created = save_filling_cycle(cycle) if cycle else None

        return {
            "rule_alerts": rule_alerts,
            "alerts_created": alerts_created,
            "cycle_created": cycle_created,
            "autocloud": _public_autocloud_result(autocloud_result),
        }

    def _remember_event(self, event: Dict[str, Any]) -> None:
        self.recent_events.append(event)
        if len(self.recent_events) > self.max_history_events:
            self.recent_events = self.recent_events[-self.max_history_events :]

    def _context_history(
        self,
        event: Dict[str, Any],
        persisted_history: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        current_key = _history_key(event)
        merged: Dict[str, Dict[str, Any]] = {}
        for item in [*persisted_history, *self.recent_events]:
            key = _history_key(item)
            if key == current_key:
                continue
            merged[key] = item

        history = list(merged.values())
        history.sort(key=lambda item: _history_sort_key(item))
        return history[-self.max_history_events :]


_engine = SensorRealtimeEngine()


def process_new_sensor_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processa um evento de sensor com idempotencia persistida no Firestore.
    """
    reservation = reserve_sensor_event_processing(event)

    if reservation.duplicate:
        return {
            "processed": False,
            "duplicate": True,
            "event_id": reservation.event_id,
            "processing_key": reservation.processing_key,
            "processing_status": reservation.existing_status,
            "payload_hash_mismatch": reservation.payload_hash_mismatch,
            "alerts_created": [],
            "cycle_created": None,
            "autocloud": {
                "used": False,
                "reason": "duplicate_event",
            },
        }

    event_with_identity = {
        **event,
        "event_id": reservation.event_id,
        "processing_key": reservation.processing_key,
    }

    try:
        persisted_history = fetch_recent_sensor_events_before(
            event_with_identity,
            limit=_engine.max_history_events,
        )
        engine_result = _engine.process_event(
            event_with_identity,
            history=persisted_history,
        )
        result = {
            "processed": True,
            "duplicate": False,
            "event_id": reservation.event_id,
            "processing_key": reservation.processing_key,
            "processing_status": "processed",
            "payload_hash_mismatch": False,
            "alerts_created": engine_result.get("alerts_created") or [],
            "cycle_created": engine_result.get("cycle_created"),
            "autocloud": engine_result.get("autocloud") or {},
        }
        mark_sensor_event_processed(reservation, result)
        return result
    except Exception as exc:
        if not is_firestore_dependency_error(exc):
            try:
                mark_sensor_event_failed(reservation, exc)
            except Exception:
                pass
        raise


def _public_autocloud_result(result: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in result.items() if key != "alert"}


def _build_cycle_tracker_from_history(
    history: List[Dict[str, Any]],
) -> FillingCycleTracker:
    tracker = FillingCycleTracker()
    validated_history: List[Dict[str, Any]] = []
    for item in history:
        alerts = evaluate_sensor_event_rules(item, validated_history)
        if not event_blocks_cycle_processing(alerts):
            tracker.process_event(item)
        validated_history.append(item)
    return tracker


def _history_key(event: Dict[str, Any]) -> str:
    for key in ("event_id", "raw_path", "document_id"):
        value = event.get(key)
        if value:
            text = str(value).strip()
            if text:
                return text
    return ":".join(
        [
            str(event.get("sensor") or ""),
            str(event.get("estado") or ""),
            str(event.get("timestamp") or ""),
        ]
    )


def _normalize_datetime(value: Any):
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return None


def _history_sort_key(event: Dict[str, Any]) -> datetime:
    return _normalize_datetime(event.get("timestamp")) or datetime.min.replace(
        tzinfo=timezone.utc
    )
