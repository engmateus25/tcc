import hashlib
import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from firebase_admin import firestore
from google.api_core.exceptions import Conflict

from .firestore import (
    _get_period_range,
    _init_firebase_admin_once,
    firestore_operation_timeout_seconds,
)


ALERTS_COLLECTION = os.getenv("FIRESTORE_ALERTS_COLLECTION", "alerts")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def build_alert_id(event_id: str, alert_type: str) -> str:
    raw_key = f"{event_id}:{alert_type}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def normalize_alert(alert: Dict[str, Any]) -> Dict[str, Any]:
    event_id = str(alert.get("event_id") or "unknown")
    alert_type = str(alert.get("type") or "unknown_alert")
    metadata = dict(alert.get("metadata") or {})
    detected_at = _normalize_datetime(alert.get("detected_at")) or utc_now()
    sensor_timestamp = _normalize_datetime(alert.get("sensor_timestamp"))

    return {
        "id": alert.get("id") or build_alert_id(event_id, alert_type),
        "event_id": event_id,
        "type": alert_type,
        "severity": alert.get("severity") or "warning",
        "title": alert.get("title") or "Alerta do AquaMonitor",
        "message": alert.get("message") or "",
        "detected_at": detected_at,
        "sensor_timestamp": sensor_timestamp,
        "status": alert.get("status") or "open",
        "possible_causes": list(alert.get("possible_causes") or []),
        "metadata": metadata,
        "acknowledged": bool(alert.get("acknowledged", False)),
        "acknowledged_at": _normalize_datetime(alert.get("acknowledged_at")),
    }


def save_alert(alert: Dict[str, Any]) -> Dict[str, Any]:
    document = normalize_alert(alert)

    _init_firebase_admin_once()
    db = firestore.client()
    ref = db.collection(ALERTS_COLLECTION).document(document["id"])
    timeout = firestore_operation_timeout_seconds()

    try:
        ref.create(
            {
                **document,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
            retry=None,
            timeout=timeout,
        )
    except Conflict:
        existing = ref.get(retry=None, timeout=timeout).to_dict() or {}
        return _alert_summary(document, duplicate=True, status=existing.get("status"))

    return _alert_summary(document, duplicate=False)


def save_alerts(alerts: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [save_alert(alert) for alert in alerts]


def list_alerts(
    *,
    period: str = "7d",
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    _init_firebase_admin_once()
    db = firestore.client()
    start, end = _get_period_range(period)
    timeout = firestore_operation_timeout_seconds()

    query = (
        db.collection(ALERTS_COLLECTION)
        .where(filter=firestore.FieldFilter("detected_at", ">=", start))
        .where(filter=firestore.FieldFilter("detected_at", "<=", end))
    )
    if status:
        query = query.where(filter=firestore.FieldFilter("status", "==", status))
    if severity:
        query = query.where(filter=firestore.FieldFilter("severity", "==", severity))

    query = query.order_by("detected_at", direction=firestore.Query.DESCENDING).limit(
        max(1, min(limit, 500))
    )

    alerts: List[Dict[str, Any]] = []
    for doc in query.stream(retry=None, timeout=timeout):
        data = doc.to_dict() or {}
        data["id"] = data.get("id") or doc.id
        alerts.append(data)
    return alerts


def acknowledge_alert(alert_id: str) -> Dict[str, Any]:
    acknowledged_at = utc_now()

    _init_firebase_admin_once()
    db = firestore.client()
    ref = db.collection(ALERTS_COLLECTION).document(alert_id)
    ref.update(
        {
            "acknowledged": True,
            "acknowledged_at": acknowledged_at,
            "status": "acknowledged",
            "updated_at": firestore.SERVER_TIMESTAMP,
        },
        retry=None,
        timeout=firestore_operation_timeout_seconds(),
    )
    return {
        "id": alert_id,
        "acknowledged": True,
        "status": "acknowledged",
        "acknowledged_at": acknowledged_at,
    }


def _alert_summary(
    document: Dict[str, Any],
    *,
    duplicate: bool,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "id": document["id"],
        "event_id": document["event_id"],
        "type": document["type"],
        "severity": document["severity"],
        "status": status or document["status"],
        "duplicate": duplicate,
    }


def _normalize_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return None
