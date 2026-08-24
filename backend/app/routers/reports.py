from datetime import timedelta

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
from app.services.alerts_store import list_alerts
from app.services.consumption import get_consumption_summary
from app.services.energy import get_energy_summary
from app.services.firestore import _get_period_range, fetch_sensor_events, build_summary
from app.services.pdf import generate_report_pdf

router = APIRouter()
PERIOD_PATTERN = "^(7d|30d|90d)$"


def build_report_payload(period: str):
    events = fetch_sensor_events(period=period)
    payload = {
        "period": period,
        "sensor_summary": build_summary(events),
        "water_consumption": get_consumption_summary(period, sensor_events=events),
        "pump_energy": get_energy_summary(period),
        "alerts": list_alerts(period=period, status=None, severity=None, limit=10),
    }
    return _fill_report_daily_series(payload, period)


def _fill_report_daily_series(payload: dict, period: str) -> dict:
    keys = _daily_keys(period)
    _fill_daily(
        payload["water_consumption"],
        keys,
        {"cycles": 0, "liters": 0.0, "cost_brl": 0.0},
    )
    _fill_daily(
        payload["pump_energy"],
        keys,
        {"on_seconds": 0.0, "kwh": 0.0, "cost_brl": 0.0},
    )
    return payload


def _fill_daily(summary: dict, keys: list[str], defaults: dict) -> None:
    current = {
        item.get("date"): item
        for item in summary.get("daily", [])
        if isinstance(item, dict) and item.get("date")
    }
    summary["daily"] = [
        {"date": key, **defaults, **current.get(key, {})}
        for key in keys
    ]


def _daily_keys(period: str) -> list[str]:
    _, end = _get_period_range(period)
    text = (period or "").strip().lower()
    if text.endswith("d") and text[:-1].isdigit():
        days = max(1, int(text[:-1]))
    else:
        start, _ = _get_period_range(period)
        days = max(1, (end.date() - start.date()).days + 1)

    first_day = end.date() - timedelta(days=days - 1)
    return [
        (first_day + timedelta(days=offset)).isoformat()
        for offset in range(days)
    ]


@router.get("/summary")
def report_summary(period: str = Query("7d", pattern=PERIOD_PATTERN)):
    return build_report_payload(period)


@router.get("/weekly")
def weekly_report(period: str = Query("7d", pattern=PERIOD_PATTERN)):
    payload = build_report_payload(period)
    pdf_path = generate_report_pdf(
        period,
        payload["sensor_summary"],
        water_consumption=payload["water_consumption"],
        pump_energy=payload["pump_energy"],
        alerts=payload["alerts"],
    )
    return FileResponse(pdf_path, media_type="application/pdf", filename=pdf_path.split("/")[-1])


@router.get("/monthly")
def monthly_report():
    payload = build_report_payload("30d")
    pdf_path = generate_report_pdf(
        "30d",
        payload["sensor_summary"],
        water_consumption=payload["water_consumption"],
        pump_energy=payload["pump_energy"],
        alerts=payload["alerts"],
    )
    return FileResponse(pdf_path, media_type="application/pdf", filename=pdf_path.split("/")[-1])
