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
    reservoirStatus,
    waitingForHighConfirmation,
    isPumpOn,
    pumpMode,
    lastSensor,
    firebaseStatus,
    firebaseError,
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
        <div className="mt-4 text-center">
          <p className="text-sm text-slate-700">{reservoirStatus}</p>
          {waitingForHighConfirmation && (
            <p className="mt-1 text-xs text-amber-600">
              A estimativa visual está limitada até confirmação do sensor alto.
            </p>
          )}
        </div>
      </div>

      {/* Grid de Informações */}
      <div className="grid grid-cols-1 gap-4 mb-6">
        {/* Status do Sensor */}
        <SensorStatus
          sensor={lastSensor}
          connectionLabel={firebaseStatusLabel(firebaseStatus, firebaseError)}
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

function firebaseStatusLabel(status: string, error?: string | null) {
  if (status === "connecting") return "Conectando ao Firestore...";
  if (status === "connected") return "Firestore conectado, sem eventos no período consultado.";
  if (status === "offline") return "Firestore usando cache/offline.";
  if (status === "error") return error || "Erro no listener do Firestore.";
  return "Aguardando leitura do Firestore.";
}
