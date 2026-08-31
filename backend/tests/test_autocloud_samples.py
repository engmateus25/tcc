from datetime import datetime, timedelta, timezone

from app.services.autocloud_fill_time import analyze_fill_time_cycle
from app.services.autocloud_samples import build_autocloud_sample_document


BASE = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)


def cycle(seconds, index=0):
    return {
        "cycle_id": f"cycle-{index}-{seconds}",
        "start_event_id": f"comandos/start-{index}",
        "end_event_id": f"sensores/end-{index}",
        "started_at": BASE + timedelta(minutes=index * 30),
        "low_raised_at": BASE + timedelta(minutes=index * 30, seconds=60),
        "ended_at": BASE + timedelta(minutes=index * 30, seconds=seconds),
        "fill_time_seconds": seconds,
        "low_to_high_seconds": seconds - 60,
        "pump_to_low_seconds": 60,
        "valid": True,
        "device_id": "esp32-reservatorio-01",
        "start_source": "pump_command_confirmed",
        "metadata": {
            "test_run_id": "pibiti-test",
            "scenario": "unit",
        },
    }


def test_build_autocloud_sample_document_keeps_cycle_and_vector_metadata():
    history = [cycle(seconds, index) for index, seconds in enumerate([470, 480, 485, 490, 475])]
    current = cycle(900, 10)
    analysis = analyze_fill_time_cycle(current, history, min_samples=5, slow_factor=1.5)

    document = build_autocloud_sample_document(
        current,
        analysis,
        source="test",
    )

    assert document["id"] == current["cycle_id"]
    assert document["fill_time_seconds"] == 900.0
    assert document["analysis_reason"] == "slow_fill_cycle"
    assert document["test_run_id"] == "pibiti-test"
    assert document["scenario"] == "unit"
    assert document["method"] == "autocloud_filling_cycle_clustering"
    assert document["raw_features"][0] == 900.0
    assert document["metadata"]["feature_metadata"]["feature_names"][0] == "fill_time_seconds"
