// src/hooks/useWaterSystem.ts
import { useEffect, useMemo, useState, useCallback } from "react";
import type { LastSensor, PumpMode } from "../types/water-system"; // ajuste se seu arquivo tiver outro nome
import client, { enviarComando } from "../services/mqttService";
import { listenUltimoEstado, UltimoEvento } from "../services/firestoreService";

type PumpMode = "automático" | "manual mqtt" | "manual chave";

type State = {
  waterLevel: number;
  isPumpOn: boolean;
  pumpMode: PumpMode;
  lastSensor: LastSensor | null;
  isConnected: { firebase: boolean; mqtt: boolean };
};

// Mock inicial (até chegar dados reais)
const initialState: State = {
  waterLevel: 42,
  isPumpOn: false,
  pumpMode: "automático",
  lastSensor: { name: "alto", action: "subiu", time: "04:11:37" },
  isConnected: { firebase: false, mqtt: false },
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
          action: ev.estado as any, // "subiu" | "desceu"
          time: ev.timestamp.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
        };
        setState((s) => ({
          ...s,
          lastSensor: ls,
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
    if ((client as any).connected) {
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

        // Espera algo como "ligada"/"desligada" OU JSON {"isOn":true,"mode":"automático"}
        let isOn: boolean | null = null;
        let mode: PumpMode | null = null;

        if (text.startsWith("{")) {
          const obj = JSON.parse(text);
          if (typeof obj.isOn === "boolean") isOn = obj.isOn;
          if (typeof obj.mode === "string") mode = obj.mode as PumpMode;
        } else {
          const lower = text.toLowerCase();
          if (lower.includes("ligad")) isOn = true;
          if (lower.includes("deslig")) isOn = false;
        }

        if (isOn !== null) {
          setState((s) => ({
            ...s,
            isPumpOn: isOn!,
            pumpMode: mode ?? s.pumpMode,
          }));
        }
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

    // 1) publicar comando usando SEU serviço (nome é livre; pode usar "bomba")
    enviarComando("bomba", target ? "ligar" : "desligar");

    // 2) UI otimista
    setState((s) => ({ ...s, isPumpOn: target }));
  }, [state.isPumpOn]);

  return useMemo(() => ({
    waterLevel: state.waterLevel,      // por enquanto mock; quando tiver tópico de nível, a gente liga aqui
    isPumpOn: state.isPumpOn,
    pumpMode: state.pumpMode,
    lastSensor: state.lastSensor!,
    isConnected: state.isConnected,    // usado pela status bar (Firebase/MQTT)
    togglePump,
  }), [state, togglePump]);
}
