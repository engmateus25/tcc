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
    <Card className="p-4">
      <p className="text-sm text-slate-600 mb-3">Controle da Bomba</p>
      <motion.button
        className={`w-full py-6 rounded-lg flex flex-col items-center justify-center gap-2 transition-colors ${
          isOn 
            ? "bg-green-600 text-white" 
            : "bg-slate-300 text-slate-700"
        }`}
        onClick={onToggle}
        disabled={isPending}
        whileTap={{ scale: 0.95 }}
      >
        <Power className="w-8 h-8" />
        <span className="text-xl">{isPending ? "..." : isOn ? "ON" : "OFF"}</span>
      </motion.button>
      <p className="mt-2 min-h-8 text-xs text-slate-500">
        {statusMessage || "Estado alterado apenas após confirmação."}
      </p>
    </Card>
  );
}
