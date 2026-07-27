import { 
  collection, query, getDocs, where, orderBy, 
  limit, onSnapshot, Unsubscribe, Timestamp,
  type FirestoreError, type QueryConstraint,
} from "firebase/firestore";
import { db } from "./firestoreConfig";

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
 * Observa em tempo real o último documento de `sensores`.
 * Usa orderBy("timestamp","desc") + limit(1).
 */
export function listenUltimoEstado(
  onChange: (ev: UltimoEvento | null) => void,
  onError?: (e: FirestoreError) => void
): Unsubscribe {
  const sensoresRef = collection(db, "sensores");
  const q = query(sensoresRef, orderBy("timestamp", "desc"), limit(1));

  return onSnapshot(
    q,
    (snap) => {
      if (snap.empty) {
        onChange(null);
        return;
      }
      const doc = snap.docs[0];
      const data = doc.data() as SensorDocumentData;
      onChange({
        id: doc.id,
        sensor: readString(data.sensor),
        estado: readString(data.estado),
        timestamp: normalizeTimestamp(data.timestamp),
      });
    },
    (err) => onError?.(err)
  );
}
