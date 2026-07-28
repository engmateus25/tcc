// src/hooks/useWaterSystem.ts
import { useEffect, useMemo, useState, useCallback } from "react";
import type { LastSensor, PumpMode } from "../types/water-system";
import client, {
  enviarComando,
  parsePumpStateMessage,
  PumpStateMessage,
} from "../services/mqttService";
import { listenUltimoEstado, UltimoEvento } from "../services/firestoreService";

type State = {
  waterLevel: number;
  isPumpOn: boolean;
  pumpMode: PumpMode;
  lastSensor: LastSensor | null;
  isConnected: { firebase: boolean; mqtt: boolean };
  pendingCommand: {
    commandId: string;
    desiredOn: boolean;
  } | null;
  lastPumpStatus: string | null;
};

function isLastSensorAction(value: string): value is LastSensor["action"] {
  return value === "subiu" || value === "desceu";
}

function isPumpMode(value: unknown): value is PumpMode {
  return (
    value === "automático" ||
    value === "manual mqtt" ||
    value === "manual chave"
  );
}

const initialState: State = {
  waterLevel: 42,
  isPumpOn: false,
  pumpMode: "automático",
  lastSensor: { name: "alto", action: "subiu", time: "04:11:37" },
  isConnected: { firebase: false, mqtt: false },
  pendingCommand: null,
  lastPumpStatus: null,
};

export function useWaterSystem() {
  const [state, setState] = useState<State>(initialState);

  // ---- FIRESTORE: escuta o último evento da coleção `sensores` ----
  useEffect(() => {
    const unsub = listenUltimoEstado(
      (ev: UltimoEvento | null) => {
        if (!ev) {
          setState((s) => ({ ...s, isConnected: { ...s.isConnected, firebase: false } }));
          return;
        }
        const ls: LastSensor = {
          name: ev.sensor,
          action: isLastSensorAction(ev.estado) ? ev.estado : "desceu",
          time: ev.timestamp.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
        };
        setState((s) => ({
          ...s,
          lastSensor: ls,
          waterLevel: estimateWaterLevelFromSensorEvent(ls, s.waterLevel),
          isConnected: { ...s.isConnected, firebase: true },
        }));
      },
      () => setState((s) => ({ ...s, isConnected: { ...s.isConnected, firebase: false } }))
    );

    return () => unsub();
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

  return useMemo(() => ({
    waterLevel: state.waterLevel,
    isPumpOn: state.isPumpOn,
    pumpMode: state.pumpMode,
    lastSensor: state.lastSensor!,
    pendingPumpCommand: state.pendingCommand,
    pumpStatusMessage: state.lastPumpStatus,
    isConnected: state.isConnected,    // usado pela status bar (Firebase/MQTT)
    togglePump,
  }), [state, togglePump]);
}

function estimateWaterLevelFromSensorEvent(
  event: LastSensor,
  fallback: number,
): number {
  if (event.name === "baixo" && event.action === "desceu") return 15;
  if (event.name === "baixo" && event.action === "subiu") return 55;
  if (event.name === "alto" && event.action === "subiu") return 96;
  if (event.name === "alto" && event.action === "desceu") return 62;
  return fallback;
}

function applyPumpStateMessage(state: State, message: PumpStateMessage): State {
  const commandMatches = !message.commandId || state.pendingCommand?.commandId === message.commandId;
  const pendingCommand = commandMatches ? null : state.pendingCommand;
  const nextMode = normalizePumpMode(message.mode || message.source) ?? state.pumpMode;

  if (!message.applied) {
    return {
      ...state,
      pumpMode: nextMode,
      pendingCommand,
      lastPumpStatus: message.overriddenBy
        ? `Comando sobreposto por ${message.overriddenBy}`
        : "Comando não aplicado",
    };
  }

  return {
    ...state,
    isPumpOn: message.confirmed ? message.pumpOn : state.isPumpOn,
    pumpMode: nextMode,
    pendingCommand,
    lastPumpStatus: message.confirmed
      ? "Estado confirmado pela bomba"
      : "Comando aplicado sem confirmação física",
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
