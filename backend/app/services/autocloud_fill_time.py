import os
import statistics
from typing import Any, Dict, Iterable, List, Optional


def analyze_fill_time_cycle(
    cycle: Dict[str, Any],
    historical_cycles: Iterable[Dict[str, Any]],
    *,
    min_samples: Optional[int] = None,
    slow_factor: Optional[float] = None,
    persistent_window: Optional[int] = None,
) -> Dict[str, Any]:
    min_samples = min_samples if min_samples is not None else _env_int("FILL_TIME_MIN_SAMPLES", 5)
    slow_factor = slow_factor if slow_factor is not None else _env_float("FILL_TIME_SLOW_FACTOR", 1.5)
    persistent_window = persistent_window if persistent_window is not None else _env_int(
        "FILL_TIME_PERSISTENT_WINDOW",
        3,
    )

    durations = [
        float(item["fill_time_seconds"])
        for item in historical_cycles
        if item.get("valid") and item.get("fill_time_seconds") is not None
    ]
    current = float(cycle["fill_time_seconds"])

    if len(durations) < min_samples:
        return {
            "used": False,
            "reason": "insufficient_data",
            "samples": len(durations),
            "required_samples": min_samples,
            "alert": None,
        }

    baseline_median = statistics.median(durations)
    baseline_mean = statistics.fmean(durations)
    baseline_stdev = statistics.pstdev(durations) if len(durations) > 1 else 0.0
    alert_type: Optional[str] = None
    severity = "warning"
    title = "Tempo de enchimento atipico"
    message = "O tempo de enchimento ficou fora do padrao historico recente."
    causes = [
        "bomba com baixa vazao",
        "obstrucao hidraulica",
        "entrada de agua limitada",
        "sensor alto demorando a acionar",
    ]
    metadata: Dict[str, Any] = {
        "method": "fill_time_temporal_baseline",
        "baseline_median_seconds": baseline_median,
        "baseline_mean_seconds": baseline_mean,
        "baseline_stdev_seconds": baseline_stdev,
        "current_fill_time_seconds": current,
        "samples": len(durations),
    }

    if baseline_median > 0 and current >= baseline_median * slow_factor:
        alert_type = "slow_fill_cycle"
        metadata["slow_factor"] = slow_factor

    window_values = durations[-max(1, persistent_window - 1) :] + [current]
    if (
        alert_type is None
        and len(window_values) >= persistent_window
        and _strictly_increasing(window_values)
    ):
        previous_window = durations[-persistent_window:]
        previous_median = statistics.median(previous_window) if previous_window else baseline_median
        if previous_median > 0 and current >= previous_median * 1.15:
            alert_type = "persistent_fill_time_shift"
            title = "Aumento persistente no tempo de enchimento"
            message = "Os ultimos ciclos indicam aumento progressivo no tempo de enchimento."
            metadata["persistent_window"] = persistent_window
            metadata["recent_fill_time_seconds"] = window_values

    if (
        alert_type is None
        and baseline_stdev > 0
        and current > baseline_mean + (3 * baseline_stdev)
    ):
        alert_type = "new_fill_time_cluster"
        metadata["z_score"] = (current - baseline_mean) / baseline_stdev

    if alert_type is None:
        return {
            "used": True,
            "reason": "normal_fill_time",
            "samples": len(durations),
            "baseline_median_seconds": baseline_median,
            "current_fill_time_seconds": current,
            "alert": None,
        }

    alert = {
        "event_id": cycle["end_event_id"],
        "type": alert_type,
        "severity": severity,
        "title": title,
        "message": message,
        "sensor_timestamp": cycle.get("ended_at"),
        "possible_causes": causes,
        "metadata": {
            **metadata,
            "cycle_id": cycle["cycle_id"],
            "start_event_id": cycle["start_event_id"],
            "end_event_id": cycle["end_event_id"],
            "blocks_cycle_processing": False,
        },
    }

    return {
        "used": True,
        "reason": alert_type,
        "samples": len(durations),
        "baseline_median_seconds": baseline_median,
        "current_fill_time_seconds": current,
        "alert": alert,
    }


def _strictly_increasing(values: List[float]) -> bool:
    return all(left < right for left, right in zip(values, values[1:]))


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default
