import mqtt from "mqtt";

export type PumpCommandDirection = "ligar" | "desligar";

export interface PumpCommandPublishResult {
  commandId: string;
  desiredOn: boolean;
  published: boolean;
}

export interface PumpStateMessage {
  pumpOn: boolean;
  mode?: string;
  confirmed: boolean;
  applied: boolean;
  source?: string;
  priority?: string;
  commandId?: string;
  overriddenBy?: string | null;
  reason?: string | null;
  timestamp?: string;
}

const options = {
  connectTimeout: 4000,
  clientId: 'ionic_client_' + Math.random().toString(16).substr(2, 8),
  username: '', 
  password: '', 
};
const connectUrl = 'wss://broker.hivemq.com:8884/mqtt';
const client = mqtt.connect(connectUrl, options);
const publishLegacyControl = import.meta.env.VITE_MQTT_PUBLISH_LEGACY_CONTROL === "1";


client.on("connect", () => {
  console.log("Conectado ao MQTT");

  client.subscribe("bomba/estado", (err) => {
    if (!err) {
      console.log("Assinou bomba/estado");
    }
  });
});


client.on("message", (topic, message) => {
  console.log(`Mensagem recebida em ${topic}: ${message.toString()}`);
});


export const enviarComando = (
  nome: string,
  comando: PumpCommandDirection,
): PumpCommandPublishResult => {
  const desiredOn = comando === "ligar";
  const commandId = `web-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
  if (client.connected) {
    const legacyPayload = `${nome} ${comando}`;
    const v2Payload = JSON.stringify({
      schema_version: 1,
      command_id: commandId,
      command: comando,
      desired_on: desiredOn,
      source: "frontend",
      timestamp: new Date().toISOString(),
    });
    client.publish("bomba/controle/v2", v2Payload);
    if (publishLegacyControl) {
      client.publish("bomba/controle", legacyPayload);
    }
    console.log(`Publicado comando de bomba: ${commandId}`);
    return { commandId, desiredOn, published: true };
  }
  console.warn("MQTT não conectado!");
  return { commandId, desiredOn, published: false };
};

export function parsePumpStateMessage(text: string): PumpStateMessage | null {
  const trimmed = text.trim();
  if (!trimmed) return null;

  if (trimmed.startsWith("{")) {
    const obj = JSON.parse(trimmed) as Record<string, unknown>;
    const pumpOn = readOptionalBoolean(obj.pump_on) ?? readOptionalBoolean(obj.isOn);
    if (pumpOn === null) return null;
    return {
      pumpOn,
      mode: readOptionalString(obj.mode) ?? undefined,
      confirmed: readOptionalBoolean(obj.confirmed) ?? true,
      applied: readOptionalBoolean(obj.applied) ?? true,
      source: readOptionalString(obj.source) ?? undefined,
      priority: readOptionalString(obj.priority) ?? undefined,
      commandId: readOptionalString(obj.command_id) ?? readOptionalString(obj.commandId) ?? undefined,
      overriddenBy: readOptionalString(obj.overridden_by) ?? readOptionalString(obj.overriddenBy),
      reason: readOptionalString(obj.reason),
      timestamp: readOptionalString(obj.timestamp) ?? undefined,
    };
  }

  const lower = trimmed.toLowerCase();
  if (lower.includes("ligad")) {
    return { pumpOn: true, confirmed: true, applied: true };
  }
  if (lower.includes("deslig")) {
    return { pumpOn: false, confirmed: true, applied: true };
  }
  return null;
}

function readOptionalBoolean(value: unknown): boolean | null {
  if (typeof value === "boolean") return value;
  if (typeof value === "string") {
    const text = value.trim().toLowerCase();
    if (["true", "1", "sim", "yes", "on", "ligar", "ligada"].includes(text)) return true;
    if (["false", "0", "nao", "não", "no", "off", "desligar", "desligada"].includes(text)) return false;
  }
  return null;
}

function readOptionalString(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const text = value.trim();
  return text || null;
}

export default client;
