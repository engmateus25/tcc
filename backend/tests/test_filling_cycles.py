from datetime import datetime, timedelta, timezone

from app.services.autocloud_fill_time import analyze_fill_time_cycle
from app.services.filling_cycles import build_filling_cycle, extract_filling_cycles


BASE = datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc)


def event(event_id, sensor, estado, seconds):
    return {
        "event_id": event_id,
        "sensor": sensor,
        "estado": estado,
        "timestamp": BASE + timedelta(seconds=seconds),
    }


def cycle(duration, event_id="sensores/end"):
    return {
        "cycle_id": f"cycle-{duration}",
        "start_event_id": "sensores/start",
        "end_event_id": event_id,
        "started_at": BASE,
        "ended_at": BASE + timedelta(seconds=duration),
        "fill_time_seconds": duration,
        "valid": True,
    }


def test_extracts_low_to_high_filling_cycle():
    cycles = extract_filling_cycles(
        [
            event("sensores/empty", "baixo", "desceu", 0),
            event("sensores/start", "baixo", "subiu", 60),
            event("sensores/end", "alto", "subiu", 540),
        ]
    )

    assert len(cycles) == 1
    assert cycles[0]["start_event_id"] == "sensores/start"
    assert cycles[0]["end_event_id"] == "sensores/end"
    assert cycles[0]["fill_time_seconds"] == 480


def test_invalid_event_does_not_feed_cycle_extraction():
    cycles = extract_filling_cycles(
        [
            event("sensores/start", "baixo", "subiu", 0),
            event("sensores/end", "alto", "subiu", 480),
        ],
        invalid_event_ids={"sensores/start"},
    )

    assert cycles == []


def test_rejects_cycle_with_non_positive_duration():
    assert (
        build_filling_cycle(
            event("sensores/start", "baixo", "subiu", 60),
            event("sensores/end", "alto", "subiu", 30),
        )
        is None
    )


def test_fill_time_analysis_requires_minimum_samples():
    result = analyze_fill_time_cycle(
        cycle(480),
        [cycle(300), cycle(320)],
        min_samples=5,
    )

    assert result["used"] is False
    assert result["reason"] == "insufficient_data"


def test_fill_time_analysis_flags_slow_cycle():
    result = analyze_fill_time_cycle(
        cycle(900),
        [cycle(300), cycle(310), cycle(305), cycle(315), cycle(320)],
        min_samples=5,
        slow_factor=1.5,
    )

    assert result["used"] is True
    assert result["reason"] == "slow_fill_cycle"
    assert result["alert"]["type"] == "slow_fill_cycle"


def test_fill_time_analysis_flags_persistent_shift():
    result = analyze_fill_time_cycle(
        cycle(500),
        [cycle(300), cycle(320), cycle(340), cycle(380), cycle(430)],
        min_samples=5,
        slow_factor=1.5,
        persistent_window=3,
    )

    assert result["used"] is True
    assert result["reason"] == "persistent_fill_time_shift"
    assert result["alert"]["type"] == "persistent_fill_time_shift"
