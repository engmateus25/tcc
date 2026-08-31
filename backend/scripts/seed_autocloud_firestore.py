from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.services.autocloud_core import (  # noqa: E402
    build_filling_cycle_feature_stats,
    vectorize_filling_cycle,
)
from app.services.autocloud_fill_time import analyze_fill_time_cycle  # noqa: E402
from app.services.autocloud_samples import (  # noqa: E402
    AUTOCLOUD_SAMPLES_COLLECTION,
    save_autocloud_filling_sample,
)
from app.services.sensor_realtime import SensorRealtimeEngine  # noqa: E402


DEFAULT_BASELINE_SECONDS = [470, 480, 485, 490, 475]


def build_cycle(
    test_run_id: str,
    index: int,
    fill_time_seconds: int,
    *,
    base: datetime,
    device_id: str,
    source: str,
    label: str,
) -> Dict[str, Any]:
    started_at = base + timedelta(minutes=index * 20)
    low_raised_at = started_at + timedelta(seconds=60)
    ended_at = started_at + timedelta(seconds=fill_time_seconds)
    return {
        "cycle_id": f"{test_run_id}-{label}-{index}",
        "start_event_id": f"comandos/{test_run_id}-{label}-start-{index}",
        "end_event_id": f"sensores/{test_run_id}-{label}-high-{index}",
        "started_at": started_at,
        "low_raised_at": low_raised_at,
        "ended_at": ended_at,
        "pump_started_at": started_at,
        "fill_time_seconds": float(fill_time_seconds),
        "low_to_high_seconds": float(fill_time_seconds - 60),
        "pump_to_low_seconds": 60.0,
        "valid": True,
        "device_id": device_id,
        "start_source": "pump_command_confirmed",
        "start_event_type": "command",
        "pump_mode": "automatico",
        "metadata": {
            "source": source,
            "test_run_id": test_run_id,
            "scenario": label,
            "low_raised_event_id": f"sensores/{test_run_id}-{label}-low-up-{index}",
        },
    }


def build_sensor_event(
    test_run_id: str,
    label: str,
    sensor: str,
    estado: str,
    timestamp: datetime,
    *,
    device_id: str,
    source: str,
) -> Dict[str, Any]:
    doc_id = f"{test_run_id}-{label}-{sensor}-{estado}".replace(" ", "-")
    return {
        "document_id": doc_id,
        "event_id": f"sensores/{doc_id}",
        "raw_path": f"sensores/{doc_id}",
        "sensor": sensor,
        "estado": estado,
        "timestamp": timestamp,
        "device_id": device_id,
        "source": source,
        "test_run_id": test_run_id,
    }


def seed_baseline_samples(cycles: Iterable[Dict[str, Any]], *, dry_run: bool) -> List[Dict[str, Any]]:
    cycles = list(cycles)
    stats = build_filling_cycle_feature_stats(cycles)
    saved: List[Dict[str, Any]] = []

    for cycle in cycles:
        _vector, feature_metadata = vectorize_filling_cycle(cycle, stats)
        analysis = {
            "method": "autocloud_seed_baseline",
            "reason": "baseline_seed",
            "samples": len(cycles),
            "feature_metadata": feature_metadata,
        }
        print(
            f"{'DRY-RUN' if dry_run else 'WRITE'} "
            f"{AUTOCLOUD_SAMPLES_COLLECTION}/{cycle['cycle_id']} "
            f"fill_time_seconds={cycle['fill_time_seconds']:.0f}"
        )
        if not dry_run:
            saved.append(
                save_autocloud_filling_sample(
                    cycle,
                    analysis,
                    source="pibiti_autocloud_baseline_seed",
                )
            )
    return saved


def validate_and_persist_alerts(
    test_run_id: str,
    baseline_cycles: List[Dict[str, Any]],
    *,
    base: datetime,
    device_id: str,
    source: str,
    dry_run: bool,
) -> Dict[str, Any]:
    normal_cycle = build_cycle(
        test_run_id,
        100,
        482,
        base=base + timedelta(hours=2),
        device_id=device_id,
        source=source,
        label="normal-validation",
    )
    normal_analysis = analyze_fill_time_cycle(normal_cycle, baseline_cycles, min_samples=5)

    slow_started_at = base + timedelta(hours=3)
    slow_high_at = slow_started_at + timedelta(seconds=900)
    slow_history = [
        build_sensor_event(
            test_run_id,
            "slow-low-down",
            "baixo",
            "desceu",
            slow_started_at,
            device_id=device_id,
            source=source,
        ),
        build_sensor_event(
            test_run_id,
            "slow-low-up",
            "baixo",
            "subiu",
            slow_started_at + timedelta(seconds=60),
            device_id=device_id,
            source=source,
        ),
    ]
    slow_event = build_sensor_event(
        test_run_id,
        "slow-high",
        "alto",
        "subiu",
        slow_high_at,
        device_id=device_id,
        source=source,
    )

    interlock_started_at = base + timedelta(hours=4)
    interlock_history = [
        build_sensor_event(
            test_run_id,
            "interlock-low-down",
            "baixo",
            "desceu",
            interlock_started_at,
            device_id=device_id,
            source=source,
        )
    ]
    interlock_event = build_sensor_event(
        test_run_id,
        "interlock-high",
        "alto",
        "subiu",
        interlock_started_at + timedelta(seconds=120),
        device_id=device_id,
        source=source,
    )

    if dry_run:
        slow_analysis = analyze_fill_time_cycle(
            {
                "cycle_id": f"{test_run_id}-dry-slow",
                "start_event_id": slow_history[0]["event_id"],
                "end_event_id": slow_event["event_id"],
                "started_at": slow_started_at,
                "low_raised_at": slow_history[1]["timestamp"],
                "ended_at": slow_high_at,
                "fill_time_seconds": 900,
                "low_to_high_seconds": 840,
                "pump_to_low_seconds": 60,
                "valid": True,
                "device_id": device_id,
                "start_source": "sensor_low_fallback",
            },
            baseline_cycles,
            min_samples=5,
        )
        return {
            "normal_analysis": normal_analysis,
            "slow_result": {"autocloud": slow_analysis, "alerts_created": [slow_analysis.get("alert")]},
            "interlock_result": {"alerts_created": [{"type": "unexpected_high_without_low"}]},
        }

    slow_result = SensorRealtimeEngine().process_event(
        slow_event,
        history=slow_history,
        command_history=[],
        historical_autocloud_samples=baseline_cycles,
    )
    interlock_result = SensorRealtimeEngine().process_event(
        interlock_event,
        history=interlock_history,
        command_history=[],
        historical_autocloud_samples=baseline_cycles,
    )

    return {
        "normal_analysis": normal_analysis,
        "slow_result": slow_result,
        "interlock_result": interlock_result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed de baseline e alertas demonstraveis do AutoCloud no Firestore.",
    )
    parser.add_argument("--test-run-id", default=datetime.now(timezone.utc).strftime("pibiti-%Y%m%d-%H%M%S"))
    parser.add_argument("--device-id", default="esp32-reservatorio-01")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    source = "pibiti_autocloud_validation"
    base = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(hours=8)
    baseline_cycles = [
        build_cycle(
            args.test_run_id,
            index,
            seconds,
            base=base,
            device_id=args.device_id,
            source=source,
            label="baseline",
        )
        for index, seconds in enumerate(DEFAULT_BASELINE_SECONDS, start=1)
    ]

    print(f"test_run_id={args.test_run_id}")
    print(f"device_id={args.device_id}")
    print(f"collection={AUTOCLOUD_SAMPLES_COLLECTION}")
    saved = seed_baseline_samples(baseline_cycles, dry_run=args.dry_run)
    results = validate_and_persist_alerts(
        args.test_run_id,
        baseline_cycles,
        base=base,
        device_id=args.device_id,
        source=source,
        dry_run=args.dry_run,
    )

    normal = results["normal_analysis"]
    slow = results["slow_result"]
    interlock = results["interlock_result"]
    print(f"baseline_samples_written={len(saved) if not args.dry_run else len(baseline_cycles)}")
    print(f"normal_cycle_reason={normal.get('reason')} alert={bool(normal.get('alert'))}")
    print(f"slow_cycle_reason={(slow.get('autocloud') or {}).get('reason')}")
    print(f"slow_cycle_created_cloud={(slow.get('autocloud') or {}).get('created_cloud')}")
    print(
        "slow_cycle_nearest_normalized_distance="
        f"{(slow.get('autocloud') or {}).get('nearest_normalized_distance')}"
    )
    print(f"slow_alerts_created={[item.get('type') for item in slow.get('alerts_created', []) if item]}")
    print(f"interlock_alerts_created={[item.get('type') for item in interlock.get('alerts_created', []) if item]}")
    print("Abra a Home e atualize o painel de Alertas Inteligentes para capturar os alertas abertos.")


if __name__ == "__main__":
    main()
