from app.routers import reports


def test_report_payload_fills_empty_daily_series(monkeypatch):
    monkeypatch.setattr(reports, "fetch_sensor_events", lambda period: [])
    monkeypatch.setattr(
        reports,
        "build_summary",
        lambda events: {
            "total_events": 0,
            "by_sensor": {},
            "by_action": {},
        },
    )
    monkeypatch.setattr(
        reports,
        "get_consumption_summary",
        lambda period, sensor_events=None: {
            "period": period,
            "cycle_count": 0,
            "volume_between_sensors_liters": 500.0,
            "total_liters": 0.0,
            "total_cubic_meters": 0.0,
            "water_price_per_cubic_meter_brl": 8.0,
            "total_cost_brl": 0.0,
            "average_liters_per_day": 0.0,
            "daily": [],
            "estimated": True,
            "basis": "sensor_events_fallback",
        },
    )
    monkeypatch.setattr(
        reports,
        "get_energy_summary",
        lambda period: {
            "period": period,
            "pump_power_kw": 0.75,
            "electricity_price_per_kwh_brl": 0.656,
            "total_on_seconds": 0.0,
            "total_on_minutes": 0.0,
            "total_on_hours": 0.0,
            "total_kwh": 0.0,
            "total_cost_brl": 0.0,
            "confirmed_event_count": 0,
            "ignored_event_count": 0,
            "daily": [],
            "estimated": True,
            "basis": "confirmed_pump_command_events",
        },
    )
    monkeypatch.setattr(reports, "list_alerts", lambda **kwargs: [])

    payload = reports.build_report_payload("7d")

    assert len(payload["water_consumption"]["daily"]) == 7
    assert len(payload["pump_energy"]["daily"]) == 7
    assert payload["water_consumption"]["daily"][0]["liters"] == 0.0
    assert payload["pump_energy"]["daily"][0]["kwh"] == 0.0
