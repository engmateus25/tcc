from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np


EPSILON = 1e-9
FILLING_CYCLE_FEATURE_NAMES = (
    "fill_time_seconds",
    "low_to_high_seconds",
    "pump_to_low_seconds",
    "start_source_score",
    "sensor_sequence_score",
)


def _as_vector(value: Any) -> np.ndarray:
    vector = np.asarray(value, dtype=float).reshape(-1)
    if vector.size == 0:
        raise ValueError("AutoCloud requires at least one numeric feature")
    return vector


class DataCloud:
    N = 0

    def __init__(self, x: Any):
        self.n = 1
        self.mean = _as_vector(x)
        self.variance = EPSILON
        self.pertinency = 1.0
        self.eccAn = 0.0
        DataCloud.N += 1

    def addDataClaud(self, x: Any):
        self.add_data_cloud(x)

    def add_data_cloud(self, x: Any):
        vector = _as_vector(x)
        self.n = 2
        self.mean = (self.mean + vector) / 2.0
        self.variance = max(float(np.linalg.norm(self.mean - vector) ** 2), EPSILON)

    def updateDataCloud(self, n: int, mean: Any, variance: float):
        self.update_data_cloud(n, mean, variance)

    def update_data_cloud(self, n: int, mean: Any, variance: float):
        self.n = int(max(1, n))
        self.mean = _as_vector(mean)
        self.variance = max(float(variance), EPSILON)


class AutoCloud:
    """
    Implementacao incremental do AutoCloud com estado por instancia.

    A API historica (`run`, `classIndex`, `mergeClouds`) foi preservada, mas o
    estado global de classe foi removido para evitar vazamento entre analises.
    """

    def __init__(self, m: float):
        self.m = max(float(m), 0.1)
        self.c = np.array([], dtype=DataCloud)
        self.alfa = np.array([], dtype=float)
        self.matrixIntersection = np.zeros((0, 0), dtype=int)
        self.listIntersection = np.array([], dtype=int)
        self.relevanceList = np.array([], dtype=float)
        self.classIndex: List[int] = []
        self.k = 1

    def mergeClouds(self):
        self.merge_clouds()

    def merge_clouds(self):
        changed = True
        while changed and len(self.c) > 1:
            changed = False
            for i in range(len(self.c) - 1):
                for j in range(i + 1, len(self.c)):
                    if self.listIntersection[i] == 1 and self.listIntersection[j] == 1:
                        self.matrixIntersection[i, j] += 1

                    n_i = self.c[i].n
                    n_j = self.c[j].n
                    n_intersection = int(self.matrixIntersection[i, j])

                    if n_intersection <= (n_i - n_intersection) and n_intersection <= (
                        n_j - n_intersection
                    ):
                        continue

                    n = max(1, n_i + n_j - n_intersection)
                    mean = ((n_i * self.c[i].mean) + (n_j * self.c[j].mean)) / (
                        n_i + n_j
                    )
                    denominator = max(1, n_i + n_j - 2)
                    variance = (
                        ((n_i - 1) * self.c[i].variance)
                        + ((n_j - 1) * self.c[j].variance)
                    ) / denominator

                    merged_cloud = DataCloud(mean)
                    merged_cloud.update_data_cloud(n, mean, variance)
                    self.c[i] = merged_cloud
                    self.c = np.delete(self.c, j)
                    self.listIntersection = np.delete(self.listIntersection, j)
                    self.alfa = np.delete(self.alfa, j)
                    self.matrixIntersection = np.delete(self.matrixIntersection, j, axis=0)
                    self.matrixIntersection = np.delete(self.matrixIntersection, j, axis=1)
                    changed = True
                    break
                if changed:
                    break

    def score(self, X: Any) -> Dict[str, Any]:
        vector = _as_vector(X)
        if len(self.c) == 0:
            return {
                "nearest_cloud_index": None,
                "nearest_distance": None,
                "nearest_normalized_distance": None,
                "distances": [],
            }

        distances = [float(np.linalg.norm(vector - cloud.mean)) for cloud in self.c]
        normalized_distances = [
            float(distance / math.sqrt(max(cloud.variance, EPSILON)))
            for distance, cloud in zip(distances, self.c)
        ]
        nearest_index = int(np.argmin(normalized_distances))
        return {
            "nearest_cloud_index": nearest_index,
            "nearest_distance": distances[nearest_index],
            "nearest_normalized_distance": normalized_distances[nearest_index],
            "distances": distances,
            "normalized_distances": normalized_distances,
        }

    def run(self, X: Any) -> Dict[str, Any]:
        vector = _as_vector(X)
        self.listIntersection = np.zeros((len(self.c)), dtype=int)
        self.alfa = np.zeros((len(self.c)), dtype=float)
        created_cloud = False

        if self.k == 1 or len(self.c) == 0:
            self.c = np.array([DataCloud(vector)], dtype=DataCloud)
            self.matrixIntersection = np.zeros((1, 1), dtype=int)
            self.listIntersection = np.array([1], dtype=int)
            self.alfa = np.array([1.0], dtype=float)
            self.relevanceList = np.array([1.0], dtype=float)
            class_index = 0
            created_cloud = True

        elif self.k == 2:
            self.c[0].add_data_cloud(vector)
            self.listIntersection = np.array([1], dtype=int)
            self.alfa = np.array([1.0], dtype=float)
            self.relevanceList = np.array([1.0], dtype=float)
            class_index = 0

        else:
            pre_score = self.score(vector)
            nearest_distance = pre_score.get("nearest_normalized_distance")
            if isinstance(nearest_distance, (int, float)) and nearest_distance > self.m:
                self.c = np.append(self.c, DataCloud(vector))
                self.listIntersection = np.append(self.listIntersection, 1)
                self.alfa = np.append(self.alfa, 1.0)
                self.matrixIntersection = np.pad(
                    self.matrixIntersection,
                    ((0, 1), (0, 1)),
                    "constant",
                    constant_values=0,
                )
                self.relevanceList = np.zeros((len(self.c)), dtype=float)
                class_index = len(self.c) - 1
                self.relevanceList[class_index] = 1.0
                created_cloud = True
                self.classIndex.append(class_index)
                self.k += 1
                return {
                    "class_index": class_index,
                    "cloud_count": len(self.c),
                    "created_cloud": True,
                    "accepted_by_existing_cloud": False,
                    "relevance": [float(item) for item in self.relevanceList],
                    "intersections": [int(item) for item in self.listIntersection],
                }

            create_cloud = True
            eccentricities: List[float] = []

            for index, cloud in enumerate(list(self.c)):
                n = cloud.n + 1
                mean = ((n - 1) / n) * cloud.mean + (1 / n) * vector
                distance_sq = float((mean - vector).T.dot(mean - vector))
                variance = ((n - 1) / n) * cloud.variance + (distance_sq / n)
                variance = max(float(variance), EPSILON)

                eccentricity = (1 / n) + (distance_sq / (n * variance))
                typicality = max(0.0, 1.0 - eccentricity)
                norm_eccentricity = eccentricity / 2.0
                norm_typicality = typicality / max(1, self.k - 2)
                threshold = (self.m**2 + 1) / (2 * n)
                cloud.eccAn = float(eccentricity)
                eccentricities.append(float(eccentricity))

                if norm_eccentricity <= threshold:
                    cloud.update_data_cloud(n, mean, variance)
                    self.alfa[index] = norm_typicality
                    self.listIntersection[index] = 1
                    create_cloud = False

            if create_cloud:
                self.c = np.append(self.c, DataCloud(vector))
                self.listIntersection = np.append(self.listIntersection, 1)
                self.alfa = np.append(self.alfa, 1.0)
                self.matrixIntersection = np.pad(
                    self.matrixIntersection,
                    ((0, 1), (0, 1)),
                    "constant",
                    constant_values=0,
                )
                class_index = len(self.c) - 1
                created_cloud = True
            else:
                self.merge_clouds()
                alpha_sum = float(np.sum(self.alfa))
                if alpha_sum > EPSILON:
                    self.relevanceList = self.alfa / alpha_sum
                    class_index = int(np.argmax(self.relevanceList))
                else:
                    score = self.score(vector)
                    class_index = int(score["nearest_cloud_index"] or 0)
                    self.relevanceList = np.zeros((len(self.c)), dtype=float)
                    self.relevanceList[class_index] = 1.0

        self.classIndex.append(class_index)
        self.k += 1
        return {
            "class_index": class_index,
            "cloud_count": len(self.c),
            "created_cloud": created_cloud,
            "accepted_by_existing_cloud": not created_cloud,
            "relevance": [float(item) for item in self.relevanceList],
            "intersections": [int(item) for item in self.listIntersection],
        }


@dataclass(frozen=True)
class FillingCycleFeatureStats:
    names: Tuple[str, ...]
    medians: Tuple[float, ...]
    scales: Tuple[float, ...]


def build_filling_cycle_feature_stats(
    cycles: Iterable[Dict[str, Any]],
) -> FillingCycleFeatureStats:
    raw_vectors = [
        _raw_filling_cycle_features(cycle)
        for cycle in cycles
        if cycle.get("valid") and cycle.get("fill_time_seconds") is not None
    ]
    if not raw_vectors:
        return FillingCycleFeatureStats(
            names=FILLING_CYCLE_FEATURE_NAMES,
            medians=(0.0, 0.0, 0.0, 0.0, 0.0),
            scales=(1.0, 1.0, 1.0, 1.0, 1.0),
        )

    matrix = np.vstack(raw_vectors)
    medians: List[float] = []
    scales: List[float] = []
    for column_index in range(matrix.shape[1]):
        values = [float(item) for item in matrix[:, column_index]]
        median = statistics.median(values)
        medians.append(float(median))
        scales.append(_robust_scale(values, median))

    return FillingCycleFeatureStats(
        names=FILLING_CYCLE_FEATURE_NAMES,
        medians=tuple(medians),
        scales=tuple(scales),
    )


def vectorize_filling_cycle(
    cycle: Dict[str, Any],
    stats: Optional[FillingCycleFeatureStats] = None,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    stats = stats or build_filling_cycle_feature_stats([cycle])
    raw = _raw_filling_cycle_features(cycle)
    medians = np.asarray(stats.medians, dtype=float)
    scales = np.asarray(stats.scales, dtype=float)
    normalized = (raw - medians) / np.where(scales <= EPSILON, 1.0, scales)
    metadata = {
        "feature_names": list(stats.names),
        "raw_features": [float(item) for item in raw],
        "normalized_features": [float(item) for item in normalized],
        "feature_medians": [float(item) for item in medians],
        "feature_scales": [float(item) for item in scales],
        "start_source": cycle.get("start_source") or "unknown",
        "sensor_sequence_complete": _sensor_sequence_score(cycle) >= 1.0,
    }
    return normalized.astype(float), metadata


def run_autocloud_for_filling_cycle(
    cycle: Dict[str, Any],
    historical_cycles: Iterable[Dict[str, Any]],
    *,
    m: float = 2.5,
) -> Dict[str, Any]:
    history = [
        item
        for item in historical_cycles
        if item.get("valid") and item.get("fill_time_seconds") is not None
    ]
    stats = build_filling_cycle_feature_stats(history)
    auto = AutoCloud(m)
    training_results = []
    for item in history:
        vector, _metadata = vectorize_filling_cycle(item, stats)
        training_results.append(auto.run(vector))

    current_vector, metadata = vectorize_filling_cycle(cycle, stats)
    score_before = auto.score(current_vector)
    result = auto.run(current_vector)
    return {
        "method": "autocloud_filling_cycle_clustering",
        "m": m,
        "training_samples": len(history),
        "training_cloud_count": max(0, result["cloud_count"] - int(result["created_cloud"])),
        "class_index": result["class_index"],
        "cloud_count": result["cloud_count"],
        "created_cloud": result["created_cloud"],
        "accepted_by_existing_cloud": result["accepted_by_existing_cloud"],
        "nearest_cloud_index": score_before.get("nearest_cloud_index"),
        "nearest_distance": score_before.get("nearest_distance"),
        "nearest_normalized_distance": score_before.get("nearest_normalized_distance"),
        "feature_metadata": metadata,
        "training_class_index": [
            int(item["class_index"])
            for item in training_results
        ],
    }


def _raw_filling_cycle_features(cycle: Dict[str, Any]) -> np.ndarray:
    fill_time = _safe_float(cycle.get("fill_time_seconds"))
    low_to_high = _safe_float(cycle.get("low_to_high_seconds"))
    if low_to_high <= 0:
        low_raised_at = _normalize_datetime(cycle.get("low_raised_at"))
        ended_at = _normalize_datetime(cycle.get("ended_at"))
        if low_raised_at and ended_at and ended_at > low_raised_at:
            low_to_high = (ended_at - low_raised_at).total_seconds()
        else:
            low_to_high = fill_time

    pump_to_low = _safe_float(cycle.get("pump_to_low_seconds"))
    if pump_to_low <= 0:
        started_at = _normalize_datetime(cycle.get("started_at"))
        low_raised_at = _normalize_datetime(cycle.get("low_raised_at"))
        if started_at and low_raised_at and low_raised_at > started_at:
            pump_to_low = (low_raised_at - started_at).total_seconds()
        else:
            pump_to_low = max(0.0, fill_time - low_to_high)

    return np.array(
        [
            fill_time,
            low_to_high,
            pump_to_low,
            _start_source_score(cycle),
            _sensor_sequence_score(cycle),
        ],
        dtype=float,
    )


def _robust_scale(values: Sequence[float], median: float) -> float:
    if not values:
        return 1.0
    if len(values) >= 4:
        quantiles = statistics.quantiles(values, n=4, method="inclusive")
        iqr = float(quantiles[2] - quantiles[0])
        if iqr > EPSILON:
            return max(iqr / 1.349, 1.0)
    if len(values) > 1:
        stdev = statistics.pstdev(values)
        if stdev > EPSILON:
            return max(float(stdev), 1.0)
    return max(abs(float(median)) * 0.1, 1.0)


def _start_source_score(cycle: Dict[str, Any]) -> float:
    source = str(cycle.get("start_source") or "").strip().lower()
    if source == "pump_command_confirmed":
        return 1.0
    if source == "sensor_low_fallback":
        return 0.65
    return 0.0


def _sensor_sequence_score(cycle: Dict[str, Any]) -> float:
    metadata = cycle.get("metadata") or {}
    if cycle.get("low_raised_at") or metadata.get("low_raised_at"):
        return 1.0
    if metadata.get("low_raised_event_id"):
        return 1.0
    if metadata.get("start_sensor") == "baixo" and metadata.get("end_sensor") == "alto":
        return 0.5
    return 0.0


def _safe_float(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(number):
        return 0.0
    return max(0.0, number)


def _normalize_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return None


def filter_time(signal_input, e1=20, e2=60):
    signal = np.asarray(signal_input)
    if len(signal) == 0:
        return signal

    result = []
    for _i in range(min(e1, len(signal))):
        result.append(0)
    for i in range(e1, len(signal)):
        if signal[i] == 0 and np.sum(signal[i - e1 : i] == signal[i]) == e1:
            result.append(signal[i])
        elif i >= e2 and signal[i] != 0 and np.sum(signal[i - e2 : i] == signal[i]) == e2:
            result.append(signal[i])
        else:
            result.append(result[-1])
    return np.array(result)
