from datetime import datetime, timedelta, timezone

from app.services.autocloud_core import (
    build_filling_cycle_feature_stats,
    run_autocloud_for_filling_cycle,
    vectorize_filling_cycle,
)
from app.services.autocloud_fill_time import analyze_fill_time_cycle


BASE = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)


def cycle(seconds, index=0, *, pump_to_low=60, start_source="pump_command_confirmed"):
    return {
        "cycle_id": f"cycle-{index}-{seconds}",
        "start_event_id": f"comandos/start-{index}",
        "end_event_id": f"sensores/end-{index}",
        "started_at": BASE + timedelta(minutes=index * 30),
        "low_raised_at": BASE + timedelta(minutes=index * 30, seconds=pump_to_low),
        "ended_at": BASE + timedelta(minutes=index * 30, seconds=seconds),
        "fill_time_seconds": seconds,
        "low_to_high_seconds": seconds - pump_to_low,
        "pump_to_low_seconds": pump_to_low,
        "valid": True,
        "device_id": "esp32-reservatorio-01",
        "start_source": start_source,
    }


def test_vectorizes_filling_cycle_timing_features():
    history = [cycle(seconds, index) for index, seconds in enumerate([470, 480, 485, 490, 475])]
    stats = build_filling_cycle_feature_stats(history)

    vector, metadata = vectorize_filling_cycle(cycle(482, 10), stats)

    assert vector.shape == (5,)
    assert metadata["feature_names"] == [
        "fill_time_seconds",
        "low_to_high_seconds",
        "pump_to_low_seconds",
        "start_source_score",
        "sensor_sequence_score",
    ]
    assert metadata["raw_features"] == [482.0, 422.0, 60.0, 1.0, 1.0]


def test_autocloud_core_reports_class_and_distance_for_cycle():
    history = [cycle(seconds, index) for index, seconds in enumerate([470, 480, 485, 490, 475])]

    result = run_autocloud_for_filling_cycle(cycle(482, 10), history, m=2.5)

    assert result["method"] == "autocloud_filling_cycle_clustering"
    assert result["training_samples"] == 5
    assert isinstance(result["class_index"], int)
    assert result["cloud_count"] >= 1
    assert result["feature_metadata"]["raw_features"] == [482.0, 422.0, 60.0, 1.0, 1.0]


def test_fill_time_analysis_uses_autocloud_metadata_and_flags_slow_cycle():
    history = [cycle(seconds, index) for index, seconds in enumerate([470, 480, 485, 490, 475])]

    result = analyze_fill_time_cycle(
        cycle(900, 10),
        history,
        min_samples=5,
        slow_factor=1.5,
        m=2.5,
    )

    assert result["reason"] == "slow_fill_cycle"
    assert result["method"] == "autocloud_filling_cycle_clustering"
    assert result["current_vs_median_seconds"] == 420
    assert result["current_vs_median_percent"] == 87.5
    assert result["alert"]["metadata"]["feature_metadata"]["raw_features"][0] == 900.0
    assert result["alert"]["metadata"]["baseline_median_seconds"] == 480
    assert result["alert"]["metadata"]["current_fill_time_seconds"] == 900
    assert result["alert"]["metadata"]["current_vs_median_seconds"] == 420
    assert result["alert"]["metadata"]["current_vs_median_percent"] == 87.5
    assert result["alert"]["metadata"]["slow_threshold_seconds"] == 720
    assert "Tempo observado: 15min 00s (900 s)." in result["alert"]["message"]
    assert "Mediana historica: 8min 00s (480 s)." in result["alert"]["message"]
    assert "Diferenca para a mediana: +7min 00s (+87,5%)." in result["alert"]["message"]
    assert "class_index" in result["alert"]["metadata"]
