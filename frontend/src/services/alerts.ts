import { API_BASE_URL } from "./env";

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

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/alerts?${params.toString()}`);
  } catch {
    throw new Error("Não foi possível conectar ao backend de alertas");
  }
  if (!response.ok) {
    throw new Error(await getApiErrorMessage(response));
  }
  return response.json() as Promise<AlertListResponse>;
}

export async function acknowledgeAlert(
  alertId: string,
): Promise<AlertAcknowledgeResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/alerts/${encodeURIComponent(alertId)}/ack`, {
      method: "PATCH",
    });
  } catch {
    throw new Error("Não foi possível conectar ao backend de alertas");
  }
  if (!response.ok) {
    throw new Error(await getApiErrorMessage(response));
  }
  return response.json() as Promise<AlertAcknowledgeResponse>;
}

async function getApiErrorMessage(response: Response): Promise<string> {
  try {
    const data = await response.json() as { detail?: unknown };
    if (typeof data.detail === "string") {
      return data.detail;
    }
  } catch {
    // Mantem o fallback HTTP abaixo quando a resposta nao for JSON.
  }
  return `HTTP ${response.status}`;
}
