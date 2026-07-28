import os
from secrets import compare_digest

from fastapi import APIRouter, Header, HTTPException, Query, status
from app.schemas.dto import (
    AlertAcknowledgeResponse,
    AlertListResponse,
    SensorEventIn,
    SensorEventProcessResponse,
)
from app.services.alerts_store import acknowledge_alert, list_alerts
from app.services.sensor_anomaly import detect_intelligent_alerts
from app.services.sensor_realtime import process_new_sensor_event

router = APIRouter()
WEBHOOK_SECRET_HEADER = "X-AquaMonitor-Webhook-Secret"


@router.get("/sensors")
def get_sensor_alerts(
    period: str = Query("7d", description="Período para análise (ex: '7d', '30d', 'this_week')")
):
    """
    Retorna alertas inteligentes de inconsistências e anomalias dos sensores
    de nível (boias), combinando regras físicas e AutoCloud.
    """
    result = detect_intelligent_alerts(period=period)
    return result


@router.get("/alerts", response_model=AlertListResponse)
def get_persisted_alerts(
    period: str = Query("7d", description="Periodo para consulta (ex: '7d', '30d')"),
    status_filter: str | None = Query(None, alias="status"),
    severity: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    alerts = list_alerts(
        period=period,
        status=status_filter,
        severity=severity,
        limit=limit,
    )
    return {"total": len(alerts), "alerts": alerts}


@router.patch("/alerts/{alert_id}/ack", response_model=AlertAcknowledgeResponse)
def acknowledge_persisted_alert(alert_id: str):
    return acknowledge_alert(alert_id)

def _validate_sensor_event_secret(secret_header: str | None) -> None:
    expected_secret = (os.getenv("SENSOR_EVENT_WEBHOOK_SECRET") or "").strip()
    if not expected_secret:
        return
    if not isinstance(secret_header, str):
        secret_header = None
    if not secret_header or not compare_digest(secret_header, expected_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid sensor event webhook secret",
        )


@router.post("/sensor-event", response_model=SensorEventProcessResponse)
async def sensor_event_webhook(
    payload: SensorEventIn,
    x_aquamonitor_webhook_secret: str | None = Header(
        default=None,
        alias=WEBHOOK_SECRET_HEADER,
    ),
):
    """
    Endpoint chamado pela Cloud Function SEMPRE que um doc novo for criado em 'sensores'.
    """
    _validate_sensor_event_secret(x_aquamonitor_webhook_secret)
    result = process_new_sensor_event(payload.model_dump())
    return result
