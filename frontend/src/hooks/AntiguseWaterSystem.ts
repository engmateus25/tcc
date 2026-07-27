import { useState, useEffect, useCallback } from "react";

// Hook customizado para gerenciar o estado do sistema de água
// Futuramente vai integrar com Firebase e MQTT
export function useWaterSystem() {
  const [waterLevel, setWaterLevel] = useState(75);
  const [isPumpOn, setIsPumpOn] = useState(false);
  const [pumpMode, setPumpMode] = useState<"automático" | "manual mqtt" | "manual chave">("automático");
  const [lastSensor, setLastSensor] = useState({
    name: "Sensor Nível Alto",
    action: "subiu" as "subiu" | "desceu",
    time: new Date().toLocaleTimeString('pt-BR')
  });
  const [isConnected] = useState({
    firebase: true,
    mqtt: true
  });

  // Simula recebimento de dados do Firebase
  useEffect(() => {
    // TODO: Substituir por listener do Firebase
    // const unsubscribe = onSnapshot(doc(db, "waterSystem", "current"), (doc) => {
    //   const data = doc.data() as FirebaseWaterData;
    //   setWaterLevel(data.waterLevel);
    //   setIsPumpOn(data.pumpState.isOn);
    //   setPumpMode(data.pumpState.mode);
    //   setLastSensor(data.lastSensor);
    // });
    // return () => unsubscribe();

    console.log("Firebase listener would be set up here");
  }, []);

  // Simula conexão MQTT
  useEffect(() => {
    // TODO: Conectar ao broker MQTT
    // const client = mqtt.connect(MQTT_BROKER_URL);
    // client.on('connect', () => {
    //   setIsConnected(prev => ({ ...prev, mqtt: true }));
    //   client.subscribe('water-system/pump');
    //   client.subscribe('water-system/sensors');
    // });
    // client.on('message', (topic, message) => {
    //   handleMQTTMessage(topic, message);
    // });
    // return () => client.end();

    console.log("MQTT connection would be established here");
  }, []);

  // Simula mudanças automáticas no nível de água
  useEffect(() => {
    const interval = setInterval(() => {
      if (isPumpOn && waterLevel < 100) {
        setWaterLevel(prev => Math.min(prev + 5, 100));
        
        // Simula sensor de nível alto sendo ativado
        if (waterLevel >= 95 && waterLevel < 100) {
          setLastSensor({
            name: "Sensor Nível Alto",
            action: "subiu",
            time: new Date().toLocaleTimeString('pt-BR')
          });
          
          // Em modo automático, desliga a bomba
          if (pumpMode === "automático") {
            setIsPumpOn(false);
          }
        }
      } else if (!isPumpOn && waterLevel > 0) {
        setWaterLevel(prev => Math.max(prev - 2, 0));
        
        // Simula sensor de nível baixo sendo ativado
        if (waterLevel <= 25 && waterLevel > 20) {
          setLastSensor({
            name: "Sensor Nível Baixo",
            action: "desceu",
            time: new Date().toLocaleTimeString('pt-BR')
          });
          
          // Em modo automático, liga a bomba
          if (pumpMode === "automático") {
            setIsPumpOn(true);
          }
        }
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [isPumpOn, waterLevel, pumpMode]);

  // Função para alternar a bomba
  const togglePump = useCallback(() => {
    const newState = !isPumpOn;
    setIsPumpOn(newState);
    setPumpMode("manual mqtt");
    
    const now = new Date();
    const timeString = now.toLocaleTimeString('pt-BR');
    
    setLastSensor({
      name: "Bomba",
      action: newState ? "subiu" : "desceu",
      time: timeString
    });

    // TODO: Enviar comando via MQTT
    // const command: MQTTCommand = {
    //   type: "pump_toggle",
    //   value: newState,
    //   timestamp: Date.now()
    // };
    // mqttClient.publish('water-system/commands', JSON.stringify(command));

    // TODO: Atualizar no Firebase
    // updateDoc(doc(db, "waterSystem", "current"), {
    //   "pumpState.isOn": newState,
    //   "pumpState.mode": "manual mqtt",
    //   "lastSensor": {
    //     name: "Bomba",
    //     action: newState ? "subiu" : "desceu",
    //     time: timeString
    //   }
    // });

    console.log(`Pump toggled: ${newState ? "ON" : "OFF"}`);
  }, [isPumpOn]);

  // Função para mudar o modo da bomba
  const changePumpMode = useCallback((mode: "automático" | "manual mqtt" | "manual chave") => {
    setPumpMode(mode);
    
    // TODO: Atualizar no Firebase
    console.log(`Pump mode changed to: ${mode}`);
  }, []);

  return {
    waterLevel,
    isPumpOn,
    pumpMode,
    lastSensor,
    isConnected,
    togglePump,
    changePumpMode,
    setWaterLevel, // Para testes
  };
}
