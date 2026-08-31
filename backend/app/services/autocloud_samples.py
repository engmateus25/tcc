from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from firebase_admin import firestore

from .firestore import _init_firebase_admin_once, firestore_operation_timeout_seconds


AUTOCLOUD_SAMPLES_COLLECTION = os.getenv(
    "FIRESTORE_AUTOCLOUD_SAMPLES_COLLECTION",
    "autocloud_filling_samples",
)


def fetch_autocloud_filling_samples(
    *,
    device_id: Optional[str] = None,
    before: Optional[datetime] = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    _init_firebase_admin_once()
    db = firestore.client()
    capped_limit = max(1, min(limit, 500))
    query = db.collection(AUTOCLOUD_SAMPLES_COLLECTION)

    before_dt = _normalize_datetime(before)
    if before_dt:
        query = query.where(filter=firestore.FieldFilter("ended_at", "<", before_dt))

    query = query.order_by("ended_at", direction=firestore.Query.DESCENDING).limit(capped_limit)

    samples: List[Dict[str, Any]] = []
    for doc in query.stream(retry=None, timeout=firestore_operation_timeout_seconds()):
        sample = doc.to_dict() or {}
        sample["id"] = sample.get("id") or doc.id
        if device_id and sample.get("device_id") not in (device_id, None, ""):
            continue
        if not sample.get("valid") or sample.get("fill_time_seconds") is None:
            continue
        samples.append(sample)

    samples.sort(key=lambda item: _normalize_datetime(item.get("ended_at")) or datetime.min.replace(tzinfo=timezone.utc))
    return samples[-capped_limit:]


def save_autocloud_filling_sample(
    cycle: Dict[str, Any],
    analysis: Optional[Dict[str, Any]] = None,
    *,
    source: str = "realtime_cycle_processing",
) -> Dict[str, Any]:
    document = build_autocloud_sample_document(cycle, analysis, source=source)
    _init_firebase_admin_once()
    db = firestore.client()
    ref = db.collection(AUTOCLOUD_SAMPLES_COLLECTION).document(document["id"])
    ref.set(
        {
            **document,
            "updated_at": firestore.SERVER_TIMESTAMP,
            "created_at": document.get("created_at") or firestore.SERVER_TIMESTAMP,
        },
        merge=True,
        retry=None,
        timeout=firestore_operation_timeout_seconds(),
    )
    return {
        "id": document["id"],
        "cycle_id": document["cycle_id"],
        "collection": AUTOCLOUD_SAMPLES_COLLECTION,
        "fill_time_seconds": document["fill_time_seconds"],
        "valid": document["valid"],
    }


def build_autocloud_sample_document(
    cycle: Dict[str, Any],
    analysis: Optional[Dict[str, Any]] = None,
    *,
    source: str = "manual_seed",
) -> Dict[str, Any]:
    analysis = analysis or {}
    cycle_metadata = dict(cycle.get("metadata") or {})
    feature_metadata = dict(
        analysis.get("feature_metadata")
        or (analysis.get("metadata") or {}).get("feature_metadata")
        or {}
    )
    cycle_id = str(cycle.get("cycle_id") or cycle.get("id") or "")
    if not cycle_id:
        raise ValueError("cycle_id is required to persist an AutoCloud sample")

    return {
        "id": cycle_id,
        "cycle_id": cycle_id,
        "start_event_id": cycle.get("start_event_id"),
        "end_event_id": cycle.get("end_event_id"),
        "started_at": _normalize_datetime(cycle.get("started_at")),
        "low_raised_at": _normalize_datetime(cycle.get("low_raised_at")),
        "ended_at": _normalize_datetime(cycle.get("ended_at")),
        "fill_time_seconds": float(cycle.get("fill_time_seconds") or 0.0),
        "low_to_high_seconds": _optional_float(cycle.get("low_to_high_seconds")),
        "pump_to_low_seconds": _optional_float(cycle.get("pump_to_low_seconds")),
        "valid": bool(cycle.get("valid", True)),
        "device_id": cycle.get("device_id"),
        "start_source": cycle.get("start_source"),
        "start_event_type": cycle.get("start_event_type"),
        "pump_mode": cycle.get("pump_mode"),
        "source": source,
        "test_run_id": cycle.get("test_run_id") or cycle_metadata.get("test_run_id"),
        "scenario": cycle.get("scenario") or cycle_metadata.get("scenario"),
        "method": analysis.get("method"),
        "analysis_reason": analysis.get("reason"),
        "class_index": analysis.get("class_index"),
        "cloud_count": analysis.get("cloud_count"),
        "nearest_normalized_distance": analysis.get("nearest_normalized_distance"),
        "training_samples": analysis.get("training_samples") or analysis.get("samples"),
        "feature_names": feature_metadata.get("feature_names"),
        "raw_features": feature_metadata.get("raw_features"),
        "normalized_features": feature_metadata.get("normalized_features"),
        "feature_medians": feature_metadata.get("feature_medians"),
        "feature_scales": feature_metadata.get("feature_scales"),
        "metadata": {
            **cycle_metadata,
            "autocloud": {
                key: value
                for key, value in analysis.items()
                if key not in {"alert", "feature_metadata"}
            },
            "feature_metadata": feature_metadata,
        },
    }


def merge_historical_samples(
    primary_cycles: Iterable[Dict[str, Any]],
    autocloud_samples: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for item in [*primary_cycles, *autocloud_samples]:
        cycle_id = str(item.get("cycle_id") or item.get("id") or "")
        if not cycle_id:
            continue
        merged[cycle_id] = item
    cycles = list(merged.values())
    cycles.sort(key=lambda item: _normalize_datetime(item.get("ended_at")) or datetime.min.replace(tzinfo=timezone.utc))
    return cycles


def _optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return None
