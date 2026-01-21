// Tipos para o sistema de monitoramento de água

export interface SensorData {
  name: string;
  action: "subiu" | "desceu";
  timestamp: Date | string;
}

export interface PumpState {
  isOn: boolean;
  mode: "automático" | "remoto" | "físico";
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
    mode: "automático" | "manual mqtt" | "manual chave";
  };
  lastSensor: {
    name: string;
    action: "subiu" | "desceu";
    time: string;
  };
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
