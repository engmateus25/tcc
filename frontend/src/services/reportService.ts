const BASE_URL = import.meta.env.VITE_AI_BASE_URL || "http://127.0.0.1:8000";

export type ReportPeriod = "7d" | "30d" | "90d";

export interface SensorSummary {
  total_events: number;
  by_sensor: Record<string, number>;
  by_action: Record<string, number>;
}

export interface WaterConsumptionSummary {
  period: ReportPeriod;
  cycle_count: number;
  volume_between_sensors_liters: number;
  total_liters: number;
  total_cubic_meters: number;
  water_price_per_cubic_meter_brl: number;
  total_cost_brl: number;
  average_liters_per_day: number;
  daily: Array<{
    date: string;
    cycles: number;
    liters: number;
    cost_brl: number;
  }>;
  estimated: boolean;
  basis: string;
}

export interface PumpEnergySummary {
  period: ReportPeriod;
  pump_power_kw: number;
  electricity_price_per_kwh_brl: number;
  total_on_seconds: number;
  total_on_minutes: number;
  total_on_hours: number;
  total_kwh: number;
  total_cost_brl: number;
  confirmed_event_count: number;
  ignored_event_count: number;
  daily: Array<{
    date: string;
    on_seconds: number;
    kwh: number;
    cost_brl: number;
  }>;
  estimated: boolean;
  basis: string;
}

export interface ReportSummary {
  period: ReportPeriod;
  sensor_summary: SensorSummary;
  water_consumption: WaterConsumptionSummary;
  pump_energy: PumpEnergySummary;
  alerts: Array<Record<string, unknown>>;
}

export async function fetchReportSummary(
  period: ReportPeriod,
): Promise<ReportSummary> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}/reports/summary?period=${period}`);
  } catch {
    throw new Error("Não foi possível conectar ao backend de relatórios");
  }
  if (!response.ok) {
    throw new Error(await getApiErrorMessage(response));
  }
  return response.json() as Promise<ReportSummary>;
}

export async function downloadReportPdf(period: ReportPeriod): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}/reports/weekly?period=${period}`);
  } catch {
    throw new Error("Não foi possível conectar ao backend de relatórios");
  }
  if (!response.ok) {
    throw new Error(await getApiErrorMessage(response));
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = getReportFilename(response, period);
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

function getReportFilename(response: Response, period: ReportPeriod) {
  const disposition = response.headers.get("content-disposition") || "";
  const match = disposition.match(/filename="?([^";]+)"?/i);
  return match?.[1] || `relatorio_${period}.pdf`;
}

async function getApiErrorMessage(response: Response): Promise<string> {
  try {
    const data = await response.json() as { detail?: unknown };
    if (typeof data.detail === "string") {
      return data.detail;
    }
  } catch {
    // Mantem fallback abaixo quando a resposta nao for JSON.
  }
  return `HTTP ${response.status}`;
}
