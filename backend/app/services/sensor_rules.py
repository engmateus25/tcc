import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class SensorRuleConfig:
    duplicate_window_seconds: int = 5
    out_of_order_tolerance_seconds: int = 2
    min_plausible_drain_time_seconds: int = 60


def load_rule_config() -> SensorRuleConfig:
    return SensorRuleConfig(
        duplicate_window_seconds=_env_int("SENSOR_DUPLICATE_WINDOW_SECONDS", 5),
        out_of_order_tolerance_seconds=_env_int(
            "SENSOR_OUT_OF_ORDER_TOLERANCE_SECONDS",
            2,
        ),
        min_plausible_drain_time_seconds=_env_int(
            "MIN_PLAUSIBLE_DRAIN_TIME_SECONDS",
            60,
        ),
    )


def evaluate_sensor_event_rules(
    event: Dict[str, Any],
    history: Iterable[Dict[str, Any]],
    config: Optional[SensorRuleConfig] = None,
) -> List[Dict[str, Any]]:
    config = config or load_rule_config()
    history_list = [
        item for item in history if _normalize_datetime(item.get("timestamp")) is not None
    ]
    history_list.sort(key=lambda item: _normalize_datetime(item.get("timestamp")))

    alerts: List[Dict[str, Any]] = []
    ts = _normalize_datetime(event.get("timestamp"))
    if event.get("timestamp_missing") or ts is None:
        return [
            _build_alert(
                event,
                "missing_timestamp",
                "error",
                "Evento de sensor sem timestamp",
                "O evento chegou sem timestamp confiavel e nao deve alimentar ciclos ou AutoCloud.",
                ["falha de NTP", "payload incompleto", "evento legado sem horario"],
                {"blocks_cycle_processing": True},
            )
        ]

    latest_event = history_list[-1] if history_list else None
    latest_ts = _normalize_datetime(latest_event.get("timestamp")) if latest_event else None
    if latest_ts and (latest_ts - ts).total_seconds() > config.out_of_order_tolerance_seconds:
        alerts.append(
            _build_alert(
                event,
                "out_of_order_event",
                "warning",
                "Evento fora de ordem cronologica",
                "O timestamp do evento e anterior ao ultimo evento processado.",
                ["atraso de rede", "reenvio antigo", "relogio do dispositivo incorreto"],
                {
                    "blocks_cycle_processing": True,
                    "last_timestamp": latest_ts,
                    "event_timestamp": ts,
                },
            )
        )

    sensor = _clean_text(event.get("sensor"))
    estado = _clean_text(event.get("estado"))
    same_previous = _latest_matching(
        history_list,
        lambda item: _clean_text(item.get("sensor")) == sensor
        and _clean_text(item.get("estado")) == estado,
    )
    same_previous_ts = (
        _normalize_datetime(same_previous.get("timestamp")) if same_previous else None
    )

    duplicate_detected = False
    if same_previous_ts:
        delta = abs((ts - same_previous_ts).total_seconds())
        if delta <= config.duplicate_window_seconds:
            duplicate_detected = True
            alerts.append(
                _build_alert(
                    event,
                    "duplicate_event",
                    "info",
                    "Evento de sensor possivelmente duplicado",
                    "O mesmo sensor repetiu o mesmo estado dentro da janela de duplicidade.",
                    ["bounce do sensor", "retry de rede", "documento repetido"],
                    {
                        "blocks_cycle_processing": True,
                        "previous_timestamp": same_previous_ts,
                        "delta_seconds": delta,
                    },
                )
            )

    state = _current_state(history_list)
    previous_low = _latest_matching(
        history_list,
        lambda item: _clean_text(item.get("sensor")) == "baixo",
    )
    previous_low_ts = (
        _normalize_datetime(previous_low.get("timestamp")) if previous_low else None
    )
    previous_high_up = _latest_matching(
        history_list,
        lambda item: _clean_text(item.get("sensor")) == "alto"
        and _clean_text(item.get("estado")) == "subiu",
    )
    previous_high_up_ts = (
        _normalize_datetime(previous_high_up.get("timestamp")) if previous_high_up else None
    )

    if sensor == "baixo" and estado == "desceu" and not duplicate_detected:
        if (
            previous_low
            and _clean_text(previous_low.get("estado")) == "desceu"
            and (
                previous_high_up_ts is None
                or (previous_low_ts and previous_high_up_ts < previous_low_ts)
            )
        ):
            alerts.append(
                _build_alert(
                    event,
                    "unexpected_low_repeat",
                    "warning",
                    "Sensor baixo repetiu antes do sensor alto",
                    "O sensor baixo voltou a indicar nivel baixo sem um fechamento de ciclo pelo sensor alto.",
                    ["leitura duplicada", "ruido na boia baixa", "evento de alto perdido"],
                    {
                        "blocks_cycle_processing": True,
                        "previous_low_timestamp": previous_low_ts,
                    },
                )
            )

        if previous_high_up_ts:
            drain_time = (ts - previous_high_up_ts).total_seconds()
            if 0 <= drain_time < config.min_plausible_drain_time_seconds:
                alerts.append(
                    _build_alert(
                        event,
                        "implausible_drain_time",
                        "warning",
                        "Esvaziamento rapido demais",
                        "O tempo entre nivel alto e nivel baixo ficou abaixo do minimo plausivel configurado.",
                        ["vazamento", "boia travada", "evento fora de ordem", "parametro minimo muito alto"],
                        {
                            "blocks_cycle_processing": True,
                            "drain_time_seconds": drain_time,
                            "min_plausible_drain_time_seconds": config.min_plausible_drain_time_seconds,
                        },
                    )
                )

    if sensor == "alto" and estado == "subiu":
        low_state = state.get("baixo")
        if low_state and low_state != "subiu":
            alerts.append(
                _build_alert(
                    event,
                    "unexpected_high_without_low",
                    "warning",
                    "Sensor alto subiu antes do sensor baixo",
                    "O sensor alto indicou nivel atingido sem o sensor baixo estar subido.",
                    ["evento de baixo perdido", "boia baixa travada", "fios invertidos"],
                    {
                        "blocks_cycle_processing": True,
                        "previous_low_state": low_state,
                    },
                )
            )

    if sensor == "baixo" and estado == "desceu" and state.get("alto") == "subiu":
        alerts.append(
            _build_alert(
                event,
                "low_dropped_while_high_active",
                "warning",
                "Sensor baixo desceu com sensor alto ativo",
                "O sensor baixo indicou nivel baixo enquanto o sensor alto ainda estava subido.",
                ["boia alta travada", "leitura invertida", "evento de alto desceu perdido"],
                {
                    "blocks_cycle_processing": True,
                    "previous_high_state": state.get("alto"),
                },
            )
        )

    return alerts


def event_blocks_cycle_processing(alerts: Iterable[Dict[str, Any]]) -> bool:
    return any(
        bool((alert.get("metadata") or {}).get("blocks_cycle_processing"))
        for alert in alerts
    )


def _build_alert(
    event: Dict[str, Any],
    alert_type: str,
    severity: str,
    title: str,
    message: str,
    possible_causes: List[str],
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    event_id = _event_identity(event)
    sensor_timestamp = _normalize_datetime(event.get("timestamp"))
    return {
        "event_id": event_id,
        "type": alert_type,
        "severity": severity,
        "title": title,
        "message": message,
        "sensor_timestamp": sensor_timestamp,
        "possible_causes": possible_causes,
        "metadata": {
            **metadata,
            "sensor": _clean_text(event.get("sensor")),
            "estado": _clean_text(event.get("estado")),
            "document_id": event.get("document_id"),
            "raw_path": event.get("raw_path"),
        },
    }


def _event_identity(event: Dict[str, Any]) -> str:
    for key in ("event_id", "raw_path", "document_id"):
        value = event.get(key)
        if value:
            text = str(value).strip()
            if text:
                return text
    return "unknown"


def _current_state(history: List[Dict[str, Any]]) -> Dict[str, Optional[str]]:
    state: Dict[str, Optional[str]] = {"baixo": None, "alto": None}
    for item in history:
        sensor = _clean_text(item.get("sensor"))
        if sensor in state:
            state[sensor] = _clean_text(item.get("estado"))
    return state


def _latest_matching(history: List[Dict[str, Any]], predicate) -> Optional[Dict[str, Any]]:
    for item in reversed(history):
        if predicate(item):
            return item
    return None


def _clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip().lower()
    return text or None


def _normalize_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return None


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default
