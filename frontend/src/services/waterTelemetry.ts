export type FirebaseConnectionStatus =
  | "connecting"
  | "connected"
  | "offline"
  | "error";

export type SensorName = "baixo" | "alto";
export type SensorAction = "subiu" | "desceu";
export type ReservoirPhase = "filling" | "draining" | "full" | "low" | "unknown";

export interface NormalizedSensorEvent {
  id: string;
  sensor: SensorName;
  estado: SensorAction;
  timestamp: Date;
  timestampSource: "firestore_timestamp" | "date" | "iso_string" | "seconds" | "legacy_fallback";
  deviceId?: string | null;
  source?: string | null;
}

export interface SensorTelemetrySnapshot {
  status: FirebaseConnectionStatus;
  events: NormalizedSensorEvent[];
  latestEvent: NormalizedSensorEvent | null;
  fromCache: boolean;
  error?: string | null;
}

export interface PumpVisualState {
  pumpOn: boolean;
  confirmed?: boolean;
}

export interface VisualWaterLevelState {
  level: number;
  phase: ReservoirPhase;
  label: string;
  waitingForHighConfirmation: boolean;
}

export const WATER_LEVEL_ESTIMATION_CONFIG = {
  lowSensorLevelPercent: 20,
  lowSensorRaisedLevelPercent: 55,
  maxLevelPercent: 100,
  drainFloorPercent: 21,
  fillDurationSeconds: 480,
  drainDurationSeconds: 480,
  fillCapBeforeHighConfirmationPercent: 99,
  tankCapacityLiters: 5000,
} as const;

type TimestampLike = {
  toDate?: () => Date;
  seconds?: number;
  nanoseconds?: number;
};

export function normalizeSensorDocument(
  id: string,
  data: Record<string, unknown>,
  fallbackDate = new Date(),
): NormalizedSensorEvent | null {
  const sensor = normalizeSensorName(data.sensor);
  const estado = normalizeSensorAction(data.estado);
  if (!sensor || !estado) {
    return null;
  }

  const { date, source } = normalizeSensorTimestamp(data.timestamp, fallbackDate);

  return {
    id,
    sensor,
    estado,
    timestamp: date,
    timestampSource: source,
    deviceId: readOptionalString(data.device_id),
    source: readOptionalString(data.source),
  };
}

export function normalizeSensorTimestamp(
  value: unknown,
  fallbackDate = new Date(),
): {
  date: Date;
  source: NormalizedSensorEvent["timestampSource"];
} {
  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    return { date: value, source: "date" };
  }

  if (typeof value === "string" && value.trim()) {
    const parsed = new Date(value);
    if (!Number.isNaN(parsed.getTime())) {
      return { date: parsed, source: "iso_string" };
    }
  }

  if (isTimestampLike(value)) {
    if (typeof value.toDate === "function") {
      const date = value.toDate();
      if (!Number.isNaN(date.getTime())) {
        return { date, source: "firestore_timestamp" };
      }
    }

    if (typeof value.seconds === "number") {
      const milliseconds =
        value.seconds * 1000 +
        Math.floor((value.nanoseconds || 0) / 1_000_000);
      return { date: new Date(milliseconds), source: "seconds" };
    }
  }

  return { date: fallbackDate, source: "legacy_fallback" };
}

export function buildSensorTelemetrySnapshot(
  docs: Array<{ id: string; data: Record<string, unknown> }>,
  options: {
    fromCache?: boolean;
    fallbackDate?: Date;
  } = {},
): SensorTelemetrySnapshot {
  const fallbackDate = options.fallbackDate || new Date();
  const events = docs
    .map((doc) => normalizeSensorDocument(doc.id, doc.data, fallbackDate))
    .filter((event): event is NormalizedSensorEvent => Boolean(event))
    .sort((left, right) => right.timestamp.getTime() - left.timestamp.getTime());

  const fromCache = Boolean(options.fromCache);
  return {
    status: fromCache ? "offline" : "connected",
    events,
    latestEvent: events[0] || null,
    fromCache,
    error: null,
  };
}

export function formatSensorDateTime(date: Date): string {
  return date.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).replace(",", " às");
}

export function deriveOperationalState(
  events: NormalizedSensorEvent[],
  pump?: PumpVisualState | null,
): string {
  const latest = [...events].sort(
    (left, right) => right.timestamp.getTime() - left.timestamp.getTime(),
  )[0];

  if (latest?.sensor === "alto" && latest.estado === "subiu") {
    return "Reservatório cheio";
  }

  if (latest?.sensor === "baixo" && latest.estado === "desceu") {
    return pump?.pumpOn ? "Enchendo" : "Nível baixo";
  }

  if (pump?.pumpOn) {
    return "Enchendo";
  }

  if (latest?.sensor === "alto" && latest.estado === "desceu") {
    return "Esvaziando";
  }

  if (latest?.sensor === "baixo" && latest.estado === "subiu") {
    return "Enchendo";
  }

  return "Aguardando leitura";
}

export function estimateVisualWaterLevel(
  events: NormalizedSensorEvent[],
  now = new Date(),
  pump?: PumpVisualState | null,
  config = WATER_LEVEL_ESTIMATION_CONFIG,
): VisualWaterLevelState {
  const latest = [...events].sort(
    (left, right) => right.timestamp.getTime() - left.timestamp.getTime(),
  )[0];

  if (!latest) {
    return {
      level: config.lowSensorRaisedLevelPercent,
      phase: "unknown",
      label: "Aguardando leitura",
      waitingForHighConfirmation: false,
    };
  }

  if (latest.sensor === "alto" && latest.estado === "subiu") {
    return {
      level: config.maxLevelPercent,
      phase: "full",
      label: "Reservatório cheio",
      waitingForHighConfirmation: false,
    };
  }

  if (latest.sensor === "baixo" && latest.estado === "desceu") {
    return buildFillingLevel(
      latest.timestamp,
      now,
      config.lowSensorLevelPercent,
      pump,
      config,
    );
  }

  if (latest.sensor === "baixo" && latest.estado === "subiu") {
    return buildFillingLevel(
      latest.timestamp,
      now,
      config.lowSensorRaisedLevelPercent,
      pump,
      config,
    );
  }

  if (latest.sensor === "alto" && latest.estado === "desceu") {
    const elapsedSeconds = elapsedSecondsFrom(latest.timestamp, now);
    const progress = clamp(elapsedSeconds / config.drainDurationSeconds, 0, 1);
    const level =
      config.maxLevelPercent -
      (config.maxLevelPercent - config.drainFloorPercent) * progress;
    return {
      level: Math.max(config.drainFloorPercent, Math.round(level)),
      phase: "draining",
      label: "Esvaziando",
      waitingForHighConfirmation: false,
    };
  }

  return {
    level: config.lowSensorRaisedLevelPercent,
    phase: "unknown",
    label: deriveOperationalState(events, pump),
    waitingForHighConfirmation: false,
  };
}

function buildFillingLevel(
  startedAt: Date,
  now: Date,
  startLevel: number,
  pump: PumpVisualState | null | undefined,
  config: typeof WATER_LEVEL_ESTIMATION_CONFIG,
): VisualWaterLevelState {
  const elapsedSeconds = elapsedSecondsFrom(startedAt, now);
  const progress = clamp(elapsedSeconds / config.fillDurationSeconds, 0, 1);
  const physicalCap = config.fillCapBeforeHighConfirmationPercent;
  const level = startLevel + (physicalCap - startLevel) * progress;
  const pumpConfirmedOff = pump && pump.confirmed && !pump.pumpOn;

  return {
    level: pumpConfirmedOff ? startLevel : Math.min(physicalCap, Math.round(level)),
    phase: "filling",
    label: pumpConfirmedOff ? "Nível baixo" : "Enchendo",
    waitingForHighConfirmation: !pumpConfirmedOff && progress >= 1,
  };
}

function elapsedSecondsFrom(startedAt: Date, now: Date): number {
  return Math.max(0, (now.getTime() - startedAt.getTime()) / 1000);
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function normalizeSensorName(value: unknown): SensorName | null {
  if (typeof value !== "string") return null;
  const text = value.trim().toLowerCase();
  if (text === "baixo" || text === "alto") return text;
  return null;
}

function normalizeSensorAction(value: unknown): SensorAction | null {
  if (typeof value !== "string") return null;
  const text = value.trim().toLowerCase();
  if (text === "subiu" || text === "desceu") return text;
  return null;
}

function readOptionalString(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const text = value.trim();
  return text || null;
}

function isTimestampLike(value: unknown): value is TimestampLike {
  return typeof value === "object" && value !== null;
}
