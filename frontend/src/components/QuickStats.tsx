import { Card } from "./ui/card";
import { Droplets, Power, TrendingUp } from "lucide-react";
import { useEffect, useState } from "react";
import { fetchReportSummary } from "../services/reportService";

interface QuickStatsProps {
  waterLevel: number;
  isPumpOn: boolean;
  dailyUsage?: number | null;
}

export function QuickStats({ waterLevel, isPumpOn, dailyUsage = null }: QuickStatsProps) {
  const [averageDailyUsage, setAverageDailyUsage] = useState<number | null>(dailyUsage);

  useEffect(() => {
    if (dailyUsage !== null && dailyUsage !== undefined) {
      setAverageDailyUsage(dailyUsage);
      return;
    }

    let active = true;
    async function loadUsage() {
      try {
        const summary = await fetchReportSummary("7d");
        if (!active) return;
        setAverageDailyUsage(summary.water_consumption.average_liters_per_day);
      } catch {
        if (active) setAverageDailyUsage(null);
      }
    }

    void loadUsage();
    const interval = window.setInterval(() => {
      void loadUsage();
    }, 60000);

    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [dailyUsage]);

  const tankCapacityLiters = 5000;
  const currentLiters = Math.round((waterLevel / 100) * tankCapacityLiters);
  const usageText =
    averageDailyUsage !== null
      ? `${Math.round(averageDailyUsage).toLocaleString("pt-BR")}L`
      : "--";

  return (
    <div className="grid grid-cols-3 gap-3 mb-6">
      {/* Volume Atual */}
      <Card className="p-3 bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
        <div className="flex flex-col items-center text-center">
          <Droplets className="w-5 h-5 text-blue-600 mb-1" />
          <p className="text-xs text-blue-600 mb-1">Volume</p>
          <p className="text-lg text-blue-800">{currentLiters}L</p>
          <p className="text-xs text-blue-500">de {tankCapacityLiters}L</p>
        </div>
      </Card>

      {/* Status da Bomba */}
      <Card className={`p-3 bg-gradient-to-br ${isPumpOn ? 'from-green-50 to-green-100 border-green-200' : 'from-slate-50 to-slate-100 border-slate-200'}`}>
        <div className="flex flex-col items-center text-center">
          <Power className={`w-5 h-5 mb-1 ${isPumpOn ? 'text-green-600' : 'text-slate-400'}`} />
          <p className={`text-xs mb-1 ${isPumpOn ? 'text-green-600' : 'text-slate-400'}`}>Bomba</p>
          <p className={`text-lg ${isPumpOn ? 'text-green-800' : 'text-slate-600'}`}>
            {isPumpOn ? 'Ligada' : 'Desligada'}
          </p>
          <p className={`text-xs ${isPumpOn ? 'text-green-500' : 'text-slate-400'}`}>
            {isPumpOn ? 'Ativa' : 'Inativa'}
          </p>
        </div>
      </Card>

      {/* Consumo Diário */}
      <Card className="p-3 bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200">
        <div className="flex flex-col items-center text-center">
          <TrendingUp className="w-5 h-5 text-purple-600 mb-1" />
          <p className="text-xs text-purple-600 mb-1">Média/dia</p>
          <p className="text-lg text-purple-800">{usageText}</p>
          <p className="text-xs text-purple-500">últimos 7 dias</p>
        </div>
      </Card>
    </div>
  );
}
