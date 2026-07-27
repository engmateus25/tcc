import { PropsWithChildren } from "react";
import { Droplets } from "lucide-react";
import { QuickHelp } from "../components/QuickHelp";
import { useWaterSystem } from "../hooks/useWaterSystem";
import { IonPage, IonHeader, IonContent, IonFooter } from "@ionic/react";


export default function AppLayout({ children }: PropsWithChildren) {
  const { isConnected } = useWaterSystem();

  return (
    <IonPage>
      {/* Ajuda flutuante (fica por cima) */}
      <QuickHelp />
 
      {/* HEADER fixo da app (fica SEMPRE visível) */}
      <IonHeader className="shadow-lg">
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white">
          <div className="container mx-auto px-4 py-6">
            <div className="flex items-center gap-3">
              <Droplets className="w-8 h-8" />
              <div>
                <h1 className="text-2xl">AquaMonitor</h1>
                <p className="text-sm text-blue-100">Sistema de Monitoramento de Água</p>
              </div>
            </div>
          </div>
        </div>
      </IonHeader>

      {/* CONTEÚDO rolável (as páginas entram aqui) */}
      <IonContent fullscreen>
        <main className="container mx-auto px-4 py-6">
          {children}
        </main>
      </IonContent>

      {/* FOOTER fixo da app (status de conexão) */}
      <IonFooter className="border-t border-slate-200">
        <div className="bg-white px-4 py-3">
          <div className="container mx-auto flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isConnected.firebase ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
              <span className="text-slate-600">Firebase {isConnected.firebase ? 'conectado' : 'desconectado'}</span>
            </div>
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isConnected.mqtt ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
              <span className="text-slate-600">MQTT {isConnected.mqtt ? 'conectado' : 'desconectado'}</span>
            </div>
          </div>
        </div>
      </IonFooter>
    </IonPage>
  );
}
