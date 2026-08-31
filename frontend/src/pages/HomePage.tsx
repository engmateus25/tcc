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
      <div
        data-testid="home-responsive-grid"
        className="home-responsive-grid"
      >
        <div data-testid="home-left-column" className="min-w-0">
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

          <QuickStats waterLevel={waterLevel} isPumpOn={isPumpOn} />

          <div className="mb-6 rounded-2xl border border-slate-100 bg-white p-5 shadow-lg sm:p-6">
            <h2 className="mb-4 text-center text-lg text-slate-700">Nível do Reservatório</h2>
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
        </div>

        <div data-testid="home-right-column" className="flex min-w-0 flex-col gap-4">
          <div className="order-1 grid grid-cols-1 gap-4 lg:order-2">
            <SensorStatus
              sensor={lastSensor}
              connectionLabel={firebaseStatusLabel(firebaseStatus, firebaseError)}
            />

            <div className="grid grid-cols-2 gap-4">
              <PumpControl
                isOn={isPumpOn}
                onToggle={togglePump}
                isPending={Boolean(pendingPumpCommand)}
                statusMessage={pumpStatusMessage}
              />
              <PumpModeDisplay mode={pumpMode} />
            </div>

            <EnergyEstimate isPumpOn={isPumpOn} pumpPowerWatts={750} />
          </div>

          <div className="order-2 grid grid-cols-2 gap-4 lg:order-1">
            <Button
              variant="outline"
              className="home-action-button home-action-history"
              onClick={() => history.push("/history")}
            >
              <BarChart3 className="h-6 w-6" />
              <span className="text-xs">Histórico</span>
            </Button>

            <Button
              variant="outline"
              className="home-action-button home-action-chat"
              onClick={() => history.push("/chat")}
            >
              <MessageSquare className="h-6 w-6" />
              <span className="text-xs">Assistente IA</span>
            </Button>
          </div>

          <div className="order-3 mt-2 text-center text-xs text-slate-400 lg:text-right">
            <p>Última atualização: {new Date().toLocaleString("pt-BR")}</p>
          </div>
        </div>
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
