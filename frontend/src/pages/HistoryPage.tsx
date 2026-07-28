import { useEffect, useMemo, useState } from "react";
import { useHistory } from "react-router-dom";
import { 
  ArrowLeft, Download, Calendar, TrendingDown,
  Droplets, Zap, MessageSquare,
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import {
  Tabs, TabsContent, TabsList, TabsTrigger,
} from "../components/ui/tabs";
import {
  BarChart, Bar, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from "recharts";
import {
  downloadReportPdf,
  fetchReportSummary,
  ReportPeriod,
  ReportSummary,
} from "../services/reportService";


export function HistoryPage() {
  const history = useHistory();
  const [selectedPeriod, setSelectedPeriod] = useState<ReportPeriod>("7d");
  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    async function loadSummary() {
      setIsLoading(true);
      try {
        const response = await fetchReportSummary(selectedPeriod);
        if (!active) return;
        setSummary(response);
        setError(null);
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Erro ao carregar histórico");
      } finally {
        if (active) setIsLoading(false);
      }
    }
    void loadSummary();
    return () => {
      active = false;
    };
  }, [selectedPeriod]);

  const waterChartData = useMemo(
    () =>
      summary?.water_consumption.daily.map((item) => ({
        date: formatShortDate(item.date),
        consumption: Math.round(item.liters),
        cost: Number(item.cost_brl.toFixed(2)),
      })) ?? [],
    [summary],
  );

  const energyData = useMemo(
    () =>
      summary?.pump_energy.daily.map((item) => ({
        date: formatShortDate(item.date),
        energy: Number(item.kwh.toFixed(3)),
        cost: Number(item.cost_brl.toFixed(2)),
      })) ?? [],
    [summary],
  );

  const sensorData = useMemo(
    () =>
      Object.entries(summary?.sensor_summary.by_sensor ?? {}).map(([sensor, count]) => ({
        sensor,
        count,
      })),
    [summary],
  );

  const handleGeneratePDF = async () => {
    setIsDownloading(true);
    try {
      await downloadReportPdf(selectedPeriod);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao baixar PDF");
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <>
      {/* Header da página */}
      <div className="flex items-center gap-3 mb-6">
        <Button
          variant="ghost"
          // se seu Button não suporta "size", pode remover a prop e usar classes
          size="icon"
          onClick={() => history.push("/home")}
          className="shrink-0"
        >
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div className="flex-1">
          <h2 className="text-xl text-slate-800">Histórico e Estatísticas</h2>
          <p className="text-sm text-slate-500">Análise de consumo e custos</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleGeneratePDF}
          disabled={isDownloading}
          className="shrink-0"
        >
          <Download className="w-4 h-4 mr-2" />
          {isDownloading ? "Baixando" : "PDF"}
        </Button>
      </div>

      {error && (
        <Card className="mb-6 border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </Card>
      )}

      {/* Cards de Resumo */}
      <div className="grid grid-cols-2 gap-3 mb-6">
        <Card className="p-4 bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
          <div className="flex items-start justify-between mb-2">
            <Droplets className="w-5 h-5 text-blue-600" />
            <Badge variant="secondary" className="text-xs">
              Média
            </Badge>
          </div>
          <p className="text-2xl text-blue-800 mb-1">
            {formatLiters(summary?.water_consumption.total_liters ?? 0)}
          </p>
          <p className="text-xs text-blue-600">Água estimada</p>
          <div className="flex items-center gap-1 mt-2 text-xs text-blue-600">
            <TrendingDown className="w-3 h-3" />
            <span>{summary?.water_consumption.cycle_count ?? 0} ciclo(s)</span>
          </div>
        </Card>

        <Card className="p-4 bg-gradient-to-br from-yellow-50 to-yellow-100 border-yellow-200">
          <div className="flex items-start justify-between mb-2">
            <Zap className="w-5 h-5 text-yellow-600" />
            <Badge variant="secondary" className="text-xs">
              Total
            </Badge>
          </div>
          <p className="text-2xl text-yellow-800 mb-1">
            {formatCurrency(summary?.pump_energy.total_cost_brl ?? 0)}
          </p>
          <p className="text-xs text-yellow-600">Custo energia</p>
          <div className="flex items-center gap-1 mt-2 text-xs text-yellow-700">
            <Zap className="w-3 h-3" />
            <span>{formatKwh(summary?.pump_energy.total_kwh ?? 0)}</span>
          </div>
        </Card>
      </div>

      {/* Seletor de Período */}
      <Card className="p-4 mb-6">
        <div className="flex items-center gap-2 mb-3">
          <Calendar className="w-4 h-4 text-slate-600" />
          <span className="text-sm text-slate-700">Período:</span>
        </div>
        <div className="grid grid-cols-3 gap-2">
          <Button
            variant={selectedPeriod === "7d" ? "default" : "outline"}
            size="sm"
            onClick={() => setSelectedPeriod("7d")}
          >
            7 dias
          </Button>
          <Button
            variant={selectedPeriod === "30d" ? "default" : "outline"}
            size="sm"
            onClick={() => setSelectedPeriod("30d")}
          >
            30 dias
          </Button>
          <Button
            variant={selectedPeriod === "90d" ? "default" : "outline"}
            size="sm"
            onClick={() => setSelectedPeriod("90d")}
          >
            90 dias
          </Button>
        </div>
      </Card>

      {/* Tabs com Gráficos */}
      <Tabs defaultValue="water" className="mb-6">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="water">Água</TabsTrigger>
          <TabsTrigger value="energy">Energia</TabsTrigger>
          <TabsTrigger value="sensors">Sensores</TabsTrigger>
        </TabsList>

        {/* Gráfico de Consumo de Água */}
        <TabsContent value="water">
          <Card className="p-4">
            <h3 className="text-sm text-slate-700 mb-4">Consumo de Água (Litros)</h3>
            {isLoading || waterChartData.length === 0 ? (
              <EmptyChartText isLoading={isLoading} />
            ) : (
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={waterChartData}>
                  <defs>
                    <linearGradient id="colorConsumption" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="date" style={{ fontSize: "12px" }} />
                  <YAxis style={{ fontSize: "12px" }} />
                  <Tooltip />
                  <Area
                    type="monotone"
                    dataKey="consumption"
                    stroke="#3b82f6"
                    fill="url(#colorConsumption)"
                    strokeWidth={2}
                    name="Consumo (L)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </Card>
        </TabsContent>

        {/* Gráfico de Energia */}
        <TabsContent value="energy">
          <Card className="p-4">
            <h3 className="text-sm text-slate-700 mb-4">Consumo de Energia e Custo</h3>
            {isLoading || energyData.length === 0 ? (
              <EmptyChartText isLoading={isLoading} />
            ) : (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={energyData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="date" style={{ fontSize: "12px" }} />
                  <YAxis yAxisId="left" style={{ fontSize: "12px" }} />
                  <YAxis yAxisId="right" orientation="right" style={{ fontSize: "12px" }} />
                  <Tooltip />
                  <Legend />
                  <Bar yAxisId="left" dataKey="energy" fill="#eab308" name="Energia (kWh)" />
                  <Bar yAxisId="right" dataKey="cost" fill="#22c55e" name="Custo (R$)" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>
        </TabsContent>

        {/* Eventos por sensor */}
        <TabsContent value="sensors">
          <Card className="p-4">
            <h3 className="text-sm text-slate-700 mb-4">Eventos por Sensor</h3>
            {isLoading || sensorData.length === 0 ? (
              <EmptyChartText isLoading={isLoading} />
            ) : (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={sensorData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="sensor" style={{ fontSize: "12px" }} />
                  <YAxis style={{ fontSize: "12px" }} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#0f766e" name="Eventos" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>
        </TabsContent>
      </Tabs>

      {/* Chatbot Placeholder */}
      <Card className="p-4 bg-slate-50 border-slate-200">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-slate-700 rounded-md">
            <MessageSquare className="w-5 h-5 text-white" />
          </div>
          <div className="flex-1">
            <h3 className="text-sm text-slate-800 mb-1">Assistente IA</h3>
            <p className="text-xs text-slate-600 mb-3">
              Analise os dados do período atual com perguntas em linguagem natural.
            </p>
            <Button
              variant="default"
              size="sm"
              className="bg-slate-700 hover:bg-slate-800"
              onClick={() => history.push("/chat")}
            >
              Abrir Chat
            </Button>
          </div>
        </div>
      </Card>

      {/* Insights */}
      <Card className="p-4 mt-6 bg-slate-50 border-slate-200">
        <h3 className="text-sm text-slate-700 mb-3">Insights</h3>
        <ul className="space-y-2 text-sm text-slate-600">
          <li className="flex items-start gap-2">
            <span className="text-blue-500 shrink-0">•</span>
            <span>
              Água estimada por ciclo: {formatLiters(summary?.water_consumption.volume_between_sensors_liters ?? 0)}.
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-orange-500 shrink-0">•</span>
            <span>
              {summary?.pump_energy.ignored_event_count ?? 0} comando(s) de bomba foram sobrepostos por prioridade.
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-green-500 shrink-0">•</span>
            <span>
              Energia baseada em {summary?.pump_energy.confirmed_event_count ?? 0} evento(s) confirmados de bomba.
            </span>
          </li>
        </ul>
      </Card>
    </>
  );
}

function EmptyChartText({ isLoading }: { isLoading: boolean }) {
  return (
    <div className="flex h-[250px] items-center justify-center rounded-md border border-dashed border-slate-200 text-sm text-slate-500">
      {isLoading ? "Carregando dados..." : "Sem dados para o período."}
    </div>
  );
}

function formatCurrency(value: number) {
  return value.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 2,
  });
}

function formatLiters(value: number) {
  return `${Math.round(value).toLocaleString("pt-BR")}L`;
}

function formatKwh(value: number) {
  return `${value.toFixed(3)} kWh`;
}

function formatShortDate(value: string) {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
  });
}
