import os
import statistics
from typing import Any, Dict, Iterable, List, Optional

from .autocloud_core import run_autocloud_for_filling_cycle


def analyze_fill_time_cycle(
    cycle: Dict[str, Any],
    historical_cycles: Iterable[Dict[str, Any]],
    *,
    min_samples: Optional[int] = None,
    slow_factor: Optional[float] = None,
    persistent_window: Optional[int] = None,
    m: Optional[float] = None,
) -> Dict[str, Any]:
    min_samples = min_samples if min_samples is not None else _env_int("FILL_TIME_MIN_SAMPLES", 5)
    slow_factor = slow_factor if slow_factor is not None else _env_float("FILL_TIME_SLOW_FACTOR", 1.5)
    persistent_window = persistent_window if persistent_window is not None else _env_int(
        "FILL_TIME_PERSISTENT_WINDOW",
        3,
    )
    m = m if m is not None else _env_float("AUTOCLOUD_M", 2.5)

    valid_historical_cycles = [
        item
        for item in historical_cycles
        if item.get("valid") and item.get("fill_time_seconds") is not None
    ]
    durations = [float(item["fill_time_seconds"]) for item in valid_historical_cycles]
    current = float(cycle["fill_time_seconds"])

    if len(durations) < min_samples:
        return {
            "used": False,
            "reason": "insufficient_data",
            "method": "autocloud_filling_cycle_clustering",
            "samples": len(durations),
            "required_samples": min_samples,
            "alert": None,
        }

    autocloud_result = run_autocloud_for_filling_cycle(
        cycle,
        valid_historical_cycles,
        m=m,
    )
    baseline_median = statistics.median(durations)
    baseline_mean = statistics.fmean(durations)
    baseline_stdev = statistics.pstdev(durations) if len(durations) > 1 else 0.0
    difference_seconds = current - baseline_median
    difference_ratio = (current / baseline_median) if baseline_median > 0 else None
    difference_percent = (
        ((current - baseline_median) / baseline_median) * 100.0
        if baseline_median > 0
        else None
    )
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
        "method": "autocloud_filling_cycle_clustering",
        "baseline_method": "fill_time_temporal_baseline",
        "baseline_median_seconds": baseline_median,
        "baseline_mean_seconds": baseline_mean,
        "baseline_stdev_seconds": baseline_stdev,
        "current_fill_time_seconds": current,
        "current_vs_median_seconds": difference_seconds,
        "current_vs_median_ratio": difference_ratio,
        "current_vs_median_percent": difference_percent,
        "samples": len(durations),
        "autocloud_m": m,
        "class_index": autocloud_result["class_index"],
        "cloud_count": autocloud_result["cloud_count"],
        "created_cloud": autocloud_result["created_cloud"],
        "accepted_by_existing_cloud": autocloud_result["accepted_by_existing_cloud"],
        "nearest_cloud_index": autocloud_result["nearest_cloud_index"],
        "nearest_distance": autocloud_result["nearest_distance"],
        "nearest_normalized_distance": autocloud_result["nearest_normalized_distance"],
        "feature_metadata": autocloud_result["feature_metadata"],
    }

    if baseline_median > 0 and current >= baseline_median * slow_factor:
        alert_type = "slow_fill_cycle"
        title = "Tempo de enchimento lento"
        metadata["slow_factor"] = slow_factor
        metadata["slow_threshold_seconds"] = baseline_median * slow_factor

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
        title = "Novo padrao temporal de enchimento"
        message = "O ciclo formou um agrupamento temporal distante do historico recente."
        metadata["z_score"] = (current - baseline_mean) / baseline_stdev

    cluster_distance = autocloud_result.get("nearest_normalized_distance")
    if (
        alert_type is None
        and autocloud_result.get("created_cloud")
        and isinstance(cluster_distance, (int, float))
        and cluster_distance >= m
        and baseline_median > 0
        and current >= baseline_median * 1.2
    ):
        alert_type = "new_fill_time_cluster"
        title = "Novo padrao temporal de enchimento"
        message = "O ciclo formou uma nova nuvem distante do historico recente."
        metadata["cluster_distance_threshold"] = m

    if alert_type is None:
        return {
            "used": True,
            "reason": "normal_fill_time",
            "method": "autocloud_filling_cycle_clustering",
            "samples": len(durations),
            "baseline_median_seconds": baseline_median,
            "baseline_mean_seconds": baseline_mean,
            "baseline_stdev_seconds": baseline_stdev,
            "current_fill_time_seconds": current,
            "current_vs_median_seconds": difference_seconds,
            "current_vs_median_ratio": difference_ratio,
            "current_vs_median_percent": difference_percent,
            "class_index": autocloud_result["class_index"],
            "cloud_count": autocloud_result["cloud_count"],
            "created_cloud": autocloud_result["created_cloud"],
            "nearest_normalized_distance": autocloud_result["nearest_normalized_distance"],
            "feature_metadata": autocloud_result["feature_metadata"],
            "alert": None,
        }

    message = _build_alert_message(
        message,
        current_seconds=current,
        baseline_median_seconds=baseline_median,
        difference_seconds=difference_seconds,
        difference_percent=difference_percent,
        nearest_normalized_distance=autocloud_result.get("nearest_normalized_distance"),
    )

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
        "method": "autocloud_filling_cycle_clustering",
        "samples": len(durations),
        "baseline_median_seconds": baseline_median,
        "baseline_mean_seconds": baseline_mean,
        "baseline_stdev_seconds": baseline_stdev,
        "current_fill_time_seconds": current,
        "current_vs_median_seconds": difference_seconds,
        "current_vs_median_ratio": difference_ratio,
        "current_vs_median_percent": difference_percent,
        "class_index": autocloud_result["class_index"],
        "cloud_count": autocloud_result["cloud_count"],
        "created_cloud": autocloud_result["created_cloud"],
        "nearest_normalized_distance": autocloud_result["nearest_normalized_distance"],
        "feature_metadata": autocloud_result["feature_metadata"],
        "alert": alert,
    }


def _strictly_increasing(values: List[float]) -> bool:
    return all(left < right for left, right in zip(values, values[1:]))


def _build_alert_message(
    base_message: str,
    *,
    current_seconds: float,
    baseline_median_seconds: float,
    difference_seconds: float,
    difference_percent: Optional[float],
    nearest_normalized_distance: Any,
) -> str:
    parts = [
        base_message,
        (
            "Tempo observado: "
            f"{_format_duration(current_seconds)} "
            f"({current_seconds:.0f} s)."
        ),
    ]
    if baseline_median_seconds > 0:
        parts.append(
            "Mediana historica: "
            f"{_format_duration(baseline_median_seconds)} "
            f"({baseline_median_seconds:.0f} s)."
        )
        difference_label = _format_signed_duration(difference_seconds)
        if difference_percent is not None:
            parts.append(
                "Diferenca para a mediana: "
                f"{difference_label} ({_format_signed_percent(difference_percent)})."
            )
    if isinstance(nearest_normalized_distance, (int, float)):
        parts.append(
            "Distancia normalizada do cluster: "
            f"{nearest_normalized_distance:.2f}."
        )
    return " ".join(parts)


def _format_duration(seconds: float) -> str:
    total_seconds = max(0, int(round(seconds)))
    minutes, remaining_seconds = divmod(total_seconds, 60)
    if minutes <= 0:
        return f"{remaining_seconds}s"
    return f"{minutes}min {remaining_seconds:02d}s"


def _format_signed_duration(seconds: float) -> str:
    sign = "+" if seconds >= 0 else "-"
    return f"{sign}{_format_duration(abs(seconds))}"


def _format_signed_percent(value: float) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1f}%".replace(".", ",")


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
