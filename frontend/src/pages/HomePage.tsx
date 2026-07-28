import { useHistory } from "react-router-dom";
import { WaterTankVisualization } from "../components/WaterTankVisualization";
import { SensorStatus } from "../components/SensorStatus";
import { PumpControl } from "../components/PumpControl";
import { PumpModeDisplay } from "../components/PumpModeDisplay";
import { EnergyEstimate } from "../components/EnergyEstimate";
import { WaterLevelAlert } from "../components/WaterLevelAlert";
import { IntelligentAlertsPanel } from "../components/IntelligentAlertsPanel";
import { QuickStats } from "../components/QuickStats";
import { BarChart3, MessageSquare } from "lucide-react";
import { Button } from "../components/ui/button";
import { useAlerts } from "../hooks/useAlerts";
import { useWaterSystem } from "../hooks/useWaterSystem";


export function HomePage() {
  const history = useHistory();

  const {
    waterLevel,
    isPumpOn,
    pumpMode,
    lastSensor,
    pendingPumpCommand,
    pumpStatusMessage,
    togglePump,
  } = useWaterSystem();

  const {
    alerts,
    isLoading: isLoadingAlerts,
    isRefreshing: isRefreshingAlerts,
    error: alertsError,
    lastUpdatedAt: alertsLastUpdatedAt,
    acknowledgingId,
    refresh: refreshAlerts,
    acknowledge: acknowledgeAlert,
  } = useAlerts();

  return (
    <>
      {/* Alerta de Nível */}
      <WaterLevelAlert waterLevel={waterLevel} />

      <IntelligentAlertsPanel
        alerts={alerts}
        isLoading={isLoadingAlerts}
        isRefreshing={isRefreshingAlerts}
        error={alertsError}
        lastUpdatedAt={alertsLastUpdatedAt}
        acknowledgingId={acknowledgingId}
        onRefresh={refreshAlerts}
        onAcknowledge={acknowledgeAlert}
      />

      {/* Estatísticas Rápidas */}
      <QuickStats waterLevel={waterLevel} isPumpOn={isPumpOn} />

      {/* Visualização do Tanque - Destaque */}
      <div className="bg-white rounded-2xl shadow-lg p-6 mb-6">
        <h2 className="text-lg text-slate-700 mb-4 text-center">Nível do Reservatório</h2>
        <div className="flex justify-center">
          <WaterTankVisualization waterLevel={waterLevel} />
        </div>
      </div>

      {/* Grid de Informações */}
      <div className="grid grid-cols-1 gap-4 mb-6">
        {/* Status do Sensor */}
        <SensorStatus
          sensorName={lastSensor.name}
          action={lastSensor.action}
          time={lastSensor.time}
        />

        {/* Grid 2 colunas para Controle e Modo */}
        <div className="grid grid-cols-2 gap-4">
          <PumpControl
            isOn={isPumpOn}
            onToggle={togglePump}
            isPending={Boolean(pendingPumpCommand)}
            statusMessage={pumpStatusMessage}
          />
          <PumpModeDisplay mode={pumpMode} />
        </div>

        {/* Estimativa de Energia */}
        <EnergyEstimate isPumpOn={isPumpOn} pumpPowerWatts={750} />
      </div>

      {/* Navegação Inferior - Botões para outras telas */}
      <div className="grid grid-cols-2 gap-4 mt-8">
        <Button
          variant="outline"
          className="home-action-button home-action-history"
          onClick={() => history.push("/history")}
        >
          <BarChart3 className="w-6 h-6" />
          <span className="text-xs">Histórico</span>
        </Button>

        <Button
          variant="outline"
          className="home-action-button home-action-chat"
          onClick={() => history.push("/chat")}
        >
          <MessageSquare className="w-6 h-6" />
          <span className="text-xs">Assistente IA</span>
        </Button>
      </div>

      {/* Info Footer */}
      <div className="mt-6 text-center text-xs text-slate-400">
        <p>Última atualização: {new Date().toLocaleString("pt-BR")}</p>
      </div>
    </>
  );
}
