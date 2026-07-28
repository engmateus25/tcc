const { onDocumentCreated } = require("firebase-functions/v2/firestore");

exports.onSensorCreated = onDocumentCreated("sensores/{docId}", async (event) => {
  const snapshot = event.data;
  if (!snapshot) return;

  const backendWebhookUrl =
    process.env.BACKEND_SENSOR_EVENT_URL || process.env.BACKEND_WEBHOOK_URL;
  if (!backendWebhookUrl) {
    throw new Error("BACKEND_SENSOR_EVENT_URL is not configured");
  }

  const data = snapshot.data();
  if (!data) return;

  const timestamp =
    data.timestamp && typeof data.timestamp.toDate === "function"
      ? data.timestamp.toDate().toISOString()
      : new Date().toISOString();

  const documentId = event.params.docId;
  const eventId = data.event_id || `sensores/${documentId}`;

  const body = {
    document_id: documentId,
    event_id: eventId,
    sensor: data.sensor,
    estado: data.estado,
    timestamp,
    device_id: data.device_id || null,
    source: "firestore_on_create",
    raw_path: snapshot.ref.path,
    received_at: new Date().toISOString(),
  };

  const headers = { "Content-Type": "application/json" };
  if (process.env.SENSOR_EVENT_WEBHOOK_SECRET) {
    headers["X-AquaMonitor-Webhook-Secret"] =
      process.env.SENSOR_EVENT_WEBHOOK_SECRET;
  }

  const response = await fetch(backendWebhookUrl, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`Backend webhook failed with HTTP ${response.status}`);
  }
});
