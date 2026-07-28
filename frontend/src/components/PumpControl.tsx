import { Card } from "./ui/card";
import { motion } from "motion/react";
import { Power } from "lucide-react";

interface PumpControlProps {
  isOn: boolean;
  onToggle: () => void;
  isPending?: boolean;
  statusMessage?: string | null;
}

export function PumpControl({
  isOn,
  onToggle,
  isPending = false,
  statusMessage,
}: PumpControlProps) {
  return (
    <Card className="pump-card">
      <p className="pump-card-title">Controle da Bomba</p>
      <motion.button
        className={`pump-toggle-button ${
          isOn ? "pump-toggle-button-on" : "pump-toggle-button-off"
        }`}
        onClick={onToggle}
        disabled={isPending}
        whileTap={{ scale: 0.95 }}
      >
        <Power className="w-8 h-8" />
        <span>{isPending ? "..." : isOn ? "ON" : "OFF"}</span>
      </motion.button>
      <p className="pump-card-status">
        {statusMessage || "Estado alterado apenas após confirmação."}
      </p>
    </Card>
  );
}
