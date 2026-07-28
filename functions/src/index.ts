import { onDocumentCreated } from "firebase-functions/v2/firestore";
import * as logger from "firebase-functions/logger";

import {
  BACKEND_SENSOR_EVENT_URL,
  FUNCTION_REGION,
  SENSOR_DOCUMENT_PATH,
  SENSOR_EVENT_WEBHOOK_SECRET,
} from "./config";
import { buildSensorEventPayload, buildWebhookHeaders } from "./payload";

export const onSensorCreated = onDocumentCreated(
  {
    document: SENSOR_DOCUMENT_PATH,
    region: FUNCTION_REGION,
    secrets: [SENSOR_EVENT_WEBHOOK_SECRET],
    timeoutSeconds: 30,
    retry: true,
  },
  async (event) => {
    const snapshot = event.data;
    if (!snapshot) {
      logger.warn("Sensor event trigger received no snapshot data", {
        params: event.params,
      });
      return;
    }

    const backendUrl = BACKEND_SENSOR_EVENT_URL.value();
    if (!backendUrl) {
      throw new Error("BACKEND_SENSOR_EVENT_URL is not configured");
    }

    const payload = buildSensorEventPayload(snapshot, event.params.docId);
    if (!payload) {
      logger.warn("Sensor event trigger received empty document data", {
        document_id: event.params.docId,
      });
      return;
    }

    const response = await fetch(backendUrl, {
      method: "POST",
      headers: buildWebhookHeaders(SENSOR_EVENT_WEBHOOK_SECRET.value()),
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const responseBody = await response.text().catch(() => "");
      logger.error("Backend sensor webhook failed", {
        event_id: payload.event_id,
        status: response.status,
        response_body: responseBody.slice(0, 500),
      });
      throw new Error(`Backend webhook failed with HTTP ${response.status}`);
    }

    logger.info("Sensor event delivered to backend", {
      event_id: payload.event_id,
      document_id: payload.document_id,
      status: response.status,
    });
  },
);
