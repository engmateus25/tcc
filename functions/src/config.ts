import { defineSecret, defineString } from "firebase-functions/params";

export const BACKEND_SENSOR_EVENT_URL = defineString("BACKEND_SENSOR_EVENT_URL");
export const BACKEND_COMMAND_EVENT_URL = defineString("BACKEND_COMMAND_EVENT_URL", {
  default: "",
});
export const FUNCTION_REGION = defineString("FUNCTION_REGION", {
  default: "us-central1",
});
export const SENSOR_EVENT_WEBHOOK_SECRET = defineSecret(
  "SENSOR_EVENT_WEBHOOK_SECRET",
);

export const SENSOR_DOCUMENT_PATH = "sensores/{docId}";
export const COMMAND_DOCUMENT_PATH = "comandos/{docId}";
export const SENSOR_EVENT_SECRET_HEADER = "X-AquaMonitor-Webhook-Secret";
export const SENSOR_EVENT_SOURCE = "firestore_on_create";
export const COMMAND_EVENT_SOURCE = "firestore_on_create";
