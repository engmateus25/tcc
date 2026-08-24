import { 
  collection, query, getDocs, where, orderBy, 
  limit, onSnapshot, Unsubscribe, Timestamp,
  type FirestoreError, type QueryConstraint,
} from "firebase/firestore";
import { db, firebaseConfigError } from "./firestoreConfig";
import {
  buildSensorTelemetrySnapshot,
  SensorTelemetrySnapshot,
} from "./waterTelemetry";

type FirestoreTimestampLike =
  | Timestamp
  | Date
  | string
  | { seconds: number }
  | null
  | undefined;

type SensorDocumentData = {
  sensor?: unknown;
  estado?: unknown;
  timestamp?: FirestoreTimestampLike;
};

export type SensorHistoryItem = {
  id: string;
  sensor: string;
  estado: string;
  timestamp: FirestoreTimestampLike | string;
};

function readString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

export const carregarUltimoEstado = async () => {
  try {
    if (!db) {
      logFirebaseConfigError();
      return null;
    }
    const sensoresRef = collection(db, "sensores");
    const q = query(sensoresRef, orderBy("timestamp", "desc"));
    const querySnapshot = await getDocs(q);

    const historico: SensorHistoryItem[] = [];
    querySnapshot.forEach((doc) => {
      const data = doc.data() as SensorDocumentData;
      historico.push({
        id: doc.id,
        sensor: readString(data.sensor),
        estado: readString(data.estado),
        timestamp: data.timestamp
      });
    });

    return historico[0] || null; 
  } catch (error) {
    console.error("Erro ao carregar último estado:", error);
    return null;
  }
};


export const buscarComFiltros = async (sensorFiltro: string, dataInicio: string, dataFim: string) => {
  try {
    if (!db) {
      logFirebaseConfigError();
      return [];
    }
    const sensoresRef = collection(db, "sensores");
    const filtros: QueryConstraint[] = [];

    if (dataInicio && dataFim) {
      const inicioDate = new Date(dataInicio + "T00:00:00");
      const fimDate = new Date(dataFim + "T23:59:59");
      filtros.push(where("timestamp", ">=", inicioDate));
      filtros.push(where("timestamp", "<=", fimDate));
    }

    if (sensorFiltro.trim() !== "") {
      filtros.push(where("sensor", "==", sensorFiltro.trim().toLowerCase()));
    }

    let q;

    if (filtros.length > 0) {
      q = query(sensoresRef, ...filtros, orderBy("timestamp", "desc"));
    } else {
      q = query(sensoresRef, orderBy("timestamp", "desc"));
    }

    const querySnapshot = await getDocs(q);

    const dados: SensorHistoryItem[] = [];
    querySnapshot.forEach(doc => {
      const data = doc.data() as SensorDocumentData;
      dados.push({
        id: doc.id,
        sensor: readString(data.sensor),
        estado: readString(data.estado),
        timestamp: normalizeTimestamp(data.timestamp).toLocaleString()
      });
    });

    return dados;
  } catch (error) {
    console.error("Erro ao buscar dados com filtros:", error);
    return [];
  }
};


// ---------- listener realtime do ÚLTIMO evento da coleção `sensores` ----------
export type UltimoEvento = {
  id: string;
  sensor: string;
  estado: string;
  timestamp: Date;
};

function normalizeTimestamp(ts: FirestoreTimestampLike): Date {
  if (ts instanceof Date) return ts;
  if (ts instanceof Timestamp) return ts.toDate();
  if (ts && typeof ts === "object" && "seconds" in ts && typeof ts.seconds === "number") {
    return new Date(ts.seconds * 1000);
  }
  if (typeof ts === "string") return new Date(ts);
  return new Date();
}

/**
 * Compatibilidade para componentes antigos: observa o último documento válido
 * da coleção `sensores`, sem tratar snapshot vazio como desconexão.
 */
export function listenUltimoEstado(
  onChange: (ev: UltimoEvento | null) => void,
  onError?: (e: FirestoreError) => void
): Unsubscribe {
  return listenSensorTelemetry(
    (snapshot) => {
      const latest = snapshot.latestEvent;
      onChange(
        latest
          ? {
              id: latest.id,
              sensor: latest.sensor,
              estado: latest.estado,
              timestamp: latest.timestamp,
            }
          : null,
      );
    },
    onError,
    { limitCount: 1 },
  );
}

export function listenSensorTelemetry(
  onChange: (snapshot: SensorTelemetrySnapshot) => void,
  onError?: (e: FirestoreError) => void,
  options: { limitCount?: number } = {},
): Unsubscribe {
  if (!db) {
    logFirebaseConfigError();
    onChange({
      status: "error",
      events: [],
      latestEvent: null,
      fromCache: false,
      error: firebaseConfigError || "Firebase não configurado",
    });
    return () => undefined;
  }

  const sensoresRef = collection(db, "sensores");
  const q = query(
    sensoresRef,
    orderBy("timestamp", "desc"),
    limit(options.limitCount || 10),
  );

  return onSnapshot(
    q,
    { includeMetadataChanges: true },
    (snap) => {
      const docs = snap.docs.map((doc) => ({
        id: doc.id,
        data: doc.data() as Record<string, unknown>,
      }));
      onChange(
        buildSensorTelemetrySnapshot(docs, {
          fromCache: snap.metadata.fromCache,
        }),
      );
    },
    (err) => {
      onChange({
        status: "error",
        events: [],
        latestEvent: null,
        fromCache: false,
        error: err.message,
      });
      onError?.(err);
    },
  );
}

function logFirebaseConfigError() {
  if (firebaseConfigError) {
    console.error(firebaseConfigError);
  }
}
