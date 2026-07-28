import { useCallback, useEffect, useState } from "react";
import {
  acknowledgeAlert,
  AquaAlert,
  fetchAlerts,
} from "../services/alerts";

interface UseAlertsOptions {
  period?: string;
  status?: string;
  limit?: number;
  refreshMs?: number;
}

export function useAlerts({
  period = "7d",
  status = "open",
  limit = 20,
  refreshMs = 15000,
}: UseAlertsOptions = {}) {
  const [alerts, setAlerts] = useState<AquaAlert[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);
  const [acknowledgingId, setAcknowledgingId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const response = await fetchAlerts({ period, status, limit });
      setAlerts(response.alerts);
      setError(null);
      setLastUpdatedAt(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao buscar alertas");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [limit, period, status]);

  const acknowledge = useCallback(
    async (alertId: string) => {
      setAcknowledgingId(alertId);
      try {
        await acknowledgeAlert(alertId);
        await refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erro ao reconhecer alerta");
      } finally {
        setAcknowledgingId(null);
      }
    },
    [refresh],
  );

  useEffect(() => {
    void refresh();
    if (refreshMs <= 0) {
      return undefined;
    }
    const interval = window.setInterval(() => {
      void refresh();
    }, refreshMs);
    return () => window.clearInterval(interval);
  }, [refresh, refreshMs]);

  return {
    alerts,
    isLoading,
    isRefreshing,
    error,
    lastUpdatedAt,
    acknowledgingId,
    refresh,
    acknowledge,
  };
}
