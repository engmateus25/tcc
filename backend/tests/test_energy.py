from datetime import datetime, timedelta, timezone

from app.services import energy
from app.services.energy import build_energy_summary, normalize_pump_event


BASE = datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc)


def event(seconds, pump_on, *, confirmed=True, applied=True, overridden_by=None):
    return {
        "timestamp": BASE + timedelta(seconds=seconds),
        "pump_on": pump_on,
        "confirmed": confirmed,
        "applied": applied,
        "overridden_by": overridden_by,
    }


def test_energy_summary_uses_confirmed_applied_intervals(monkeypatch):
    monkeypatch.setattr(energy, "_get_period_range", lambda period: (BASE, BASE + timedelta(hours=2)))

    summary = build_energy_summary(
        [
            event(0, True),
            event(3600, False),
            event(5400, True, confirmed=True, applied=False, overridden_by="manual chave"),
        ],
        period="7d",
        pump_power_kw=0.75,
        electricity_price_per_kwh_brl=0.656,
    )

    assert summary["total_on_seconds"] == 3600
    assert summary["total_kwh"] == 0.75
    assert summary["total_cost_brl"] == 0.492
    assert summary["confirmed_event_count"] == 2
    assert summary["ignored_event_count"] == 1


def test_normalize_pump_event_reads_extended_command_contract():
    normalized = normalize_pump_event(
        {
            "command_id": "cmd-1",
            "timestamp": BASE,
            "requested_state": True,
            "applied_state": False,
            "confirmed": True,
            "applied": False,
            "source": "remoto",
            "overridden_by": "físico",
        },
        doc_id="doc-1",
    )

    assert normalized["command_id"] == "cmd-1"
    assert normalized["requested_state"] is True
    assert normalized["pump_on"] is False
    assert normalized["confirmed"] is True
    assert normalized["applied"] is False
    assert normalized["overridden_by"] == "físico"
