const { onDocumentCreated } = require("firebase-functions/v2/firestore");

exports.onSensorCreated = onDocumentCreated("sensores/{docId}", async (event) => {
  const snapshot = event.data;
  if (!snapshot) return;

  const backendWebhookUrl = process.env.BACKEND_WEBHOOK_URL;
  if (!backendWebhookUrl) {
    throw new Error("BACKEND_WEBHOOK_URL is not configured");
  }

  const data = snapshot.data();
  if (!data) return;

  const timestamp =
    data.timestamp && typeof data.timestamp.toDate === "function"
      ? data.timestamp.toDate().toISOString()
      : new Date().toISOString();

  const body = {
    sensor: data.sensor,
    estado: data.estado,
    timestamp,
    device_id: data.device_id || null,
  };

  const response = await fetch(backendWebhookUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`Backend webhook failed with HTTP ${response.status}`);
  }
});
