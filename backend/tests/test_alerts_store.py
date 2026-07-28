from datetime import datetime, timezone

from app.services.alerts_store import build_alert_id, normalize_alert


def test_alert_id_is_stable_for_event_and_type():
    first = build_alert_id("sensores/doc-1", "unexpected_low_repeat")
    second = build_alert_id("sensores/doc-1", "unexpected_low_repeat")

    assert first == second
    assert first != build_alert_id("sensores/doc-1", "duplicate_event")


def test_normalize_alert_applies_defaults():
    sensor_timestamp = datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc)

    alert = normalize_alert(
        {
            "event_id": "sensores/doc-1",
            "type": "unexpected_low_repeat",
            "title": "Sensor baixo repetiu",
            "message": "Evento suspeito.",
            "sensor_timestamp": sensor_timestamp,
        }
    )

    assert alert["id"] == build_alert_id("sensores/doc-1", "unexpected_low_repeat")
    assert alert["severity"] == "warning"
    assert alert["status"] == "open"
    assert alert["acknowledged"] is False
    assert alert["sensor_timestamp"] == sensor_timestamp
