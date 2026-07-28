import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple

import firebase_admin
from firebase_admin import credentials, firestore
from google.api_core.exceptions import (
    DeadlineExceeded,
    FailedPrecondition,
    PermissionDenied,
    RetryError,
    ServiceUnavailable,
    Unauthenticated,
)
from google.auth.exceptions import GoogleAuthError

try:
    import grpc
except ImportError:  # pragma: no cover - grpc vem das dependencias do Firestore
    grpc = None


SENSORS_COLLECTION = os.getenv("FIRESTORE_SENSORS_COLLECTION", "sensores")
DEFAULT_FIRESTORE_OPERATION_TIMEOUT_SECONDS = 10.0


FIRESTORE_DEPENDENCY_ERROR_TYPES = (
    DeadlineExceeded,
    FailedPrecondition,
    PermissionDenied,
    RetryError,
    ServiceUnavailable,
    Unauthenticated,
    GoogleAuthError,
)


def firestore_operation_timeout_seconds() -> float:
    raw_value = (os.getenv("FIRESTORE_OPERATION_TIMEOUT_SECONDS") or "").strip()
    if not raw_value:
        return DEFAULT_FIRESTORE_OPERATION_TIMEOUT_SECONDS
    try:
        value = float(raw_value)
    except ValueError:
        return DEFAULT_FIRESTORE_OPERATION_TIMEOUT_SECONDS
    return max(1.0, value)


def is_firestore_dependency_error(exc: Exception) -> bool:
    if isinstance(exc, FIRESTORE_DEPENDENCY_ERROR_TYPES):
        return True
    return grpc is not None and isinstance(exc, grpc.RpcError)


def _init_firebase_admin_once():
    if firebase_admin._apps:
        return
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    creds_inline = os.getenv("FIREBASE_CREDENTIALS_JSON")

    if creds_path and os.path.exists(creds_path):
        cred = credentials.Certificate(creds_path)
    elif creds_inline:
        cred = credentials.Certificate(json.loads(creds_inline))
    else:
        # Tenta ADC (gcloud / ambiente)
        cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred)

def _period_to_dates(period: str) -> Tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    if period == "30d":
        start = now - timedelta(days=30)
    elif period == "90d":
        start = now - timedelta(days=90)
    else:
        start = now - timedelta(days=7)
    return start, now

"""
def fetch_sensor_events(period: str = "7d") -> List[Dict]:
    _init_firebase_admin_once()
    db = firestore.client()

    start, end = _period_to_dates(period)
    q = (
        db.collection(SENSORS_COLLECTION)
          .where("timestamp", ">=", start)
          .where("timestamp", "<=", end)
          .order_by("timestamp", direction=firestore.Query.DESCENDING)
    )

    docs = q.stream()
    results = []
    for d in docs:
        data = d.to_dict()
        results.append({
            "id": d.id,
            "sensor": data.get("sensor"),
            "estado": data.get("estado"),
            "timestamp": data.get("timestamp"),
        })
    return results
"""

def build_summary(events: List[Dict]) -> Dict:
    by_sensor: Dict[str, int] = {}
    by_action: Dict[str, int] = {}
    for e in events:
        s = (e.get("sensor") or "").strip()
        a = (e.get("estado") or "").strip()
        if s:
            by_sensor[s] = by_sensor.get(s, 0) + 1
        if a:
            by_action[a] = by_action.get(a, 0) + 1

    return {
        "total_events": len(events),
        "by_sensor": dict(sorted(by_sensor.items(), key=lambda kv: kv[1], reverse=True)),
        "by_action": dict(sorted(by_action.items(), key=lambda kv: kv[1], reverse=True)),
    }


def _get_period_range(period: str) -> Tuple[datetime, datetime]:
    """
    Converte códigos de período em (start, end) em UTC.

    period exemplos:
    - "2d", "7d", "20d", "30d" -> últimos X dias
    - "this_week"              -> semana atual (domingo 00:00 até agora)
    - "this_month"             -> mês atual (dia 1 00:00 até agora)
    """
    now = datetime.now(timezone.utc)
    p = (period or "").strip().lower()

    # genérico Xd (dias)
    if p.endswith("d") and p[:-1].isdigit():
        days = int(p[:-1])
        start = now - timedelta(days=days)
        return start, now

    # genérico Xh (horas) – se um dia você quiser usar
    if p.endswith("h") and p[:-1].isdigit():
        hours = int(p[:-1])
        start = now - timedelta(hours=hours)
        return start, now

    # semana atual (começando no domingo)
    if p in ("this_week", "semana_atual"):
        # weekday() -> segunda=0 … domingo=6
        # queremos voltar até domingo (6)
        weekday = now.weekday()  # 0..6, sendo 6 domingo
        # se domingo, weekday=6 → deslocamento=0; se segunda (0), deslocamento=1 dia pra trás
        offset = (weekday + 1) % 7
        start = (now - timedelta(days=offset)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return start, now

    # mês atual
    if p in ("this_month", "mes_atual"):
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return start, now

    # compatibilidade com "7d", "30d", "90d" etc
    if p in ("7d", "30d", "90d"):
        days = int(p[:-1])
        start = now - timedelta(days=days)
        return start, now

    # fallback: últimos 7 dias
    start = now - timedelta(days=7)
    return start, now


def fetch_sensor_events(period: str) -> List[Dict]:
    """
    Busca todos os eventos de nível no período informado.

    Ajuste o nome da coleção abaixo conforme a sua estrutura real.
    """
    _init_firebase_admin_once()
    db = firestore.client()
    
    start, end = _get_period_range(period)

    col = db.collection(SENSORS_COLLECTION)

    # Filtra por timestamp e ordena cronologicamente
    query = (
        col.where(filter=firestore.FieldFilter("timestamp", ">=", start))
           .where(filter=firestore.FieldFilter("timestamp", "<=", end))
           .order_by("timestamp")
    )

    events: List[Dict] = []
    for doc in query.stream(retry=None, timeout=firestore_operation_timeout_seconds()):
        events.append(_sensor_event_from_doc(doc))

    return events


def fetch_recent_sensor_events_before(
    event: Dict,
    *,
    limit: int = 200,
) -> List[Dict]:
    event_ts = _normalize_datetime(event.get("timestamp"))
    if event_ts is None:
        return []

    _init_firebase_admin_once()
    db = firestore.client()
    capped_limit = max(1, min(limit, 500))
    query = (
        db.collection(SENSORS_COLLECTION)
        .where(filter=firestore.FieldFilter("timestamp", "<", event_ts))
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(capped_limit)
    )

    events: List[Dict] = []
    for doc in query.stream(retry=None, timeout=firestore_operation_timeout_seconds()):
        events.append(_sensor_event_from_doc(doc))
    events.reverse()
    return events


def _sensor_event_from_doc(doc) -> Dict:
    data = doc.to_dict() or {}
    raw_path = f"{SENSORS_COLLECTION}/{doc.id}"
    data.setdefault("document_id", doc.id)
    data.setdefault("raw_path", raw_path)
    data.setdefault("event_id", raw_path)
    return data


def _normalize_datetime(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return None
