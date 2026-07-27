import { Alert, AlertDescription, AlertTitle } from "./ui/alert";
import { AlertTriangle, CheckCircle } from "lucide-react";

interface WaterLevelAlertProps {
  waterLevel: number;
}

export function WaterLevelAlert({ waterLevel }: WaterLevelAlertProps) {
  if (waterLevel >= 30 && waterLevel < 90) {
    return null; // Não mostra nada se estiver em nível normal
  }

  if (waterLevel < 30) {
    return (
      <Alert className="border-red-500 bg-red-50 mb-4">
        <AlertTriangle className="h-4 w-4 text-red-600" />
        <AlertTitle className="text-red-800">Nível Crítico!</AlertTitle>
        <AlertDescription className="text-red-700">
          O reservatório está com apenas {waterLevel}% de água. 
          {waterLevel < 15 && " Acionamento urgente da bomba recomendado!"}
        </AlertDescription>
      </Alert>
    );
  }

  if (waterLevel >= 90) {
    return (
      <Alert className="border-green-500 bg-green-50 mb-4">
        <CheckCircle className="h-4 w-4 text-green-600" />
        <AlertTitle className="text-green-800">Reservatório Cheio</AlertTitle>
        <AlertDescription className="text-green-700">
          O reservatório está com {waterLevel}% de capacidade.
          {waterLevel >= 95 && " A bomba deve ser desligada em breve."}
        </AlertDescription>
      </Alert>
    );
  }

  return null;
}
