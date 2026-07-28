import {
  Activity,
  AlertTriangle,
  Check,
  Clock3,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";
import { AquaAlert } from "../services/alerts";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";

interface IntelligentAlertsPanelProps {
  alerts: AquaAlert[];
  isLoading: boolean;
  isRefreshing: boolean;
  error: string | null;
  lastUpdatedAt: Date | null;
  acknowledgingId: string | null;
  onRefresh: () => void;
  onAcknowledge: (alertId: string) => void;
}

export function IntelligentAlertsPanel({
  alerts,
  isLoading,
  isRefreshing,
  error,
  lastUpdatedAt,
  acknowledgingId,
  onRefresh,
  onAcknowledge,
}: IntelligentAlertsPanelProps) {
  const criticalCount = alerts.filter((alert) =>
    ["error", "critical"].includes(alert.severity),
  ).length;

  return (
    <section className="bg-white rounded-2xl shadow-lg border border-slate-100 p-4 mb-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-slate-100 text-slate-700">
            <ShieldAlert className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-base text-slate-800">Alertas inteligentes</h2>
            <p className="text-xs text-slate-500">
              {alerts.length} aberto{alerts.length === 1 ? "" : "s"}
              {criticalCount > 0 ? ` · ${criticalCount} crítico${criticalCount === 1 ? "" : "s"}` : ""}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {lastUpdatedAt && (
            <span className="hidden text-xs text-slate-500 sm:inline">
              {lastUpdatedAt.toLocaleTimeString("pt-BR", {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          )}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={isRefreshing}
            title="Atualizar alertas"
          >
            <RefreshCw className={isRefreshing ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
            Atualizar
          </Button>
        </div>
      </div>

      <div className="mt-4 space-y-3">
        {isLoading && <AlertSkeleton />}

        {!isLoading && error && (
          <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            Falha ao carregar alertas: {error}
          </div>
        )}

        {!isLoading && !error && alerts.length === 0 && (
          <div className="rounded-md border border-green-200 bg-green-50 px-3 py-3 text-sm text-green-700">
            Nenhum alerta aberto.
          </div>
        )}

        {!isLoading &&
          alerts.map((alert) => (
            <AlertRow
              key={alert.id}
              alert={alert}
              isAcknowledging={acknowledgingId === alert.id}
              onAcknowledge={onAcknowledge}
            />
          ))}
      </div>
    </section>
  );
}

function AlertRow({
  alert,
  isAcknowledging,
  onAcknowledge,
}: {
  alert: AquaAlert;
  isAcknowledging: boolean;
  onAcknowledge: (alertId: string) => void;
}) {
  const Icon = alert.type.includes("fill") ? Activity : AlertTriangle;

  return (
    <article className="rounded-md border border-slate-200 bg-slate-50 px-3 py-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Icon className={`h-4 w-4 ${severityIconClass(alert.severity)}`} />
            <h3 className="text-sm text-slate-800">{alert.title || alert.type}</h3>
            <Badge variant="outline" className={severityBadgeClass(alert.severity)}>
              {severityLabel(alert.severity)}
            </Badge>
            <Badge variant="secondary" className="bg-white text-slate-600">
              {typeLabel(alert.type)}
            </Badge>
          </div>

          {alert.message && (
            <p className="mt-1 text-sm text-slate-600">{alert.message}</p>
          )}

          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <Clock3 className="h-3.5 w-3.5" />
            <span>{formatAlertDate(alert.sensor_timestamp || alert.detected_at)}</span>
            {alert.possible_causes?.slice(0, 2).map((cause) => (
              <span key={cause} className="rounded-sm bg-white px-2 py-0.5">
                {cause}
              </span>
            ))}
          </div>
        </div>

        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => onAcknowledge(alert.id)}
          disabled={isAcknowledging}
          title="Reconhecer alerta"
        >
          <Check className="h-4 w-4" />
          Reconhecer
        </Button>
      </div>
    </article>
  );
}

function AlertSkeleton() {
  return (
    <div className="space-y-3">
      {[0, 1].map((item) => (
        <div key={item} className="rounded-md border border-slate-200 bg-slate-50 p-3">
          <div className="h-4 w-2/3 rounded-sm bg-slate-200" />
          <div className="mt-3 h-3 w-full rounded-sm bg-slate-200" />
          <div className="mt-2 h-3 w-1/2 rounded-sm bg-slate-200" />
        </div>
      ))}
    </div>
  );
}

function severityLabel(severity: string) {
  const labels: Record<string, string> = {
    info: "Info",
    warning: "Atenção",
    error: "Erro",
    critical: "Crítico",
  };
  return labels[severity] || severity;
}

function typeLabel(type: string) {
  const labels: Record<string, string> = {
    duplicate_event: "Duplicidade",
    unexpected_low_repeat: "Sequência",
    unexpected_high_without_low: "Sequência",
    low_dropped_while_high_active: "Sequência",
    implausible_drain_time: "Esvaziamento",
    out_of_order_event: "Ordem",
    missing_timestamp: "Timestamp",
    slow_fill_cycle: "Enchimento lento",
    persistent_fill_time_shift: "Tendência",
    new_fill_time_cluster: "Novo padrão",
  };
  return labels[type] || type.replaceAll("_", " ");
}

function severityIconClass(severity: string) {
  if (severity === "critical" || severity === "error") {
    return "text-red-600";
  }
  if (severity === "warning") {
    return "text-amber-600";
  }
  return "text-blue-600";
}

function severityBadgeClass(severity: string) {
  if (severity === "critical" || severity === "error") {
    return "border-red-200 bg-red-50 text-red-700";
  }
  if (severity === "warning") {
    return "border-amber-200 bg-yellow-100 text-amber-700";
  }
  return "border-blue-200 bg-blue-50 text-blue-700";
}

function formatAlertDate(value?: string | null) {
  if (!value) {
    return "sem horario";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "horario invalido";
  }
  return date.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
