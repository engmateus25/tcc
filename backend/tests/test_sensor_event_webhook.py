import os
import unittest
import asyncio
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

from app.routers.alerts import sensor_event_webhook
from app.schemas.dto import SensorEventIn
from app.services.sensor_event_processing import (
    SensorEventReservation,
    build_event_identity,
)
from app.services.sensor_realtime import process_new_sensor_event


VALID_RESPONSE = {
    "processed": True,
    "duplicate": False,
    "event_id": "sensores/doc-1",
    "processing_key": "processing-key",
    "processing_status": "processed",
    "payload_hash_mismatch": False,
    "alerts_created": [],
    "cycle_created": None,
    "autocloud": {"used": True, "class_index": 0, "alert_created": False},
}


class SensorEventContractTests(unittest.TestCase):
    def test_schema_normalizes_legacy_payload(self):
        event = SensorEventIn(sensor=" BAIXO ", estado=" DESCEU ", timestamp=None)

        self.assertEqual(event.sensor, "baixo")
        self.assertEqual(event.estado, "desceu")
        self.assertIsNotNone(event.timestamp.tzinfo)

    def test_schema_rejects_invalid_sensor(self):
        with self.assertRaises(ValidationError):
            SensorEventIn(sensor="meio", estado="subiu")

    def test_event_identity_prefers_raw_path_then_document_id(self):
        timestamp = datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc)

        self.assertEqual(
            build_event_identity(
                {
                    "raw_path": "sensores/doc-1",
                    "document_id": "doc-1",
                    "sensor": "baixo",
                    "estado": "desceu",
                    "timestamp": timestamp,
                }
            ),
            "sensores/doc-1",
        )
        self.assertEqual(
            build_event_identity(
                {
                    "document_id": "doc-2",
                    "sensor": "alto",
                    "estado": "subiu",
                    "timestamp": timestamp,
                }
            ),
            "sensores/doc-2",
        )


class SensorEventWebhookTests(unittest.TestCase):
    def make_payload(self):
        return SensorEventIn(
            document_id="doc-1",
            sensor="baixo",
            estado="desceu",
            timestamp="2026-07-27T12:00:00Z",
            source="firestore_on_create",
            raw_path="sensores/doc-1",
        )

    @patch.dict(os.environ, {"SENSOR_EVENT_WEBHOOK_SECRET": "secret"}, clear=False)
    @patch("app.routers.alerts.process_new_sensor_event")
    def test_endpoint_rejects_missing_secret(self, process_mock):
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(
                sensor_event_webhook(
                    self.make_payload(),
                    x_aquamonitor_webhook_secret=None,
                )
            )

        self.assertEqual(raised.exception.status_code, 401)
        process_mock.assert_not_called()

    @patch.dict(os.environ, {"SENSOR_EVENT_WEBHOOK_SECRET": "secret"}, clear=False)
    @patch("app.routers.alerts.process_new_sensor_event")
    def test_endpoint_rejects_wrong_secret(self, process_mock):
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(
                sensor_event_webhook(
                    self.make_payload(),
                    x_aquamonitor_webhook_secret="wrong",
                )
            )

        self.assertEqual(raised.exception.status_code, 401)
        process_mock.assert_not_called()

    @patch.dict(os.environ, {"SENSOR_EVENT_WEBHOOK_SECRET": "secret"}, clear=False)
    @patch("app.routers.alerts.process_new_sensor_event", return_value=VALID_RESPONSE)
    def test_endpoint_accepts_valid_secret(self, process_mock):
        response = asyncio.run(
            sensor_event_webhook(
                self.make_payload(),
                x_aquamonitor_webhook_secret="secret",
            )
        )

        self.assertEqual(response["event_id"], "sensores/doc-1")
        process_mock.assert_called_once()

    @patch.dict(os.environ, {"SENSOR_EVENT_WEBHOOK_SECRET": ""}, clear=False)
    @patch("app.routers.alerts.process_new_sensor_event", return_value=VALID_RESPONSE)
    def test_endpoint_accepts_legacy_payload_when_secret_not_configured(self, _):
        response = asyncio.run(
            sensor_event_webhook(
                SensorEventIn(
                    sensor="alto",
                    estado="subiu",
                    timestamp="2026-07-27T12:05:00Z",
                )
            )
        )

        self.assertEqual(response["event_id"], "sensores/doc-1")


class SensorEventIdempotencyTests(unittest.TestCase):
    @patch("app.services.sensor_realtime.reserve_sensor_event_processing")
    @patch("app.services.sensor_realtime._engine")
    def test_duplicate_event_is_not_processed_again(self, engine_mock, reserve_mock):
        reserve_mock.return_value = SensorEventReservation(
            event_id="sensores/doc-1",
            processing_key="processing-key",
            payload_hash="hash",
            duplicate=True,
            existing_status="processed",
            payload_hash_mismatch=False,
        )

        result = process_new_sensor_event(
            {
                "document_id": "doc-1",
                "sensor": "baixo",
                "estado": "desceu",
                "timestamp": datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc),
            }
        )

        self.assertTrue(result["duplicate"])
        self.assertFalse(result["processed"])
        engine_mock.process_event.assert_not_called()


if __name__ == "__main__":
    unittest.main()
