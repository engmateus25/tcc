import {
  SENSOR_EVENT_SECRET_HEADER,
  SENSOR_EVENT_SOURCE,
} from "./config";

export type FirestoreTimestampLike = {
  toDate?: () => Date;
  seconds?: number;
  nanoseconds?: number;
};

export type FirestoreSnapshotLike = {
  data: () => Record<string, unknown> | undefined;
  ref?: {
    path?: string;
  };
};

export type SensorEventPayload = {
  document_id: string;
  event_id: string;
  sensor: unknown;
  estado: unknown;
  timestamp: string;
  device_id: unknown | null;
  source: string;
  raw_path: string;
  received_at: string;
};

export function buildSensorEventPayload(
  snapshot: FirestoreSnapshotLike,
  documentId: string,
  receivedAt = new Date(),
): SensorEventPayload | null {
  const data = snapshot.data();
  if (!data) {
    return null;
  }

  const rawPath = snapshot.ref?.path || `sensores/${documentId}`;
  const eventId = normalizeString(data.event_id) || rawPath;

  return {
    document_id: documentId,
    event_id: eventId,
    sensor: data.sensor,
    estado: data.estado,
    timestamp: normalizeTimestamp(data.timestamp, receivedAt),
    device_id: data.device_id || null,
    source: SENSOR_EVENT_SOURCE,
    raw_path: rawPath,
    received_at: receivedAt.toISOString(),
  };
}

export function buildWebhookHeaders(
  webhookSecret?: string,
): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (webhookSecret) {
    headers[SENSOR_EVENT_SECRET_HEADER] = webhookSecret;
  }

  return headers;
}

export function normalizeTimestamp(
  timestamp: unknown,
  fallbackDate = new Date(),
): string {
  if (timestamp instanceof Date) {
    return timestamp.toISOString();
  }

  if (typeof timestamp === "string" && timestamp.trim()) {
    const parsed = new Date(timestamp);
    if (!Number.isNaN(parsed.getTime())) {
      return parsed.toISOString();
    }
  }

  if (isFirestoreTimestampLike(timestamp)) {
    if (typeof timestamp.toDate === "function") {
      return timestamp.toDate().toISOString();
    }

    if (typeof timestamp.seconds === "number") {
      const milliseconds =
        timestamp.seconds * 1000 +
        Math.floor((timestamp.nanoseconds || 0) / 1_000_000);
      return new Date(milliseconds).toISOString();
    }
  }

  return fallbackDate.toISOString();
}

function isFirestoreTimestampLike(
  value: unknown,
): value is FirestoreTimestampLike {
  return typeof value === "object" && value !== null;
}

function normalizeString(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed || null;
}
