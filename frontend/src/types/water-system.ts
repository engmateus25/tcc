// Tipos para o sistema de monitoramento de água

export type PumpMode = "automático" | "manual mqtt" | "manual chave";
export type FirebaseConnectionStatus =
  | "connecting"
  | "connected"
  | "offline"
  | "error";

export type LastSensor = {
  name: string;
  action: "subiu" | "desceu";
  date: string;
  time: string;
  dateTime: string;
  operationalState: string;
};

// --- abaixo, faça pequenos ajustes para reutilizar os tipos recém-criados ---

export interface PumpState {
  isOn: boolean;
  mode: PumpMode;      // <--- usar PumpMode
  powerWatts: number;
}

export interface WaterLevelData {
  level: number; // 0-100
  timestamp: Date | string;
}

export interface EnergyData {
  totalMinutes: number;
  energyKwh: number;
  costEstimate: number;
}

export interface SystemStatus {
  firebaseConnected: boolean;
  mqttConnected: boolean;
  lastUpdate: Date | string;
}

// Estrutura de dados que virá do Firebase
export interface FirebaseWaterData {
  waterLevel: number;
  pumpState: {
    isOn: boolean;
    mode: PumpMode;    // <--- usar PumpMode
  };
  lastSensor: LastSensor; // <--- usar LastSensor (mesma estrutura que você já tinha)
  energyData?: {
    totalMinutes: number;
    sessionStart: number | null;
  };
}

// Estrutura de comandos MQTT
export interface MQTTCommand {
  type: "pump_toggle" | "pump_on" | "pump_off" | "mode_change";
  value?: boolean | string;
  timestamp: number;
}
