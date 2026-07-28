import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.schemas.dto import AquaIntent, ChatMessage
from app.services.alerts_store import list_alerts
from app.services.consumption import get_consumption_summary
from app.services.energy import get_energy_summary
from app.services.firestore import fetch_sensor_events
from app.services.llm import LLMProviderError, chat as llm_chat


AGENT_SYSTEM_PROMPT = """
Voce e o assistente analitico do AquaMonitor, um sistema de TCC para monitoramento
e controle de reservatorio de agua.

Responda em portugues do Brasil. Voce pode interpretar a pergunta livremente, mas
deve usar somente os dados estruturados fornecidos no prompt. Nao invente contagens,
custos, tempos, alertas ou estados de bomba. Quando houver poucos dados, diga isso
com clareza. Sempre indique o periodo analisado e a base usada para a resposta.

Se a pergunta for fora do dominio do AquaMonitor, responda brevemente e redirecione
para perguntas sobre sensores, caixa vazia/cheia, alertas, consumo de agua, energia
da bomba, custos e relatorios.
""".strip()


@dataclass
class AgentResult:
    answer: str
    intent: AquaIntent
    provider: Optional[str] = None
    model: Optional[str] = None
    usage: Optional[Any] = None
    fallback_used: bool = False
    llm_error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def parse_period_from_text(text: str) -> str:
    t = text.lower()

    if "hoje" in t:
        return "1d"

    hours = re.search(r"(\d+)\s*horas?", t)
    if hours:
        return f"{hours.group(1)}h"

    days = re.search(r"(\d+)\s*dias?", t)
    if days:
        return f"{days.group(1)}d"

    if "sete dias" in t:
        return "7d"
    if "vinte dias" in t:
        return "20d"
    if "trinta dias" in t:
        return "30d"
    if "noventa dias" in t:
        return "90d"

    if any(term in t for term in ("essa semana", "nesta semana", "nessa semana", "esta semana")):
        return "this_week"

    if any(
        term in t
        for term in (
            "nesse mês",
            "neste mês",
            "esse mês",
            "este mês",
            "nesse ultimo mês",
            "nesse último mês",
            "neste ultimo mês",
            "neste último mês",
        )
    ):
        return "this_month"

    if "últimos dias" in t or "ultimos dias" in t:
        return "7d"

    return "7d"


def period_human_label(period: str) -> str:
    p = (period or "").lower()
    if p.endswith("d") and p[:-1].isdigit():
        days = int(p[:-1])
        return "no ultimo dia" if days == 1 else f"nos ultimos {days} dias"
    if p.endswith("h") and p[:-1].isdigit():
        hours = int(p[:-1])
        return "na ultima hora" if hours == 1 else f"nas ultimas {hours} horas"
    if p == "this_week":
        return "nesta semana"
    if p == "this_month":
        return "neste mes"
    return f"no periodo {period}"


def detect_intent(question: str) -> AquaIntent:
    q = question.lower().strip()
    period = parse_period_from_text(question)

    if _contains_any(
        q,
        [
            "quem é você",
            "quem é vc",
            "quem e vc",
            "quem e você",
            "qual o seu nome",
            "qual é o seu nome",
            "o que você faz",
            "o que vc faz",
            "quem é o aquamonitor",
            "quem é o assistente",
        ],
    ):
        return AquaIntent(kind="smalltalk", period=period)

    if _contains_any(q, ["energia", "kwh", "quilowatt", "custo da bomba", "bomba consumiu"]):
        return AquaIntent(kind="energy_consumption", period=period)

    if _contains_any(q, ["consumo de água", "consumo de agua", "litros", "m³", "metro cúbico", "metro cubico", "custo da água", "custo da agua"]):
        return AquaIntent(kind="water_consumption", period=period)

    if _contains_any(q, ["alerta", "alertas", "alarme", "alarmes", "anomalia", "anomalias"]):
        if _contains_any(q, ["sensor", "sensores", "sequencia", "sequência", "inconsist"]):
            return AquaIntent(kind="health_check", period=period)
        return AquaIntent(kind="alerts_summary", period=period)

    if _contains_any(q, ["inconsist", "problema nos sensores", "erro de sensor", "estranho"]):
        return AquaIntent(kind="health_check", period=period)

    asks_count = "quantas vezes" in q or "quanto(s)" in q or "quantidade" in q
    asks_duration = "quanto tempo" in q or "duração" in q or "duracao" in q
    mentions_empty = "vazia" in q or "vazio" in q or "baixo" in q
    mentions_full = "cheia" in q or "cheio" in q or "alto" in q

    if asks_count and asks_duration and mentions_empty:
        return AquaIntent(kind="count_and_duration_empty", period=period, sensor="baixo")
    if asks_count and asks_duration and mentions_full:
        return AquaIntent(kind="count_and_duration_full", period=period, sensor="alto")
    if asks_count and mentions_empty and mentions_full:
        return AquaIntent(kind="count_empty_and_full", period=period)
    if asks_count and mentions_empty:
        return AquaIntent(kind="count_low", period=period, sensor="baixo", estado="desceu")
    if asks_count and mentions_full:
        return AquaIntent(kind="count_full", period=period, sensor="alto", estado="subiu")
    if asks_duration and mentions_empty:
        return AquaIntent(kind="duration_empty", period=period, sensor="baixo")
    if asks_duration and mentions_full:
        return AquaIntent(kind="duration_full", period=period, sensor="alto")

    if "resumo" in q or "eventos" in q or "relatório" in q or "relatorio" in q:
        return AquaIntent(kind="summary_all", period=period)

    return AquaIntent(kind="unknown", period=period)


def handle_analytics_question(
    question: str,
    *,
    history: Optional[List[Dict[str, Any]]] = None,
    provider_name: Optional[str] = None,
) -> AgentResult:
    intent = detect_intent(question)
    context = build_agent_context(question, intent)
    deterministic_answer = build_deterministic_answer(intent, context)
    response_mode = os.getenv("AGENT_RESPONSE_MODE", "hybrid").strip().lower()

    if response_mode == "deterministic":
        return AgentResult(
            answer=deterministic_answer,
            intent=intent,
            fallback_used=True,
            metadata=context,
        )

    try:
        llm_answer, meta = compose_answer_with_llm(
            question,
            intent,
            context,
            deterministic_answer,
            history or [],
            provider_name=provider_name,
        )
        return AgentResult(
            answer=llm_answer,
            intent=intent,
            provider=meta.get("provider"),
            model=meta.get("model"),
            usage=meta.get("usage"),
            fallback_used=False,
            metadata=context,
        )
    except LLMProviderError as exc:
        if response_mode == "llm" and not _env_bool("AGENT_ALLOW_DETERMINISTIC_FALLBACK", True):
            raise
        return AgentResult(
            answer=deterministic_answer,
            intent=intent,
            provider=exc.provider,
            model=exc.model,
            fallback_used=True,
            llm_error=exc.message,
            metadata=context,
        )


def build_agent_context(question: str, intent: AquaIntent) -> Dict[str, Any]:
    period = intent.period or parse_period_from_text(question)
    label = period_human_label(period)
    errors: Dict[str, str] = {}

    events = _safe_fetch("sensor_events", lambda: fetch_sensor_events(period), [], errors)
    summary = _compute_summary(events)
    empty_count = _count_event(events, "baixo", "desceu")
    full_count = _count_event(events, "alto", "subiu")
    empty_seconds = _duration_for_sensor_state(events, "baixo", "desceu", "subiu")
    full_seconds = _duration_for_sensor_state(events, "alto", "subiu", "desceu")

    water = _safe_fetch("water_consumption", lambda: get_consumption_summary(period), None, errors)
    energy = _safe_fetch("pump_energy", lambda: get_energy_summary(period), None, errors)
    alerts = _safe_fetch("alerts", lambda: list_alerts(period=period, status="open", limit=10), [], errors)

    context: Dict[str, Any] = {
        "question": question,
        "period": period,
        "period_label": label,
        "intent": intent.model_dump(),
        "sensor_summary": summary,
        "empty_count": empty_count,
        "full_count": full_count,
        "empty_duration_seconds": empty_seconds,
        "empty_duration_label": _format_duration(empty_seconds),
        "full_duration_seconds": full_seconds,
        "full_duration_label": _format_duration(full_seconds),
        "water_consumption": water,
        "pump_energy": energy,
        "open_alerts": [_alert_for_prompt(alert) for alert in alerts],
        "data_errors": errors,
        "data_basis": {
            "sensor_events": "Firestore sensores",
            "water_consumption": "Firestore filling_cycles",
            "pump_energy": "Firestore comandos confirmados",
            "alerts": "Firestore alerts abertas",
        },
    }

    if _env_bool("AGENT_SEND_RAW_EVENTS_TO_LLM", False):
        context["recent_sensor_events"] = [_event_for_prompt(e) for e in events[-12:]]

    return _json_safe(context)


def compose_answer_with_llm(
    question: str,
    intent: AquaIntent,
    context: Dict[str, Any],
    deterministic_answer: str,
    history: List[Dict[str, Any]],
    *,
    provider_name: Optional[str],
) -> tuple[str, Dict[str, Any]]:
    prompt_context = {
        "intent": intent.model_dump(),
        "facts": context,
        "deterministic_baseline_answer": deterministic_answer,
        "recent_chat_history": _history_for_prompt(history),
    }

    messages = [
        ChatMessage(role="system", content=AGENT_SYSTEM_PROMPT),
        ChatMessage(
            role="user",
            content=(
                "Pergunta atual do usuario:\n"
                f"{question}\n\n"
                "Contexto estruturado disponivel para resposta:\n"
                f"{json.dumps(prompt_context, ensure_ascii=False, indent=2)}\n\n"
                "Responda de forma natural, mas fiel aos dados."
            ),
        ),
    ]
    content, meta = llm_chat(messages, stream=False, provider_name=provider_name)
    text = str(content).strip()
    if not text:
        raise LLMProviderError(
            "LLM retornou resposta vazia.",
            provider=str(meta.get("provider") or provider_name or "unknown"),
            model=meta.get("model"),
            status_code=502,
        )
    return text, meta


def build_deterministic_answer(intent: AquaIntent, context: Dict[str, Any]) -> str:
    label = context["period_label"]
    errors = context.get("data_errors") or {}
    if intent.kind == "smalltalk":
        return (
            "Eu sou o assistente de IA do AquaMonitor. Analiso eventos dos sensores, "
            "alertas, consumo de agua, energia da bomba e relatorios do reservatorio."
        )

    if errors.get("sensor_events") and intent.kind not in ("water_consumption", "energy_consumption", "alerts_summary"):
        return f"Nao consegui acessar os eventos de sensores para responder {label}: {errors['sensor_events']}"

    if intent.kind == "summary_all":
        summary = context["sensor_summary"]
        return (
            f"Resumo {label}: {summary['total']} evento(s) de sensores. "
            f"Por sensor: {_format_dict(summary['by_sensor'])}. "
            f"Por estado: {_format_dict(summary['by_estado'])}."
        )

    if intent.kind == "summary_low":
        summary = context["sensor_summary"]
        low = summary["by_sensor"].get("baixo", 0)
        return f"Resumo do sensor baixo {label}: {low} evento(s) registrados."

    if intent.kind == "count_events_all":
        return f"{label}, foram registrados {context['sensor_summary']['total']} evento(s) de sensores."

    if intent.kind == "count_low":
        return f"{label}, a caixa ficou vazia {context['empty_count']} vez(es), usando baixo=desceu como criterio."

    if intent.kind == "count_full":
        return f"{label}, a caixa ficou cheia {context['full_count']} vez(es), usando alto=subiu como criterio."

    if intent.kind == "count_empty_and_full":
        return (
            f"{label}, a caixa ficou vazia {context['empty_count']} vez(es) "
            f"e cheia {context['full_count']} vez(es)."
        )

    if intent.kind == "duration_empty":
        return f"{label}, a caixa ficou vazia por aproximadamente {context['empty_duration_label']}."

    if intent.kind == "duration_full":
        return f"{label}, a caixa ficou cheia por aproximadamente {context['full_duration_label']}."

    if intent.kind == "count_and_duration_empty":
        return (
            f"{label}, a caixa ficou vazia {context['empty_count']} vez(es) "
            f"e permaneceu vazia por cerca de {context['empty_duration_label']}."
        )

    if intent.kind == "count_and_duration_full":
        return (
            f"{label}, a caixa ficou cheia {context['full_count']} vez(es) "
            f"e permaneceu cheia por cerca de {context['full_duration_label']}."
        )

    if intent.kind == "water_consumption":
        water = context.get("water_consumption")
        if not water:
            return f"Nao consegui calcular consumo de agua {label}: {errors.get('water_consumption', 'sem dados de ciclos')}."
        return (
            f"{label}, o consumo estimado foi de {water['total_liters']:.0f} L "
            f"em {water['cycle_count']} ciclo(s), media de {water['average_liters_per_day']:.0f} L/dia "
            f"e custo estimado de R$ {water['total_cost_brl']:.2f}."
        )

    if intent.kind == "energy_consumption":
        energy = context.get("pump_energy")
        if not energy:
            return f"Nao consegui calcular energia da bomba {label}: {errors.get('pump_energy', 'sem eventos confirmados')}."
        return (
            f"{label}, a bomba consumiu cerca de {energy['total_kwh']:.3f} kWh, "
            f"ficou ligada por {energy['total_on_minutes']:.0f} minuto(s) confirmados "
            f"e gerou custo estimado de R$ {energy['total_cost_brl']:.2f}."
        )

    if intent.kind == "alerts_summary":
        alerts = context.get("open_alerts") or []
        if not alerts:
            return f"{label}, nao ha alertas abertos retornados pela consulta."
        return f"{label}, ha {len(alerts)} alerta(s) aberto(s). Principal: {alerts[0].get('title') or alerts[0].get('type')}."

    if intent.kind == "health_check":
        summary = context["sensor_summary"]
        alerts = context.get("open_alerts") or []
        return (
            f"Consistencia dos sensores {label}: {summary['total']} evento(s), "
            f"baixo={summary['by_sensor'].get('baixo', 0)}, alto={summary['by_sensor'].get('alto', 0)}, "
            f"alertas abertos={len(alerts)}."
        )

    return (
        "Ainda nao entendi completamente a analise pedida. Posso responder sobre eventos, "
        "caixa vazia/cheia, alertas, consumo de agua, energia da bomba e relatorios por periodo."
    )


def _compute_summary(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_sensor: Dict[str, int] = {}
    by_estado: Dict[str, int] = {}
    for event in events:
        sensor = _clean_text(event.get("sensor"))
        estado = _clean_text(event.get("estado"))
        if sensor:
            by_sensor[sensor] = by_sensor.get(sensor, 0) + 1
        if estado:
            by_estado[estado] = by_estado.get(estado, 0) + 1
    return {
        "total": len(events),
        "by_sensor": by_sensor,
        "by_estado": by_estado,
    }


def _duration_for_sensor_state(
    events: List[Dict[str, Any]],
    sensor_target: str,
    state_down: str,
    state_up: str,
) -> float:
    ordered = sorted(
        [event for event in events if isinstance(event.get("timestamp"), datetime)],
        key=lambda event: event["timestamp"],
    )
    last_down_at: Optional[datetime] = None
    total_seconds = 0.0

    for event in ordered:
        sensor = _clean_text(event.get("sensor"))
        estado = _clean_text(event.get("estado"))
        timestamp = event["timestamp"]

        if sensor == sensor_target and estado == state_down:
            last_down_at = timestamp
        elif sensor == sensor_target and estado == state_up and last_down_at is not None:
            total_seconds += max(0.0, (timestamp - last_down_at).total_seconds())
            last_down_at = None

    return total_seconds


def _count_event(events: List[Dict[str, Any]], sensor: str, estado: str) -> int:
    return sum(
        1
        for event in events
        if _clean_text(event.get("sensor")) == sensor and _clean_text(event.get("estado")) == estado
    )


def _safe_fetch(label: str, func, fallback, errors: Dict[str, str]):
    try:
        return func()
    except Exception as exc:
        errors[label] = str(exc)
        return fallback


def _history_for_prompt(history: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    limit = _env_int("AGENT_MAX_HISTORY_MESSAGES", 8)
    cleaned = []
    for message in history[-limit:]:
        role = _clean_text(message.get("role"))
        content = message.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            cleaned.append({"role": role, "content": content.strip()[:1200]})
    return cleaned


def _event_for_prompt(event: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": event.get("id") or event.get("document_id"),
        "sensor": event.get("sensor"),
        "estado": event.get("estado"),
        "timestamp": _format_datetime(event.get("timestamp")),
        "device_id": event.get("device_id"),
    }


def _alert_for_prompt(alert: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": alert.get("id"),
        "type": alert.get("type"),
        "severity": alert.get("severity"),
        "title": alert.get("title"),
        "message": alert.get("message"),
        "sensor_timestamp": _format_datetime(alert.get("sensor_timestamp")),
        "possible_causes": alert.get("possible_causes") or [],
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return _format_datetime(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _format_datetime(value: Any) -> Optional[str]:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _format_duration(seconds: float) -> str:
    if seconds <= 0:
        return "0 minutos"
    minutes = int(seconds // 60)
    hours = minutes // 60
    minutes = minutes % 60
    days = hours // 24
    hours = hours % 24
    parts = []
    if days:
        parts.append(f"{days} dia(s)")
    if hours:
        parts.append(f"{hours} hora(s)")
    if minutes:
        parts.append(f"{minutes} minuto(s)")
    return " e ".join(parts) or "menos de 1 minuto"


def _format_dict(values: Dict[str, int]) -> str:
    if not values:
        return "sem registros"
    return ", ".join(f"{key}: {value}" for key, value in values.items())


def _contains_any(text: str, terms: List[str]) -> bool:
    return any(term in text for term in terms)


def _clean_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in ("1", "true", "sim", "yes", "on")


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default
