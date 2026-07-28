import { Card } from "./ui/card";
import { useEffect, useState } from "react";
import { Clock, Zap } from "lucide-react";
import {
  fetchReportSummary,
  PumpEnergySummary,
} from "../services/reportService";

interface EnergyEstimateProps {
  isPumpOn: boolean;
  pumpPowerWatts?: number;
}

export function EnergyEstimate({ isPumpOn, pumpPowerWatts = 750 }: EnergyEstimateProps) {
  const [summary, setSummary] = useState<PumpEnergySummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    async function loadEnergy() {
      try {
        const report = await fetchReportSummary("7d");
        if (!active) return;
        setSummary(report.pump_energy);
        setError(null);
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Erro ao carregar energia");
      }
    }
    void loadEnergy();
    const interval = window.setInterval(() => {
      void loadEnergy();
    }, 60000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  const totalMinutes = Math.round(summary?.total_on_minutes ?? 0);
  const hours = summary?.total_on_hours ?? 0;
  const energyKwh = summary?.total_kwh ?? 0;
  const costEstimate = summary?.total_cost_brl ?? 0;
  const configuredPowerWatts = Math.round((summary?.pump_power_kw ?? pumpPowerWatts / 1000) * 1000);

  return (
    <Card className="p-4">
      <div className="flex items-center gap-2 mb-3">
        <Zap className="w-5 h-5 text-yellow-600" />
        <p className="text-sm text-slate-600">Energia da bomba</p>
      </div>

      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <span className="text-sm text-slate-600">Estado atual:</span>
          <span className={isPumpOn ? "text-sm text-green-700" : "text-sm text-slate-600"}>
            {isPumpOn ? "Ligada" : "Desligada"}
          </span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-sm text-slate-600">Tempo confirmado:</span>
          <div className="flex items-center gap-1">
            <Clock className="w-4 h-4 text-slate-500" />
            <span className="text-sm">
              {Math.floor(hours)}h {totalMinutes % 60}min
            </span>
          </div>
        </div>
        
        <div className="flex justify-between items-center">
          <span className="text-sm text-slate-600">Energia:</span>
          <span className="text-lg text-blue-600">{energyKwh.toFixed(3)} kWh</span>
        </div>
        
        <div className="flex justify-between items-center pt-2 border-t border-slate-200">
          <span className="text-sm text-slate-600">Custo estimado:</span>
          <span className="text-lg text-green-700">
            R$ {costEstimate.toFixed(2)}
          </span>
        </div>

        <p className="text-xs text-slate-400 mt-2">
          Baseado em eventos confirmados e {configuredPowerWatts}W configurados
        </p>
        {summary && summary.ignored_event_count > 0 && (
          <p className="text-xs text-amber-600">
            {summary.ignored_event_count} comando(s) sobreposto(s) não entraram no cálculo.
          </p>
        )}
        {error && <p className="text-xs text-red-600">{error}</p>}
      </div>
    </Card>
  );
}
