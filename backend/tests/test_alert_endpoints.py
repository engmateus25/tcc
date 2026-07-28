import asyncio
import os
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from google.api_core.exceptions import ServiceUnavailable

from app.main import app
from app.routers.alerts import (
    acknowledge_persisted_alert,
    get_persisted_alerts,
    get_sensor_alerts,
    sensor_event_webhook,
)
from app.schemas.dto import SensorEventIn


def test_alert_routes_are_registered_under_alerts_prefix():
    routes = {
        (route.path, tuple(sorted(route.methods or [])))
        for route in app.routes
        if hasattr(route, "methods")
    }

    assert ("/alerts", ("GET",)) in routes
    assert ("/alerts/{alert_id}/ack", ("PATCH",)) in routes
    assert ("/alerts/sensor-event", ("POST",)) in routes
    assert ("/alerts/sensors", ("GET",)) in routes


@patch("app.routers.alerts.list_alerts")
def test_get_persisted_alerts_endpoint_returns_service_alerts(list_mock):
    list_mock.return_value = [
        {
            "id": "alert-1",
            "event_id": "sensores/doc-1",
            "type": "unexpected_low_repeat",
            "severity": "warning",
            "status": "open",
        }
    ]

    response = get_persisted_alerts(
        period="30d",
        status_filter="open",
        severity="warning",
        limit=50,
    )

    assert response["total"] == 1
    assert response["alerts"][0]["type"] == "unexpected_low_repeat"
    list_mock.assert_called_once_with(
        period="30d",
        status="open",
        severity="warning",
        limit=50,
    )


@patch("app.routers.alerts.acknowledge_alert")
def test_acknowledge_persisted_alert_endpoint_calls_service(ack_mock):
    acknowledged_at = datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc)
    ack_mock.return_value = {
        "id": "alert-1",
        "acknowledged": True,
        "status": "acknowledged",
        "acknowledged_at": acknowledged_at,
    }

    response = acknowledge_persisted_alert("alert-1")

    assert response["id"] == "alert-1"
    assert response["acknowledged"] is True
    ack_mock.assert_called_once_with("alert-1")


@patch("app.routers.alerts.detect_intelligent_alerts")
def test_get_sensor_alerts_returns_503_when_firestore_is_unavailable(detect_mock):
    detect_mock.side_effect = ServiceUnavailable("invalid firestore credentials")

    with pytest.raises(HTTPException) as raised:
        get_sensor_alerts(period="7d")

    assert raised.value.status_code == 503
    assert "Firestore unavailable" in raised.value.detail


@patch("app.routers.alerts.list_alerts")
def test_get_persisted_alerts_returns_503_when_firestore_is_unavailable(list_mock):
    list_mock.side_effect = ServiceUnavailable("invalid firestore credentials")

    with pytest.raises(HTTPException) as raised:
        get_persisted_alerts(period="7d", status_filter="open")

    assert raised.value.status_code == 503
    assert "Firestore unavailable" in raised.value.detail


@patch("app.routers.alerts.acknowledge_alert")
def test_acknowledge_alert_returns_503_when_firestore_is_unavailable(ack_mock):
    ack_mock.side_effect = ServiceUnavailable("invalid firestore credentials")

    with pytest.raises(HTTPException) as raised:
        acknowledge_persisted_alert("alert-1")

    assert raised.value.status_code == 503
    assert "Firestore unavailable" in raised.value.detail


@patch.dict(os.environ, {"SENSOR_EVENT_WEBHOOK_SECRET": ""}, clear=False)
@patch("app.routers.alerts.process_new_sensor_event")
def test_sensor_event_webhook_returns_503_when_firestore_is_unavailable(process_mock):
    process_mock.side_effect = ServiceUnavailable("invalid firestore credentials")

    with pytest.raises(HTTPException) as raised:
        asyncio.run(
            sensor_event_webhook(
                SensorEventIn(
                    document_id="doc-1",
                    sensor="baixo",
                    estado="desceu",
                    timestamp="2026-07-27T12:00:00Z",
                    raw_path="sensores/doc-1",
                )
            )
        )

    assert raised.value.status_code == 503
    assert "Firestore unavailable" in raised.value.detail
