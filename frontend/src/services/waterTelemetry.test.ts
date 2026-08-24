import {
  buildSensorTelemetrySnapshot,
  deriveOperationalState,
  estimateVisualWaterLevel,
  formatSensorDateTime,
  normalizeSensorDocument,
  normalizeSensorTimestamp,
} from "./waterTelemetry";

const BASE = new Date("2026-08-24T18:32:10.000Z");

describe("waterTelemetry", () => {
  it("treats an empty server snapshot as connected", () => {
    const snapshot = buildSensorTelemetrySnapshot([], {
      fromCache: false,
      fallbackDate: BASE,
    });

    expect(snapshot.status).toBe("connected");
    expect(snapshot.latestEvent).toBeNull();
    expect(snapshot.events).toHaveLength(0);
  });

  it("normalizes a Firestore Timestamp-like value", () => {
    const result = normalizeSensorTimestamp({
      toDate: () => new Date("2026-08-24T18:32:10.000Z"),
    });

    expect(result.source).toBe("firestore_timestamp");
    expect(result.date.toISOString()).toBe("2026-08-24T18:32:10.000Z");
  });

  it("normalizes an ISO string timestamp", () => {
    const event = normalizeSensorDocument(
      "doc-1",
      { sensor: " ALTO ", estado: " SUBIU ", timestamp: "2026-08-24T18:32:10Z" },
      BASE,
    );

    expect(event?.sensor).toBe("alto");
    expect(event?.estado).toBe("subiu");
    expect(event?.timestampSource).toBe("iso_string");
  });

  it("falls back for legacy events without timestamp", () => {
    const event = normalizeSensorDocument(
      "legacy-1",
      { sensor: "baixo", estado: "desceu" },
      BASE,
    );

    expect(event?.timestampSource).toBe("legacy_fallback");
    expect(event?.timestamp.toISOString()).toBe(BASE.toISOString());
  });

  it("formats UTC timestamps in pt-BR", () => {
    expect(formatSensorDateTime(BASE)).toMatch(/24\/08\/2026 às/);
  });

  it("derives the operational state from sensor sequence and pump state", () => {
    const low = normalizeSensorDocument(
      "doc-1",
      { sensor: "baixo", estado: "desceu", timestamp: "2026-08-24T18:00:00Z" },
      BASE,
    )!;

    expect(deriveOperationalState([low], { pumpOn: true })).toBe("Enchendo");
    expect(deriveOperationalState([low], { pumpOn: false })).toBe("Nível baixo");
  });

  it("animates filling by elapsed timestamp and caps before high confirmation", () => {
    const low = normalizeSensorDocument(
      "doc-1",
      { sensor: "baixo", estado: "desceu", timestamp: "2026-08-24T18:00:00Z" },
      BASE,
    )!;

    const halfway = estimateVisualWaterLevel(
      [low],
      new Date("2026-08-24T18:04:00Z"),
      { pumpOn: true },
    );
    const capped = estimateVisualWaterLevel(
      [low],
      new Date("2026-08-24T18:12:00Z"),
      { pumpOn: true },
    );

    expect(halfway.level).toBeGreaterThan(20);
    expect(halfway.level).toBeLessThan(99);
    expect(capped.level).toBe(99);
    expect(capped.waitingForHighConfirmation).toBe(true);
  });

  it("animates draining down to the visual floor", () => {
    const highDown = normalizeSensorDocument(
      "doc-1",
      { sensor: "alto", estado: "desceu", timestamp: "2026-08-24T18:00:00Z" },
      BASE,
    )!;

    const drained = estimateVisualWaterLevel(
      [highDown],
      new Date("2026-08-24T18:20:00Z"),
      { pumpOn: false },
    );

    expect(drained.level).toBe(21);
    expect(drained.phase).toBe("draining");
  });
});
