from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
from app.services.alerts_store import list_alerts
from app.services.consumption import get_consumption_summary
from app.services.energy import get_energy_summary
from app.services.firestore import fetch_sensor_events, build_summary
from app.services.pdf import generate_report_pdf

router = APIRouter()
PERIOD_PATTERN = "^(7d|30d|90d)$"


def build_report_payload(period: str):
    events = fetch_sensor_events(period=period)
    return {
        "period": period,
        "sensor_summary": build_summary(events),
        "water_consumption": get_consumption_summary(period),
        "pump_energy": get_energy_summary(period),
        "alerts": list_alerts(period=period, status=None, severity=None, limit=10),
    }


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
