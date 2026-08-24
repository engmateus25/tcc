from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

from dotenv import load_dotenv
from firebase_admin import firestore

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.services.firestore import _init_firebase_admin_once


def utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def build_documents(test_run_id: str) -> Tuple[list[Dict[str, Any]], list[Dict[str, Any]]]:
    base = datetime.now(timezone.utc).replace(microsecond=0)
    common = {
        "device_id": "esp32-reservatorio-01",
        "source": "integration_test",
        "test_run_id": test_run_id,
    }
    commands = [
        {
            **common,
            "id": f"{test_run_id}-command-start",
            "command_id": f"{test_run_id}-command-start",
            "event_id": f"comandos/{test_run_id}-command-start",
            "bomba": "bomba ligar",
            "acionamento": "remoto",
            "requested_state": True,
            "applied_state": True,
            "applied": True,
            "confirmed": True,
            "state_changed": True,
            "priority": "remoto",
            "overridden_by": "",
            "reason": "integration test confirmed start",
            "timestamp": base,
        }
    ]
    sensors = [
        {
            **common,
            "id": f"{test_run_id}-sensor-low",
            "event_id": f"sensores/{test_run_id}-sensor-low",
            "sensor": "baixo",
            "estado": "desceu",
            "timestamp": base,
        },
        {
            **common,
            "id": f"{test_run_id}-sensor-high",
            "event_id": f"sensores/{test_run_id}-sensor-high",
            "sensor": "alto",
            "estado": "subiu",
            "timestamp": base + timedelta(seconds=480),
        },
    ]
    return sensors, commands


def collection_names(operational: bool) -> Tuple[str, str]:
    if operational:
        return "sensores", "comandos"
    return "integration_test_sensores", "integration_test_comandos"


def upsert_documents(collection: str, documents: Iterable[Dict[str, Any]], dry_run: bool) -> None:
    db = None
    if not dry_run:
        _init_firebase_admin_once()
        db = firestore.client()
    for document in documents:
        doc_id = str(document["id"])
        payload = {key: value for key, value in document.items() if key != "id"}
        print(f"{'DRY-RUN' if dry_run else 'WRITE'} {collection}/{doc_id}")
        if db is not None:
            db.collection(collection).document(doc_id).set(payload, merge=True)


def cleanup(collections: Iterable[str], test_run_id: str, dry_run: bool) -> None:
    _init_firebase_admin_once()
    db = firestore.client()
    for collection in collections:
        query = db.collection(collection).where(
            filter=firestore.FieldFilter("test_run_id", "==", test_run_id)
        )
        for doc in query.stream():
            print(f"{'DRY-RUN' if dry_run else 'DELETE'} {collection}/{doc.id}")
            if not dry_run:
                doc.reference.delete()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed seguro e idempotente de documentos de integracao Firestore.",
    )
    parser.add_argument("--test-run-id", default=f"codex-{uuid.uuid4().hex[:10]}")
    parser.add_argument("--operational", action="store_true", help="usa sensores/comandos reais")
    parser.add_argument("--dry-run", action="store_true", help="mostra sem gravar")
    parser.add_argument("--cleanup", action="store_true", help="remove docs do test_run_id")
    args = parser.parse_args()

    sensor_collection, command_collection = collection_names(args.operational)
    print(f"test_run_id={args.test_run_id}")
    print(f"collections={sensor_collection},{command_collection}")

    if args.cleanup:
        cleanup([sensor_collection, command_collection], args.test_run_id, args.dry_run)
        return

    sensors, commands = build_documents(args.test_run_id)
    upsert_documents(command_collection, commands, args.dry_run)
    upsert_documents(sensor_collection, sensors, args.dry_run)
    print("Seed finalizado. Em modo operational, aguarde a Function processar sensores/comandos.")


if __name__ == "__main__":
    main()
