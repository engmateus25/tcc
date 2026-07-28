from datetime import datetime, timezone

from app.services.consumption import build_consumption_summary


def test_consumption_summary_uses_valid_cycles_and_liters_to_m3():
    summary = build_consumption_summary(
        [
            {"cycle_id": "a", "valid": True, "ended_at": datetime(2026, 7, 27, tzinfo=timezone.utc)},
            {"cycle_id": "b", "valid": True, "ended_at": datetime(2026, 7, 27, 1, tzinfo=timezone.utc)},
            {"cycle_id": "c", "valid": False, "ended_at": datetime(2026, 7, 27, 2, tzinfo=timezone.utc)},
        ],
        period="7d",
        volume_between_sensors_liters=500,
        water_price_per_cubic_meter_brl=8,
    )

    assert summary["cycle_count"] == 2
    assert summary["total_liters"] == 1000
    assert summary["total_cubic_meters"] == 1
    assert summary["total_cost_brl"] == 8
    assert summary["average_liters_per_day"] == 1000 / 7
    assert summary["daily"][0]["liters"] == 1000
