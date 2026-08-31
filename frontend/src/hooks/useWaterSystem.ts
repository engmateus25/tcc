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
import {
  listenPumpCommandTelemetry,
  listenSensorTelemetry,
} from "../services/firestoreService";
import {
  deriveOperationalState,
  EffectivePumpState,
  estimateVisualWaterLevel,
  formatSensorDateTime,
  getAutomaticPumpStateFromSensors,
  getEffectivePumpStateFromCommand,
  NormalizedPumpCommandEvent,
  NormalizedSensorEvent,
  PumpStateSource,
  WATER_LEVEL_ESTIMATION_CONFIG,
} from "../services/waterTelemetry";

type State = {
  waterLevel: number;
  reservoirStatus: string;
  waitingForHighConfirmation: boolean;
  isPumpOn: boolean;
  isPumpStateConfirmed: boolean;
  pumpStateSource: PumpStateSource;
  pumpStateUpdatedAt: Date | null;
  pumpMode: PumpMode;
  lastSensor: LastSensor | null;
  sensorEvents: NormalizedSensorEvent[];
  pumpCommands: NormalizedPumpCommandEvent[];
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
  isPumpStateConfirmed: boolean;
  pumpStateSource: PumpStateSource;
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
  isPumpStateConfirmed: false,
  pumpStateSource: "initial",
  pumpStateUpdatedAt: null,
  pumpMode: "automático",
  lastSensor: null,
  sensorEvents: [],
  pumpCommands: [],
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
      setState((s) => withSensorTelemetry(s, snapshot));
    });

    return () => unsub();
  }, []);

  useEffect(() => {
    const unsub = listenPumpCommandTelemetry((snapshot) => {
      setState((s) => {
        let next: State = {
          ...s,
          pumpCommands: snapshot.commands,
        };
        const effective = getEffectivePumpStateFromCommand(snapshot.effectiveCommand);
        if (effective) {
          next = applyEffectivePumpState(next, effective, pumpCommandStatus(snapshot.effectiveCommand));
        } else if (snapshot.latestCommand && snapshot.latestCommand.applied === false) {
          next = {
            ...next,
            pendingCommand: clearMatchingPendingCommand(next, snapshot.latestCommand.commandId),
            lastPumpStatus: pumpCommandStatus(snapshot.latestCommand),
          };
        }
        return withVisualState(next);
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
          { pumpOn: s.isPumpOn, confirmed: s.isPumpStateConfirmed },
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
    isPumpStateConfirmed: state.isPumpStateConfirmed,
    pumpStateSource: state.pumpStateSource,
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
  const timestamp = parseOptionalDate(message.timestamp) || new Date();

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

  return applyEffectivePumpState(
    {
      ...state,
      pumpMode: nextMode,
      pendingCommand,
    },
    {
      pumpOn: message.pumpOn,
      applied: true,
      confirmed: message.confirmed,
      source: "mqtt_state",
      mode: message.mode || message.source,
      commandId: message.commandId,
      timestamp,
      overriddenBy: message.overriddenBy,
      reason: message.reason,
    },
    message.confirmed
      ? "Estado confirmado pela bomba"
      : "Comando aplicado sem confirmação física",
  );
}

function withVisualState(state: State): State {
  const visual = estimateVisualWaterLevel(
    state.sensorEvents,
    new Date(),
    { pumpOn: state.isPumpOn, confirmed: state.isPumpStateConfirmed },
  );
  const operationalState = deriveOperationalState(
    state.sensorEvents,
    { pumpOn: state.isPumpOn, confirmed: state.isPumpStateConfirmed },
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

function withSensorTelemetry(
  state: State,
  snapshot: {
    status: FirebaseConnectionStatus;
    events: NormalizedSensorEvent[];
    latestEvent: NormalizedSensorEvent | null;
    error?: string | null;
  },
): State {
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
        operationalState: "Aguardando leitura",
      }
    : null;

  let next: State = {
    ...state,
    sensorEvents: snapshot.events,
    lastSensor,
    firebaseStatus: snapshot.status,
    firebaseError: snapshot.error || null,
    isConnected: {
      ...state.isConnected,
      firebase: snapshot.status === "connected",
    },
  };

  const automaticPumpState = getAutomaticPumpStateFromSensors(snapshot.events);
  if (automaticPumpState && shouldUseAutomaticFallback(next, automaticPumpState)) {
    next = applyEffectivePumpState(
      next,
      automaticPumpState,
      automaticPumpState.reason || "Aguardando confirmação do comando automático",
    );
  }

  return withVisualState(next);
}

function applyEffectivePumpState(
  state: State,
  pumpState: EffectivePumpState,
  statusMessage: string | null = null,
): State {
  if (!shouldAcceptPumpState(state, pumpState)) {
    return withVisualState(state);
  }

  return withVisualState({
    ...state,
    isPumpOn: pumpState.pumpOn,
    isPumpStateConfirmed: pumpState.confirmed,
    pumpStateSource: pumpState.source,
    pumpStateUpdatedAt: pumpState.timestamp || new Date(),
    pumpMode: normalizePumpMode(pumpState.mode) ?? state.pumpMode,
    pendingCommand: pumpState.commandId
      ? clearMatchingPendingCommand(state, pumpState.commandId)
      : state.pendingCommand,
    lastPumpStatus: statusMessage || pumpState.reason || state.lastPumpStatus,
  });
}

function shouldAcceptPumpState(state: State, pumpState: EffectivePumpState): boolean {
  if (!pumpState.timestamp || !state.pumpStateUpdatedAt) {
    return true;
  }
  return pumpState.timestamp.getTime() >= state.pumpStateUpdatedAt.getTime() - 1000;
}

function shouldUseAutomaticFallback(state: State, pumpState: EffectivePumpState): boolean {
  if (state.pumpStateSource === "initial" || state.pumpStateSource === "sensor_automatic") {
    return shouldAcceptPumpState(state, pumpState);
  }
  if (!pumpState.timestamp || !state.pumpStateUpdatedAt) {
    return false;
  }
  return pumpState.timestamp.getTime() > state.pumpStateUpdatedAt.getTime();
}

function pumpCommandStatus(command: NormalizedPumpCommandEvent | null): string {
  if (!command) {
    return "Aguardando comando de bomba";
  }

  const requested = command.requestedState === false ? "desligar" : "ligar";
  const mode = command.mode || command.priority || command.source || "comando";
  if (command.applied === false) {
    return command.overriddenBy
      ? `Comando para ${requested} sobreposto por ${command.overriddenBy}`
      : `Comando para ${requested} não aplicado`;
  }

  const stateText = command.appliedState ? "ligada" : "desligada";
  const confirmation = command.confirmed === false
    ? "sem confirmação física"
    : "confirmada";
  return `Bomba ${stateText} por ${mode}; ${confirmation}`;
}

function clearMatchingPendingCommand(
  state: State,
  commandId: string | null | undefined,
): State["pendingCommand"] {
  if (!commandId || state.pendingCommand?.commandId !== commandId) {
    return state.pendingCommand;
  }
  return null;
}

function parseOptionalDate(value: string | undefined): Date | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
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
