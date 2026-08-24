import { Card } from "./ui/card";
import { Badge } from "./ui/badge";
import { ArrowUp, ArrowDown, Clock, Radio } from "lucide-react";
import type { LastSensor } from "../types/water-system";

interface SensorStatusProps {
  sensor: LastSensor | null;
  connectionLabel?: string;
}

export function SensorStatus({ sensor, connectionLabel }: SensorStatusProps) {
  const isUp = sensor?.action === "subiu";

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <p className="text-sm text-slate-600 mb-2">Último Sensor Alterado</p>
          {sensor ? (
            <>
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <Badge
                  variant={isUp ? "default" : "secondary"}
                  className={isUp ? "bg-green-600" : "bg-orange-600"}
                >
                  {isUp ? <ArrowUp className="w-3 h-3 mr-1" /> : <ArrowDown className="w-3 h-3 mr-1" />}
                  Sensor {sensor.name}
                </Badge>
                <span className="text-sm text-slate-700">{sensor.action}</span>
              </div>
              <p className="mb-2 text-base text-slate-800">
                {sensor.operationalState}
              </p>
              <div className="flex items-center gap-1 text-sm text-slate-500">
                <Clock className="w-4 h-4" />
                <span>{sensor.dateTime}</span>
              </div>
            </>
          ) : (
            <div className="rounded-md border border-dashed border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-500">
              <div className="flex items-center gap-2">
                <Radio className="h-4 w-4" />
                <span>{connectionLabel || "Aguardando primeira leitura do Firestore"}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
