// src/hooks/useWaterSystem.ts
import {
  createContext,
  createElement,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { PropsWithChildren } from "react";
import type {
  FirebaseConnectionStatus,
  LastSensor,
  PumpMode,
} from "../types/water-system";
import client, {
  enviarComando,
  parsePumpStateMessage,
  PumpStateMessage,
} from "../services/mqttService";
import { listenSensorTelemetry } from "../services/firestoreService";
import {
  deriveOperationalState,
  estimateVisualWaterLevel,
  formatSensorDateTime,
  NormalizedSensorEvent,
  WATER_LEVEL_ESTIMATION_CONFIG,
} from "../services/waterTelemetry";

type State = {
  waterLevel: number;
  reservoirStatus: string;
  waitingForHighConfirmation: boolean;
  isPumpOn: boolean;
  pumpMode: PumpMode;
  lastSensor: LastSensor | null;
  sensorEvents: NormalizedSensorEvent[];
  firebaseStatus: FirebaseConnectionStatus;
  firebaseError: string | null;
  isConnected: { firebase: boolean; mqtt: boolean };
  pendingCommand: {
    commandId: string;
    desiredOn: boolean;
  } | null;
  lastPumpStatus: string | null;
};

export interface WaterSystemValue {
  waterLevel: number;
  reservoirStatus: string;
  waitingForHighConfirmation: boolean;
  isPumpOn: boolean;
  pumpMode: PumpMode;
  lastSensor: LastSensor | null;
  firebaseStatus: FirebaseConnectionStatus;
  firebaseError: string | null;
  pendingPumpCommand: State["pendingCommand"];
  pumpStatusMessage: string | null;
  isConnected: State["isConnected"];
  togglePump: () => void;
}

const WaterSystemContext = createContext<WaterSystemValue | null>(null);

function isPumpMode(value: unknown): value is PumpMode {
  return (
    value === "automático" ||
    value === "manual mqtt" ||
    value === "manual chave"
  );
}

const initialState: State = {
  waterLevel: WATER_LEVEL_ESTIMATION_CONFIG.lowSensorRaisedLevelPercent,
  reservoirStatus: "Aguardando leitura",
  waitingForHighConfirmation: false,
  isPumpOn: false,
  pumpMode: "automático",
  lastSensor: null,
  sensorEvents: [],
  firebaseStatus: "connecting",
  firebaseError: null,
  isConnected: { firebase: false, mqtt: false },
  pendingCommand: null,
  lastPumpStatus: null,
};

export function useWaterSystemState(): WaterSystemValue {
  const [state, setState] = useState<State>(initialState);

  // ---- FIRESTORE: escuta o último evento da coleção `sensores` ----
  useEffect(() => {
    const unsub = listenSensorTelemetry((snapshot) => {
      setState((s) => {
        const visual = estimateVisualWaterLevel(
          snapshot.events,
          new Date(),
          { pumpOn: s.isPumpOn },
        );
        const operationalState = deriveOperationalState(
          snapshot.events,
          { pumpOn: s.isPumpOn },
        );
        const latest = snapshot.latestEvent;
        const lastSensor: LastSensor | null = latest
          ? {
              name: latest.sensor,
              action: latest.estado,
              date: latest.timestamp.toLocaleDateString("pt-BR"),
              time: latest.timestamp.toLocaleTimeString("pt-BR", {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              }),
              dateTime: formatSensorDateTime(latest.timestamp),
              operationalState,
            }
          : null;

        return {
          ...s,
          sensorEvents: snapshot.events,
          lastSensor,
          waterLevel: visual.level,
          reservoirStatus: visual.waitingForHighConfirmation
            ? "Aguardando confirmação do sensor alto"
            : visual.label,
          waitingForHighConfirmation: visual.waitingForHighConfirmation,
          firebaseStatus: snapshot.status,
          firebaseError: snapshot.error || null,
          isConnected: {
            ...s.isConnected,
            firebase: snapshot.status === "connected",
          },
        };
      });
    });

    return () => unsub();
  }, []);

  useEffect(() => {
    const interval = window.setInterval(() => {
      setState((s) => {
        const visual = estimateVisualWaterLevel(
          s.sensorEvents,
          new Date(),
          { pumpOn: s.isPumpOn },
        );
        return {
          ...s,
          waterLevel: visual.level,
          reservoirStatus: visual.waitingForHighConfirmation
            ? "Aguardando confirmação do sensor alto"
            : visual.label,
          waitingForHighConfirmation: visual.waitingForHighConfirmation,
        };
      });
    }, 5000);

    return () => window.clearInterval(interval);
  }, []);

  // ---- MQTT: usa SEU client e tópicos já existentes ----
  useEffect(() => {
    // se já estiver conectado (porque o serviço inicia na importação), marcamos true
    if (client.connected) {
      setState((s) => ({ ...s, isConnected: { ...s.isConnected, mqtt: true } }));
    }

    const onConnect = () => {
      setState((s) => ({ ...s, isConnected: { ...s.isConnected, mqtt: true } }));
      // o service já faz subscribe em "bomba/estado", então aqui é opcional repetir.
    };
    const onCloseOrError = () => {
      setState((s) => ({ ...s, isConnected: { ...s.isConnected, mqtt: false } }));
    };
    const onMessage = (_topic: string, payload: Buffer) => {
      try {
        const text = payload.toString().trim();

        const pumpState = parsePumpStateMessage(text);
        if (!pumpState) return;

        setState((s) => applyPumpStateMessage(s, pumpState));
      } catch (e) {
        console.warn("Falha ao parsear mensagem MQTT:", e);
      }
    };

    client.on("connect", onConnect);
    client.on("reconnect", onCloseOrError);
    client.on("close", onCloseOrError);
    client.on("error", onCloseOrError);
    client.on("message", onMessage);

    return () => {
      // remove apenas os listeners que adicionamos aqui
      client.removeListener("connect", onConnect);
      client.removeListener("reconnect", onCloseOrError);
      client.removeListener("close", onCloseOrError);
      client.removeListener("error", onCloseOrError);
      client.removeListener("message", onMessage);
    };
  }, []);

  // ---- Ação do UI: alternar bomba (publica em `bomba/controle`) ----
  const togglePump = useCallback(() => {
    const target = !state.isPumpOn;
    const result = enviarComando("bomba", target ? "ligar" : "desligar");

    setState((s) => ({
      ...s,
      pendingCommand: result.published
        ? { commandId: result.commandId, desiredOn: result.desiredOn }
        : null,
      lastPumpStatus: result.published
        ? "Aguardando confirmação da bomba"
        : "MQTT desconectado; comando não publicado",
    }));
  }, [state.isPumpOn]);

  return useMemo<WaterSystemValue>(() => ({
    waterLevel: state.waterLevel,
    reservoirStatus: state.reservoirStatus,
    waitingForHighConfirmation: state.waitingForHighConfirmation,
    isPumpOn: state.isPumpOn,
    pumpMode: state.pumpMode,
    lastSensor: state.lastSensor,
    firebaseStatus: state.firebaseStatus,
    firebaseError: state.firebaseError,
    pendingPumpCommand: state.pendingCommand,
    pumpStatusMessage: state.lastPumpStatus,
    isConnected: state.isConnected,    // usado pela status bar (Firebase/MQTT)
    togglePump,
  }), [state, togglePump]);
}

export function WaterSystemProvider({
  children,
  value,
}: PropsWithChildren<{ value: WaterSystemValue }>) {
  return createElement(WaterSystemContext.Provider, { value }, children);
}

export function useWaterSystem(): WaterSystemValue {
  const value = useContext(WaterSystemContext);
  if (!value) {
    throw new Error("useWaterSystem deve ser usado dentro de WaterSystemProvider");
  }
  return value;
}

function applyPumpStateMessage(state: State, message: PumpStateMessage): State {
  const commandMatches = !message.commandId || state.pendingCommand?.commandId === message.commandId;
  const pendingCommand = commandMatches ? null : state.pendingCommand;
  const nextMode = normalizePumpMode(message.mode || message.source) ?? state.pumpMode;

  if (!message.applied) {
    return withVisualState({
      ...state,
      pumpMode: nextMode,
      pendingCommand,
      lastPumpStatus: message.overriddenBy
        ? `Comando sobreposto por ${message.overriddenBy}`
        : "Comando não aplicado",
    });
  }

  return withVisualState({
    ...state,
    isPumpOn: message.confirmed ? message.pumpOn : state.isPumpOn,
    pumpMode: nextMode,
    pendingCommand,
    lastPumpStatus: message.confirmed
      ? "Estado confirmado pela bomba"
      : "Comando aplicado sem confirmação física",
  });
}

function withVisualState(state: State): State {
  const visual = estimateVisualWaterLevel(
    state.sensorEvents,
    new Date(),
    { pumpOn: state.isPumpOn },
  );
  const operationalState = deriveOperationalState(
    state.sensorEvents,
    { pumpOn: state.isPumpOn },
  );
  return {
    ...state,
    waterLevel: visual.level,
    reservoirStatus: visual.waitingForHighConfirmation
      ? "Aguardando confirmação do sensor alto"
      : visual.label,
    waitingForHighConfirmation: visual.waitingForHighConfirmation,
    lastSensor: state.lastSensor
      ? { ...state.lastSensor, operationalState }
      : state.lastSensor,
  };
}

function normalizePumpMode(value: unknown): PumpMode | null {
  if (isPumpMode(value)) return value;
  if (typeof value !== "string") return null;
  const text = value.trim().toLowerCase();
  if (text === "remoto" || text === "mqtt" || text === "frontend") return "manual mqtt";
  if (text === "físico" || text === "fisico" || text === "manual chave") return "manual chave";
  if (text === "auto" || text === "automático" || text === "automatico") return "automático";
  return null;
}
