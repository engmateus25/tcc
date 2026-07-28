import assert from "node:assert/strict";
import test from "node:test";

import {
  buildSensorEventPayload,
  buildWebhookHeaders,
  normalizeTimestamp,
} from "../src/payload";

test("buildSensorEventPayload maps Firestore data to backend contract", () => {
  const receivedAt = new Date("2026-07-27T12:00:01.000Z");
  const payload = buildSensorEventPayload(
    {
      data: () => ({
        sensor: "baixo",
        estado: "desceu",
        timestamp: {
          toDate: () => new Date("2026-07-27T12:00:00.000Z"),
        },
        device_id: "esp32-reservatorio-01",
      }),
      ref: { path: "sensores/doc-1" },
    },
    "doc-1",
    receivedAt,
  );

  assert.deepEqual(payload, {
    document_id: "doc-1",
    event_id: "sensores/doc-1",
    sensor: "baixo",
    estado: "desceu",
    timestamp: "2026-07-27T12:00:00.000Z",
    device_id: "esp32-reservatorio-01",
    source: "firestore_on_create",
    raw_path: "sensores/doc-1",
    received_at: "2026-07-27T12:00:01.000Z",
  });
});

test("buildSensorEventPayload preserves explicit event_id", () => {
  const payload = buildSensorEventPayload(
    {
      data: () => ({
        event_id: "device-event-1",
        sensor: "alto",
        estado: "subiu",
        timestamp: "2026-07-27T12:05:00Z",
      }),
      ref: { path: "sensores/doc-2" },
    },
    "doc-2",
    new Date("2026-07-27T12:05:01.000Z"),
  );

  assert.equal(payload?.event_id, "device-event-1");
  assert.equal(payload?.raw_path, "sensores/doc-2");
});

test("normalizeTimestamp supports Firestore seconds/nanoseconds", () => {
  assert.equal(
    normalizeTimestamp({ seconds: 1785153600, nanoseconds: 500000000 }),
    "2026-07-27T12:00:00.500Z",
  );
});

test("normalizeTimestamp falls back when timestamp is missing", () => {
  assert.equal(
    normalizeTimestamp(undefined, new Date("2026-07-27T12:00:01.000Z")),
    "2026-07-27T12:00:01.000Z",
  );
});

test("buildWebhookHeaders includes secret only when configured", () => {
  assert.deepEqual(buildWebhookHeaders(), {
    "Content-Type": "application/json",
  });
  assert.deepEqual(buildWebhookHeaders("secret"), {
    "Content-Type": "application/json",
    "X-AquaMonitor-Webhook-Secret": "secret",
  });
});
