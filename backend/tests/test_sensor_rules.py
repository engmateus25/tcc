from datetime import datetime, timedelta, timezone

from app.services.sensor_rules import SensorRuleConfig, evaluate_sensor_event_rules


BASE = datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc)
CONFIG = SensorRuleConfig(
    duplicate_window_seconds=5,
    out_of_order_tolerance_seconds=2,
    min_plausible_drain_time_seconds=60,
)


def event(event_id, sensor, estado, seconds):
    return {
        "event_id": event_id,
        "sensor": sensor,
        "estado": estado,
        "timestamp": BASE + timedelta(seconds=seconds),
    }


def alert_types(alerts):
    return {alert["type"] for alert in alerts}


def test_duplicate_event_within_window_is_flagged():
    alerts = evaluate_sensor_event_rules(
        event("sensores/doc-2", "baixo", "desceu", 3),
        [event("sensores/doc-1", "baixo", "desceu", 0)],
        CONFIG,
    )

    assert "duplicate_event" in alert_types(alerts)


def test_repeated_low_before_high_is_flagged_after_duplicate_window():
    alerts = evaluate_sensor_event_rules(
        event("sensores/doc-2", "baixo", "desceu", 20),
        [event("sensores/doc-1", "baixo", "desceu", 0)],
        CONFIG,
    )

    assert "unexpected_low_repeat" in alert_types(alerts)


def test_implausible_drain_time_is_flagged():
    alerts = evaluate_sensor_event_rules(
        event("sensores/doc-2", "baixo", "desceu", 30),
        [event("sensores/doc-1", "alto", "subiu", 0)],
        CONFIG,
    )

    assert "implausible_drain_time" in alert_types(alerts)


def test_out_of_order_event_is_flagged():
    alerts = evaluate_sensor_event_rules(
        event("sensores/doc-2", "alto", "subiu", 8),
        [event("sensores/doc-1", "baixo", "subiu", 12)],
        CONFIG,
    )

    assert "out_of_order_event" in alert_types(alerts)


def test_high_rising_after_low_dropped_is_flagged():
    alerts = evaluate_sensor_event_rules(
        event("sensores/doc-2", "alto", "subiu", 30),
        [event("sensores/doc-1", "baixo", "desceu", 0)],
        CONFIG,
    )

    assert "unexpected_high_without_low" in alert_types(alerts)


def test_missing_timestamp_blocks_cycle_processing():
    alerts = evaluate_sensor_event_rules(
        {"event_id": "sensores/doc-1", "sensor": "baixo", "estado": "subiu"},
        [],
        CONFIG,
    )

    assert alerts[0]["type"] == "missing_timestamp"
    assert alerts[0]["metadata"]["blocks_cycle_processing"] is True
