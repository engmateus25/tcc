import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.services.autocloud_fill_time import analyze_fill_time_cycle
from app.services.filling_cycles import FillingCycleTracker, extract_filling_cycles
from app.services.sensor_rules import SensorRuleConfig, evaluate_sensor_event_rules


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "autocloud" / "scenarios.json"
BASE = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)
RULE_CONFIG = SensorRuleConfig(
    duplicate_window_seconds=5,
    out_of_order_tolerance_seconds=2,
    min_plausible_drain_time_seconds=60,
)


def load_fixture():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def cycle(seconds, index=0):
    return {
        "cycle_id": f"cycle-{index}-{seconds}",
        "start_event_id": f"comandos/start-{index}",
        "end_event_id": f"sensores/end-{index}",
        "started_at": BASE,
        "ended_at": BASE + timedelta(seconds=seconds),
        "fill_time_seconds": seconds,
        "valid": True,
        "start_source": "pump_command_confirmed",
    }


def parse_event(item):
    parsed = dict(item)
    if parsed.get("timestamp"):
        parsed["timestamp"] = datetime.fromisoformat(
            parsed["timestamp"].replace("Z", "+00:00")
        )
    return parsed


def alert_types_for_sequence(events):
    history = []
    alert_types = set()
    for item in events:
        event = parse_event(item)
        alerts = evaluate_sensor_event_rules(event, history, RULE_CONFIG)
        alert_types.update(alert["type"] for alert in alerts)
        history.append(event)
    return alert_types


def test_autocloud_fixture_insufficient_data():
    data = load_fixture()["cycles"]["insufficient_data"]
    result = analyze_fill_time_cycle(
        cycle(data["current_seconds"]),
        [cycle(seconds, index) for index, seconds in enumerate(data["history_seconds"])],
        min_samples=5,
    )

    assert result["reason"] == "insufficient_data"


def test_autocloud_fixture_normal_baseline_has_no_alert():
    data = load_fixture()["cycles"]["normal_baseline"]
    result = analyze_fill_time_cycle(
        cycle(data["current_seconds"]),
        [cycle(seconds, index) for index, seconds in enumerate(data["history_seconds"])],
        min_samples=5,
        slow_factor=1.5,
        persistent_window=3,
    )

    assert result["reason"] == "normal_fill_time"
    assert result["alert"] is None


def test_autocloud_fixture_abrupt_slow_cycle_alerts():
    data = load_fixture()["cycles"]["abrupt_slow"]
    result = analyze_fill_time_cycle(
        cycle(data["current_seconds"]),
        [cycle(seconds, index) for index, seconds in enumerate(data["history_seconds"])],
        min_samples=5,
        slow_factor=1.5,
    )

    assert result["reason"] == "slow_fill_cycle"
    assert result["alert"]["type"] == "slow_fill_cycle"


def test_autocloud_fixture_gradual_degradation_alerts():
    data = load_fixture()["cycles"]["gradual_degradation"]
    result = analyze_fill_time_cycle(
        cycle(data["current_seconds"]),
        [cycle(seconds, index) for index, seconds in enumerate(data["history_seconds"])],
        min_samples=5,
        slow_factor=1.5,
        persistent_window=3,
    )

    assert result["reason"] == "persistent_fill_time_shift"
    assert result["alert"]["type"] == "persistent_fill_time_shift"


def test_sensor_rule_fixtures_cover_expected_alerts():
    sensors = load_fixture()["sensor_events"]

    assert "duplicate_event" in alert_types_for_sequence(sensors["duplicate"])
    assert "out_of_order_event" in alert_types_for_sequence(sensors["out_of_order"])
    assert "missing_timestamp" in alert_types_for_sequence(sensors["missing_timestamp"])
    assert "unexpected_low_repeat" in alert_types_for_sequence(sensors["unexpected_low_repeat"])
    assert "unexpected_high_without_low" in alert_types_for_sequence(sensors["unexpected_high_without_low"])
    assert "implausible_drain_time" in alert_types_for_sequence(sensors["implausible_drain"])


def test_valid_sensor_fallback_cycle_fixture():
    cycles = extract_filling_cycles(
        parse_event(item)
        for item in load_fixture()["sensor_events"]["valid_cycle_with_sensor_fallback"]
    )

    assert len(cycles) == 1
    assert cycles[0]["start_source"] == "sensor_low_fallback"
    assert cycles[0]["fill_time_seconds"] == 480


def test_command_fixture_confirmed_start_creates_cycle():
    fixture = load_fixture()
    command = parse_event(fixture["command_events"]["valid_confirmed_start"])
    end_event = {
        "event_id": "sensores/end",
        "sensor": "alto",
        "estado": "subiu",
        "timestamp": BASE + timedelta(seconds=480),
        "device_id": command["device_id"],
    }

    tracker = FillingCycleTracker()
    tracker.process_command_event(command)
    cycle_created = tracker.process_event(end_event)

    assert cycle_created is not None
    assert cycle_created["start_event_id"] == "comandos/valid-start"
    assert cycle_created["start_source"] == "pump_command_confirmed"
    assert cycle_created["fill_time_seconds"] == 480


def test_command_fixtures_ignore_not_applied_or_unconfirmed_starts():
    commands = load_fixture()["command_events"]
    end_event = {
        "event_id": "sensores/end",
        "sensor": "alto",
        "estado": "subiu",
        "timestamp": BASE + timedelta(seconds=480),
        "device_id": "esp32-reservatorio-01",
    }

    for key in ("requested_not_applied", "applied_unconfirmed", "overridden_by_priority"):
        tracker = FillingCycleTracker()
        tracker.process_command_event(parse_event(commands[key]))
        assert tracker.process_event(end_event) is None
