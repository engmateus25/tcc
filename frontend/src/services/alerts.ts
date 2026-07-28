const BASE_URL = import.meta.env.VITE_AI_BASE_URL || "http://127.0.0.1:8000";

export type AlertSeverity = "info" | "warning" | "error" | "critical" | string;
export type AlertStatus = "open" | "acknowledged" | string;

export interface AquaAlert {
  id: string;
  event_id: string;
  type: string;
  severity: AlertSeverity;
  title: string;
  message: string;
  detected_at?: string;
  sensor_timestamp?: string | null;
  status: AlertStatus;
  possible_causes: string[];
  metadata: Record<string, unknown>;
  acknowledged: boolean;
  acknowledged_at?: string | null;
}

export interface AlertListResponse {
  total: number;
  alerts: AquaAlert[];
}

export interface AlertAcknowledgeResponse {
  id: string;
  acknowledged: boolean;
  status: AlertStatus;
  acknowledged_at: string;
}

export interface AlertQuery {
  period?: string;
  status?: AlertStatus;
  severity?: AlertSeverity;
  limit?: number;
}

export async function fetchAlerts(query: AlertQuery = {}): Promise<AlertListResponse> {
  const params = new URLSearchParams();
  params.set("period", query.period || "7d");
  params.set("limit", String(query.limit || 20));
  if (query.status) {
    params.set("status", query.status);
  }
  if (query.severity) {
    params.set("severity", query.severity);
  }

  const response = await fetch(`${BASE_URL}/alerts?${params.toString()}`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json() as Promise<AlertListResponse>;
}

export async function acknowledgeAlert(
  alertId: string,
): Promise<AlertAcknowledgeResponse> {
  const response = await fetch(`${BASE_URL}/alerts/${encodeURIComponent(alertId)}/ack`, {
    method: "PATCH",
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json() as Promise<AlertAcknowledgeResponse>;
}
