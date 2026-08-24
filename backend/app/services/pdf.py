import os
from datetime import datetime
from typing import Any, Dict, Iterable, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

OUTPUT_DIR = os.getenv("PDF_OUTPUT_DIR", "./generated")

def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_report_pdf(
    period: str,
    summary: Dict,
    *,
    water_consumption: Optional[Dict[str, Any]] = None,
    pump_energy: Optional[Dict[str, Any]] = None,
    alerts: Optional[Iterable[Dict[str, Any]]] = None,
) -> str:
    ensure_output_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"relatorio_{period}_{ts}.pdf"
    path = os.path.join(OUTPUT_DIR, filename)

    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4
    margin = 50
    y = height - margin

    c.setFillColor(colors.HexColor("#0f766e"))
    c.roundRect(margin, y - 72, width - (2 * margin), 72, 8, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin + 18, y - 26, "AquaMonitor")
    c.setFont("Helvetica", 10)
    c.drawString(margin + 18, y - 45, "Relatorio operacional do reservatorio")
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(width - margin - 18, y - 26, f"Periodo: {period}")
    c.setFont("Helvetica", 9)
    c.drawRightString(
        width - margin - 18,
        y - 45,
        f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
    )
    y -= 95

    y = _draw_section_title(c, y, "Resumo de sensores", height, margin)
    y = _draw_metric_grid(
        c,
        y,
        height,
        margin,
        [
            ("Eventos", summary.get("total_events", 0), "#2563eb"),
            ("Sensores", len(summary.get("by_sensor", {}) or {}), "#0f766e"),
            ("Acoes", len(summary.get("by_action", {}) or {}), "#7c3aed"),
        ],
    )

    y = _draw_kv_block(c, y, "Eventos por sensor", summary.get("by_sensor", {}), height, margin)
    y = _draw_kv_block(c, y, "Eventos por acao", summary.get("by_action", {}), height, margin)

    if water_consumption:
        y = _ensure_space(c, y, height, margin, 125)
        y = _draw_section_title(c, y, "Consumo estimado de agua", height, margin)
        water_rows = {
            "Ciclos validos": water_consumption.get("cycle_count", 0),
            "Volume estimado": f"{water_consumption.get('total_liters', 0):.1f} L",
            "Media diaria": f"{water_consumption.get('average_liters_per_day', 0):.1f} L/dia",
            "Custo estimado": f"R$ {water_consumption.get('total_cost_brl', 0):.2f}",
            "Volume por ciclo": f"{water_consumption.get('volume_between_sensors_liters', 0):.1f} L",
        }
        y = _draw_metric_grid(
            c,
            y,
            height,
            margin,
            [
                ("Ciclos", water_rows["Ciclos validos"], "#2563eb"),
                ("Volume", water_rows["Volume estimado"], "#0891b2"),
                ("Custo", water_rows["Custo estimado"], "#16a34a"),
            ],
        )
        y = _draw_kv_block(c, y, "", water_rows, height, margin)

    if pump_energy:
        y = _ensure_space(c, y, height, margin, 135)
        y = _draw_section_title(c, y, "Energia estimada da bomba", height, margin)
        energy_rows = {
            "Eventos confirmados": pump_energy.get("confirmed_event_count", 0),
            "Comandos ignorados": pump_energy.get("ignored_event_count", 0),
            "Tempo ligado": f"{pump_energy.get('total_on_minutes', 0):.1f} min",
            "Energia": f"{pump_energy.get('total_kwh', 0):.3f} kWh",
            "Custo estimado": f"R$ {pump_energy.get('total_cost_brl', 0):.2f}",
            "Potencia configurada": f"{pump_energy.get('pump_power_kw', 0):.3f} kW",
        }
        y = _draw_metric_grid(
            c,
            y,
            height,
            margin,
            [
                ("Tempo", energy_rows["Tempo ligado"], "#ca8a04"),
                ("Energia", energy_rows["Energia"], "#2563eb"),
                ("Custo", energy_rows["Custo estimado"], "#16a34a"),
            ],
        )
        y = _draw_kv_block(c, y, "", energy_rows, height, margin)

    if alerts is not None:
        y = _ensure_space(c, y, height, margin, 95)
        y = _draw_section_title(c, y, "Alertas recentes", height, margin)
        alerts_list = list(alerts)
        if not alerts_list:
            c.setFont("Helvetica", 10)
            c.drawString(margin, y, "Nenhum alerta no periodo consultado.")
            y -= 16
        for alert in alerts_list[:10]:
            y = _ensure_space(c, y, height, margin, 36)
            severity = str(alert.get("severity") or "-")
            c.setFillColor(_severity_color(severity))
            c.roundRect(margin, y - 26, width - (2 * margin), 28, 4, fill=True, stroke=False)
            c.setFillColor(colors.HexColor("#111827"))
            c.setFont("Helvetica-Bold", 10)
            c.drawString(margin + 10, y - 9, _clip(str(alert.get("title") or alert.get("type") or "Alerta"), 72))
            y -= 13
            c.setFont("Helvetica", 9)
            c.drawString(
                margin + 10,
                y,
                _clip(
                    f"{alert.get('severity', '-')}/{alert.get('status', '-')}: "
                    f"{alert.get('message', '')}",
                    100,
                ),
            )
            y -= 15

    y = _ensure_space(c, y, height, margin, 75)
    y = _draw_section_title(c, y, "Observacoes", height, margin)
    c.setFont("Helvetica", 9)
    notes = [
        "Consumo de agua e estimado por ciclos validos de enchimento.",
        "Energia considera apenas eventos de bomba aplicados e confirmados.",
        "Comandos sobrepostos por prioridade ficam auditados, mas nao entram no tempo ligado.",
    ]
    for note in notes:
        c.drawString(margin, y, f"- {note}")
        y -= 13

    c.showPage()
    c.save()
    return path


def _draw_section_title(c, y, title, height, margin):
    y = _ensure_space(c, y, height, margin, 35)
    c.setFillColor(colors.HexColor("#e0f2fe"))
    c.roundRect(margin, y - 20, A4[0] - (2 * margin), 24, 4, fill=True, stroke=False)
    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 13)
    c.drawString(margin + 10, y - 12, title)
    y -= 18
    return y


def _draw_kv_block(c, y, title, items, height, margin):
    if title:
        y = _ensure_space(c, y, height, margin, 35)
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(colors.HexColor("#334155"))
        c.drawString(margin, y, title)
        y -= 16
    if not items:
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.HexColor("#64748b"))
        c.drawString(margin + 15, y, "Sem dados.")
        return y - 16
    c.setFont("Helvetica", 10)
    for key, value in items.items():
        y = _ensure_space(c, y, height, margin, 20)
        c.setStrokeColor(colors.HexColor("#e2e8f0"))
        c.line(margin + 15, y - 4, A4[0] - margin - 15, y - 4)
        c.setFillColor(colors.HexColor("#334155"))
        c.drawString(margin + 15, y, f"- {key}: {value}")
        y -= 14
    return y - 6


def _draw_metric_grid(c, y, height, margin, metrics):
    y = _ensure_space(c, y, height, margin, 70)
    page_width = A4[0]
    gap = 10
    card_width = (page_width - (2 * margin) - (gap * (len(metrics) - 1))) / len(metrics)
    card_height = 48
    for index, (label, value, color) in enumerate(metrics):
        x = margin + index * (card_width + gap)
        c.setFillColor(colors.HexColor(color))
        c.roundRect(x, y - card_height, card_width, card_height, 6, fill=True, stroke=False)
        c.setFillColor(colors.white)
        c.setFont("Helvetica", 8)
        c.drawString(x + 10, y - 16, str(label))
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x + 10, y - 34, _clip(str(value), 22))
    return y - card_height - 16


def _ensure_space(c, y, height, margin, required):
    if y >= margin + required:
        return y
    c.showPage()
    return height - margin


def _clip(text: str, max_len: int) -> str:
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def _severity_color(severity: str):
    if severity in ("critical", "error"):
        return colors.HexColor("#fee2e2")
    if severity == "warning":
        return colors.HexColor("#fef3c7")
    return colors.HexColor("#dbeafe")
