import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from firebase_admin import firestore
from google.api_core.exceptions import Conflict

from .firestore import (
    SENSORS_COLLECTION,
    _init_firebase_admin_once,
    firestore_operation_timeout_seconds,
)


PROCESSING_COLLECTION = os.getenv(
    "FIRESTORE_SENSOR_EVENT_PROCESSING_COLLECTION",
    "sensor_event_processing",
)


@dataclass(frozen=True)
class SensorEventReservation:
    event_id: str
    processing_key: str
    payload_hash: str
    duplicate: bool
    existing_status: Optional[str] = None
    payload_hash_mismatch: Optional[bool] = None


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def build_payload_hash(event: Dict[str, Any]) -> str:
    stable_payload = {
        key: event.get(key)
        for key in (
            "document_id",
            "event_id",
            "sensor",
            "estado",
            "timestamp",
            "device_id",
            "source",
            "raw_path",
        )
        if event.get(key) is not None
    }
    encoded = json.dumps(_json_safe(stable_payload), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_event_identity(event: Dict[str, Any]) -> str:
    explicit_event_id = _clean_string(event.get("event_id"))
    if explicit_event_id:
        return explicit_event_id

    raw_path = _clean_string(event.get("raw_path"))
    if raw_path:
        return raw_path

    document_id = _clean_string(event.get("document_id"))
    if document_id:
        return f"{SENSORS_COLLECTION}/{document_id}"

    return f"legacy:{build_payload_hash(event)}"


def build_processing_key(event_id: str) -> str:
    return hashlib.sha256(event_id.encode("utf-8")).hexdigest()


def reserve_sensor_event_processing(event: Dict[str, Any]) -> SensorEventReservation:
    event_id = build_event_identity(event)
    processing_key = build_processing_key(event_id)
    payload_hash = build_payload_hash(event)

    _init_firebase_admin_once()
    db = firestore.client()
    ref = db.collection(PROCESSING_COLLECTION).document(processing_key)
    timeout = firestore_operation_timeout_seconds()

    processing_doc = {
        "event_id": event_id,
        "processing_key": processing_key,
        "payload_hash": payload_hash,
        "status": "processing",
        "document_id": event.get("document_id"),
        "raw_path": event.get("raw_path"),
        "sensor": event.get("sensor"),
        "estado": event.get("estado"),
        "device_id": event.get("device_id"),
        "source": event.get("source"),
        "event_timestamp": event.get("timestamp"),
        "received_at": event.get("received_at"),
        "created_at": firestore.SERVER_TIMESTAMP,
        "updated_at": firestore.SERVER_TIMESTAMP,
    }

    try:
        ref.create(processing_doc, retry=None, timeout=timeout)
    except Conflict:
        existing = ref.get(retry=None, timeout=timeout).to_dict() or {}
        existing_hash = existing.get("payload_hash")
        return SensorEventReservation(
            event_id=event_id,
            processing_key=processing_key,
            payload_hash=payload_hash,
            duplicate=True,
            existing_status=existing.get("status") or "unknown",
            payload_hash_mismatch=bool(existing_hash and existing_hash != payload_hash),
        )

    return SensorEventReservation(
        event_id=event_id,
        processing_key=processing_key,
        payload_hash=payload_hash,
        duplicate=False,
        existing_status="processing",
        payload_hash_mismatch=False,
    )


def mark_sensor_event_processed(
    reservation: SensorEventReservation,
    result: Dict[str, Any],
) -> None:
    _update_processing_doc(
        reservation.processing_key,
        {
            "status": "processed",
            "result": result,
            "processed_at": firestore.SERVER_TIMESTAMP,
        },
    )


def mark_sensor_event_failed(
    reservation: SensorEventReservation,
    error: Exception,
) -> None:
    _update_processing_doc(
        reservation.processing_key,
        {
            "status": "failed",
            "error": str(error),
            "failed_at": firestore.SERVER_TIMESTAMP,
        },
    )


def _update_processing_doc(processing_key: str, data: Dict[str, Any]) -> None:
    _init_firebase_admin_once()
    db = firestore.client()
    db.collection(PROCESSING_COLLECTION).document(processing_key).update(
        {
            **data,
            "updated_at": firestore.SERVER_TIMESTAMP,
        },
        retry=None,
        timeout=firestore_operation_timeout_seconds(),
    )


def _clean_string(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
