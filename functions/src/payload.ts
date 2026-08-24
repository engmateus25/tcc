import {
  COMMAND_EVENT_SOURCE,
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

export type CommandEventPayload = {
  document_id: string;
  event_id: string;
  command_id: unknown | null;
  timestamp: string;
  device_id: unknown | null;
  source: string;
  raw_path: string;
  received_at: string;
  bomba: unknown | null;
  acionamento: unknown | null;
  requested_state: unknown | null;
  applied_state: unknown | null;
  applied: unknown | null;
  confirmed: unknown | null;
  state_changed: unknown | null;
  priority: unknown | null;
  overridden_by: unknown | null;
  reason: unknown | null;
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

export function buildCommandEventPayload(
  snapshot: FirestoreSnapshotLike,
  documentId: string,
  receivedAt = new Date(),
): CommandEventPayload | null {
  const data = snapshot.data();
  if (!data) {
    return null;
  }

  const rawPath = snapshot.ref?.path || `comandos/${documentId}`;
  const commandId = data.command_id || documentId;
  const eventId = normalizeString(data.event_id) || rawPath;

  return {
    document_id: documentId,
    event_id: eventId,
    command_id: commandId,
    timestamp: normalizeTimestamp(data.timestamp || data.applied_at || data.created_at, receivedAt),
    device_id: data.device_id || null,
    source: COMMAND_EVENT_SOURCE,
    raw_path: rawPath,
    received_at: receivedAt.toISOString(),
    bomba: data.bomba || null,
    acionamento: data.acionamento || null,
    requested_state: data.requested_state ?? null,
    applied_state: data.applied_state ?? data.pump_on ?? null,
    applied: data.applied ?? data.state_changed ?? null,
    confirmed: data.confirmed ?? null,
    state_changed: data.state_changed ?? null,
    priority: data.priority || null,
    overridden_by: data.overridden_by || null,
    reason: data.reason || null,
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
