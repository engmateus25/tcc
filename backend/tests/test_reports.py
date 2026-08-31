from app.routers import reports
from app.services import pdf


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


def test_generate_report_pdf_handles_long_alert_texts(monkeypatch, tmp_path):
    monkeypatch.setattr(pdf, "OUTPUT_DIR", str(tmp_path))
    long_message = (
        "Sensor alto subiu sem confirmacao previa do sensor baixo. "
        "Este texto simula uma descricao extensa de diagnostico, possiveis causas, "
        "orientacao operacional e contexto suficiente para validar quebra de linha."
    )
    alerts = [
        {
            "title": f"Alerta deterministico de intertravamento {index}",
            "severity": "warning",
            "status": "open",
            "message": long_message,
            "detected_at": "2026-08-31T12:00:00Z",
            "possible_causes": [
                "evento de baixo perdido",
                "boia baixa travada",
                "fios invertidos",
            ],
        }
        for index in range(8)
    ]

    for period in ("7d", "30d", "90d"):
        path = pdf.generate_report_pdf(
            period,
            {"total_events": 12, "by_sensor": {"baixo": 6, "alto": 6}, "by_action": {"subiu": 6, "desceu": 6}},
            water_consumption={
                "cycle_count": 3,
                "total_liters": 1500,
                "average_liters_per_day": 214.2,
                "total_cost_brl": 12.0,
                "volume_between_sensors_liters": 500,
            },
            pump_energy={
                "confirmed_event_count": 4,
                "ignored_event_count": 1,
                "total_on_minutes": 32,
                "total_kwh": 0.4,
                "total_cost_brl": 0.26,
                "pump_power_kw": 0.75,
            },
            alerts=alerts,
        )

        generated = tmp_path / path.split("/")[-1]
        assert generated.exists()
        assert generated.read_bytes().startswith(b"%PDF")
        assert generated.stat().st_size > 1000


def test_generate_report_pdf_handles_empty_alerts(monkeypatch, tmp_path):
    monkeypatch.setattr(pdf, "OUTPUT_DIR", str(tmp_path))

    path = pdf.generate_report_pdf(
        "7d",
        {"total_events": 0, "by_sensor": {}, "by_action": {}},
        water_consumption={"cycle_count": 0, "total_liters": 0},
        pump_energy={"confirmed_event_count": 0, "total_kwh": 0},
        alerts=[],
    )

    generated = tmp_path / path.split("/")[-1]
    assert generated.exists()
    assert generated.read_bytes().startswith(b"%PDF")
