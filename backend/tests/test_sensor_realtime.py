from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.services.sensor_realtime import SensorRealtimeEngine


BASE = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)


def event(event_id, sensor, estado, seconds):
    return {
        "event_id": event_id,
        "sensor": sensor,
        "estado": estado,
        "timestamp": BASE + timedelta(seconds=seconds),
        "device_id": "esp32-reservatorio-01",
    }


def cycle(seconds, index=0):
    return {
        "cycle_id": f"sample-{index}-{seconds}",
        "start_event_id": f"comandos/start-{index}",
        "end_event_id": f"sensores/end-{index}",
        "started_at": BASE + timedelta(hours=index),
        "low_raised_at": BASE + timedelta(hours=index, seconds=60),
        "ended_at": BASE + timedelta(hours=index, seconds=seconds),
        "fill_time_seconds": seconds,
        "low_to_high_seconds": seconds - 60,
        "pump_to_low_seconds": 60,
        "valid": True,
        "device_id": "esp32-reservatorio-01",
        "start_source": "pump_command_confirmed",
    }


@patch("app.services.sensor_realtime.save_filling_cycle")
@patch("app.services.sensor_realtime.save_alerts")
def test_realtime_engine_persists_interlock_alert_and_blocks_cycle(
    save_alerts_mock,
    save_filling_cycle_mock,
):
    save_alerts_mock.side_effect = lambda alerts: [
        {"id": f"alert-{index}", **alert}
        for index, alert in enumerate(alerts)
    ]
    engine = SensorRealtimeEngine()

    result = engine.process_event(
        event("sensores/high", "alto", "subiu", 120),
        history=[event("sensores/low", "baixo", "desceu", 0)],
        command_history=[],
    )

    assert [alert["type"] for alert in result["alerts_created"]] == [
        "unexpected_high_without_low"
    ]
    assert result["cycle_created"] is None
    assert result["autocloud"]["reason"] == "deterministic_rule_alert"
    save_alerts_mock.assert_called_once()
    save_filling_cycle_mock.assert_not_called()


@patch("app.services.sensor_realtime.save_autocloud_filling_sample")
@patch("app.services.sensor_realtime.save_filling_cycle")
@patch("app.services.sensor_realtime.save_alerts")
def test_realtime_engine_persists_autocloud_alert_from_seeded_samples(
    save_alerts_mock,
    save_filling_cycle_mock,
    save_sample_mock,
):
    save_alerts_mock.side_effect = lambda alerts: [
        {"id": f"alert-{index}", **alert}
        for index, alert in enumerate(alerts)
    ]
    save_filling_cycle_mock.side_effect = lambda created_cycle: {
        "id": created_cycle["cycle_id"],
        "cycle_id": created_cycle["cycle_id"],
        "fill_time_seconds": created_cycle["fill_time_seconds"],
    }
    save_sample_mock.side_effect = lambda created_cycle, _analysis: {
        "id": created_cycle["cycle_id"],
        "cycle_id": created_cycle["cycle_id"],
    }
    engine = SensorRealtimeEngine()

    result = engine.process_event(
        event("sensores/current-high", "alto", "subiu", 900),
        history=[
            event("sensores/current-low-down", "baixo", "desceu", 0),
            event("sensores/current-low-up", "baixo", "subiu", 60),
        ],
        command_history=[],
        historical_autocloud_samples=[
            cycle(seconds, index)
            for index, seconds in enumerate([470, 480, 485, 490, 475])
        ],
    )

    assert result["alerts_created"][0]["type"] == "slow_fill_cycle"
    assert result["cycle_created"]["fill_time_seconds"] == 900
    assert result["autocloud"]["method"] == "autocloud_filling_cycle_clustering"
    assert result["autocloud_sample_created"]["cycle_id"] == result["cycle_created"]["cycle_id"]
    save_alerts_mock.assert_called_once()
    save_filling_cycle_mock.assert_called_once()
    save_sample_mock.assert_called_once()
