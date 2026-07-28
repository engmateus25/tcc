from datetime import datetime
from typing import Dict, List, Any, Tuple

import numpy as np

from .firestore import fetch_sensor_events
from .autocloud_core import AutoCloud
from .autocloud_fill_time import analyze_fill_time_cycle
from .filling_cycles import extract_filling_cycles
from .sensor_rules import evaluate_sensor_event_rules


# ---------------------------
# 1. Codificação dos eventos
# ---------------------------

def _encode_event(event: Dict, last_timestamp_by_sensor: Dict[str, datetime]) -> np.ndarray:
    """
    Converte um evento do Firestore em um vetor numérico para o AutoCloud.

    event: {
      "sensor": "baixo" | "alto",
      "estado": "subiu" | "desceu",
      "timestamp": datetime (timezone-aware)
    }
    """

    sensor_str = (event.get("sensor") or "").strip().lower()
    estado_str = (event.get("estado") or "").strip().lower()
    ts: datetime = event.get("timestamp")

    # 0 = baixo, 1 = alto
    if sensor_str == "alto":
        sensor_num = 1.0
    else:
        sensor_num = 0.0

    # -1 = desceu, +1 = subiu
    if estado_str == "subiu":
        estado_num = 1.0
    else:
        estado_num = -1.0

    # delta t em segundos desde o ÚLTIMO evento desse mesmo sensor
    last_ts = last_timestamp_by_sensor.get(sensor_str)
    if last_ts is None:
        delta_t = 0.0
    else:
        delta_t = (ts - last_ts).total_seconds()

    last_timestamp_by_sensor[sensor_str] = ts

    # Podemos normalizar ou apenas usar log(1 + delta_t) para ficar mais suave
    delta_t_feat = np.log1p(delta_t)  # log(1 + x)

    return np.array([sensor_num, estado_num, delta_t_feat], dtype=float)


# -----------------------------------------
# 2. Treinar / rodar o AutoCloud nos dados
# -----------------------------------------

def run_autocloud_on_events(events: List[Dict], m: float = 2.5) -> Tuple[AutoCloud, List[int]]:
    """
    Executa o AutoCloud em cima da sequência de eventos.

    Retorna:
      - o objeto AutoCloud (com as nuvens aprendidas)
      - a lista de índices de classe para cada evento
    """
    if not events:
        return AutoCloud(m), []

    auto = AutoCloud(m)
    last_timestamp_by_sensor: Dict[str, datetime] = {}

    for ev in events:
        x = _encode_event(ev, last_timestamp_by_sensor)
        auto.run(x)

    return auto, list(auto.classIndex)


# -------------------------------------------------
# 3. Regras físicas de consistência (baixo/alto)
# -------------------------------------------------

def detect_rule_based_inconsistencies(events: List[Dict]) -> List[Dict[str, Any]]:
    """
    Aplica REGRAS LÓGICAS baseadas na física do sistema:

    - Sensor 'alto' não pode subir ('subiu') se o 'baixo' ainda está 'desceu'
    - Sensor 'baixo' não pode descer ('desceu') se o 'alto' está 'subiu'
    - Em geral: como 'alto' é fisicamente acima de 'baixo', não pode haver
      estado 'alto=subiu' com 'baixo=desceu' ao mesmo tempo.

    Retorna uma lista de alertas com explicação.
    """
    alerts: List[Dict[str, Any]] = []
    history: List[Dict[str, Any]] = []
    for ev in events:
        alerts.extend(evaluate_sensor_event_rules(ev, history))
        history.append(ev)

    return alerts


# ---------------------------------------------------------
# 4. Detecção de anomalias com AutoCloud + Regras
# ---------------------------------------------------------

def detect_intelligent_alerts(period: str = "7d") -> Dict[str, Any]:
    """
    Pipeline completo:
      1. Busca eventos no Firestore (já em ordem cronológica)
      2. Aplica regras deterministicas de consistencia fisica
      3. Extrai ciclos validos de enchimento
      4. Analisa fill_time_seconds sobre os ciclos validos
      4. Junta tudo em um dicionário de retorno
    """
    events = fetch_sensor_events(period=period)

    rule_alerts = detect_rule_based_inconsistencies(events)
    invalid_event_ids = {
        alert["event_id"]
        for alert in rule_alerts
        if (alert.get("metadata") or {}).get("blocks_cycle_processing")
    }

    cycles = extract_filling_cycles(events, invalid_event_ids=invalid_event_ids)
    historical_cycles: List[Dict[str, Any]] = []
    fill_time_analysis: List[Dict[str, Any]] = []
    fill_time_alerts: List[Dict[str, Any]] = []

    for cycle in cycles:
        result = analyze_fill_time_cycle(cycle, historical_cycles)
        alert = result.get("alert")
        if alert:
            fill_time_alerts.append(alert)
        fill_time_analysis.append(
            {
                "cycle_id": cycle["cycle_id"],
                "fill_time_seconds": cycle["fill_time_seconds"],
                "analysis": {key: value for key, value in result.items() if key != "alert"},
            }
        )
        historical_cycles.append(cycle)

    return {
        "periodo_analisado": period,
        "total_eventos": len(events),
        "total_cycles": len(cycles),
        "total_classes_autocloud": None,
        "rare_classes": [],
        "autocloud_anomalies": fill_time_alerts,
        "rule_based_alerts": rule_alerts,
        "filling_cycles": cycles,
        "fill_time_analysis": fill_time_analysis,
    }
