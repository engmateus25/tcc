import os
from datetime import datetime
from typing import Any, Dict, Iterable, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
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
            y = _draw_alert_item(c, y, alert, height, margin)

    y = _ensure_space(c, y, height, margin, 75)
    y = _draw_section_title(c, y, "Observacoes", height, margin)
    notes = [
        "Consumo de agua e estimado por ciclos validos de enchimento.",
        "Energia considera apenas eventos de bomba aplicados e confirmados.",
        "Comandos sobrepostos por prioridade ficam auditados, mas nao entram no tempo ligado.",
    ]
    for note in notes:
        y = _draw_wrapped_text(
            c,
            f"- {note}",
            margin,
            y,
            A4[0] - (2 * margin),
            height,
            margin,
            font_name="Helvetica",
            font_size=9,
            leading=12,
            color=colors.HexColor("#334155"),
        )
        y -= 2

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
        y = _ensure_space(c, y, height, margin, 26)
        c.setStrokeColor(colors.HexColor("#e2e8f0"))
        c.line(margin + 15, y - 4, A4[0] - margin - 15, y - 4)
        y = _draw_wrapped_text(
            c,
            f"- {key}: {value}",
            margin + 15,
            y,
            A4[0] - (2 * margin) - 30,
            height,
            margin,
            font_name="Helvetica",
            font_size=10,
            leading=13,
            color=colors.HexColor("#334155"),
        )
        y -= 2
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


def _draw_alert_item(c, y, alert, height, margin):
    page_width = A4[0]
    max_width = page_width - (2 * margin) - 24
    severity = str(alert.get("severity") or "-")
    status = str(alert.get("status") or "-")
    title = str(alert.get("title") or alert.get("type") or "Alerta")
    message = str(alert.get("message") or "Sem descricao.")
    detected_at = alert.get("detected_at") or alert.get("sensor_timestamp") or ""
    causes = alert.get("possible_causes") or []
    causes_text = ""
    if causes:
        causes_text = "Possiveis causas: " + ", ".join(str(item) for item in causes[:3])

    title_lines = _wrap_text(title, "Helvetica-Bold", 10, max_width)
    body_lines = _wrap_text(
        f"{severity}/{status}: {message}",
        "Helvetica",
        9,
        max_width,
    )
    timestamp_lines = _wrap_text(
        f"Referencia temporal: {detected_at}" if detected_at else "Referencia temporal: nao informada",
        "Helvetica",
        8,
        max_width,
    )
    causes_lines = _wrap_text(causes_text, "Helvetica", 8, max_width) if causes_text else []
    block_height = (
        16
        + len(title_lines) * 12
        + len(body_lines) * 11
        + len(timestamp_lines) * 10
        + len(causes_lines) * 10
    )

    y = _ensure_space(c, y, height, margin, min(block_height, height - (2 * margin)))
    top = y + 3
    c.setStrokeColor(_severity_border_color(severity))
    c.setLineWidth(2)
    c.line(margin, top, margin, max(margin, top - min(block_height - 4, 90)))
    c.setFillColor(_severity_color(severity))
    c.roundRect(margin + 7, y - 15, page_width - (2 * margin) - 7, 19, 4, fill=True, stroke=False)

    y = _draw_wrapped_text(
        c,
        title,
        margin + 16,
        y - 8,
        max_width,
        height,
        margin,
        font_name="Helvetica-Bold",
        font_size=10,
        leading=12,
        color=colors.HexColor("#111827"),
    )
    y -= 3
    y = _draw_wrapped_text(
        c,
        f"{severity}/{status}: {message}",
        margin + 16,
        y,
        max_width,
        height,
        margin,
        font_name="Helvetica",
        font_size=9,
        leading=11,
        color=colors.HexColor("#334155"),
    )
    y -= 1
    y = _draw_wrapped_text(
        c,
        f"Referencia temporal: {detected_at}" if detected_at else "Referencia temporal: nao informada",
        margin + 16,
        y,
        max_width,
        height,
        margin,
        font_name="Helvetica",
        font_size=8,
        leading=10,
        color=colors.HexColor("#64748b"),
    )
    if causes_text:
        y = _draw_wrapped_text(
            c,
            causes_text,
            margin + 16,
            y,
            max_width,
            height,
            margin,
            font_name="Helvetica",
            font_size=8,
            leading=10,
            color=colors.HexColor("#64748b"),
        )
    return y - 10


def _draw_wrapped_text(
    c,
    text: str,
    x: float,
    y: float,
    max_width: float,
    height: float,
    margin: float,
    *,
    font_name: str,
    font_size: int,
    leading: int,
    color,
):
    c.setFont(font_name, font_size)
    c.setFillColor(color)
    for line in _wrap_text(str(text), font_name, font_size, max_width):
        y = _ensure_space(c, y, height, margin, leading + 2)
        c.setFont(font_name, font_size)
        c.setFillColor(color)
        c.drawString(x, y, line)
        y -= leading
    return y


def _wrap_text(text: str, font_name: str, font_size: int, max_width: float):
    lines = []
    for paragraph in str(text).splitlines() or [""]:
        words = paragraph.split()
        current = ""
        for word in words:
            candidates = _split_word_for_width(word, font_name, font_size, max_width)
            for candidate in candidates:
                proposed = candidate if not current else f"{current} {candidate}"
                if pdfmetrics.stringWidth(proposed, font_name, font_size) <= max_width:
                    current = proposed
                    continue
                if current:
                    lines.append(current)
                current = candidate
        if current:
            lines.append(current)
        elif not words:
            lines.append("")
    return lines or [""]


def _split_word_for_width(word: str, font_name: str, font_size: int, max_width: float):
    if pdfmetrics.stringWidth(word, font_name, font_size) <= max_width:
        return [word]
    pieces = []
    current = ""
    for char in word:
        proposed = current + char
        if current and pdfmetrics.stringWidth(proposed, font_name, font_size) > max_width:
            pieces.append(current)
            current = char
        else:
            current = proposed
    if current:
        pieces.append(current)
    return pieces


def _severity_color(severity: str):
    if severity in ("critical", "error"):
        return colors.HexColor("#fee2e2")
    if severity == "warning":
        return colors.HexColor("#fef3c7")
    return colors.HexColor("#dbeafe")


def _severity_border_color(severity: str):
    if severity in ("critical", "error"):
        return colors.HexColor("#dc2626")
    if severity == "warning":
        return colors.HexColor("#d97706")
    return colors.HexColor("#2563eb")
