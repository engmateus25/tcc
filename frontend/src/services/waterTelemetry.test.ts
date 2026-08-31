import {
  buildPumpTelemetrySnapshot,
  buildSensorTelemetrySnapshot,
  deriveOperationalState,
  estimateVisualWaterLevel,
  formatSensorDateTime,
  getAutomaticPumpStateFromSensors,
  getEffectivePumpStateFromCommand,
  normalizePumpCommandDocument,
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

  it("normalizes applied pump commands as the effective pump state", () => {
    const snapshot = buildPumpTelemetrySnapshot(
      [
        {
          id: "auto-on",
          data: {
            command_id: "auto-1",
            timestamp: "2026-08-24T18:00:00Z",
            acionamento: "automático",
            applied_state: true,
            requested_state: true,
            applied: true,
            confirmed: true,
            state_changed: true,
          },
        },
      ],
      { fallbackDate: BASE },
    );

    const state = getEffectivePumpStateFromCommand(snapshot.effectiveCommand);

    expect(snapshot.status).toBe("connected");
    expect(state).toMatchObject({
      pumpOn: true,
      applied: true,
      confirmed: true,
      source: "firestore_command",
      mode: "automático",
      commandId: "auto-1",
    });
  });

  it("keeps overridden pump commands out of the effective pump state", () => {
    const command = normalizePumpCommandDocument(
      "remote-off",
      {
        timestamp: "2026-08-24T18:00:00Z",
        bomba: "bomba desligar",
        requested_state: false,
        applied_state: true,
        applied: false,
        confirmed: true,
        overridden_by: "físico",
      },
      BASE,
    );

    expect(command?.requestedState).toBe(false);
    expect(command?.appliedState).toBe(true);
    expect(getEffectivePumpStateFromCommand(command)).toBeNull();
  });

  it("infers the automatic pump intent from sensor boundaries until command confirmation arrives", () => {
    const lowDropped = normalizeSensorDocument(
      "sensor-low",
      { sensor: "baixo", estado: "desceu", timestamp: "2026-08-24T18:00:00Z" },
      BASE,
    )!;
    const lowRaised = normalizeSensorDocument(
      "sensor-low-up",
      { sensor: "baixo", estado: "subiu", timestamp: "2026-08-24T18:03:00Z" },
      BASE,
    )!;

    const state = getAutomaticPumpStateFromSensors([lowDropped, lowRaised]);

    expect(state).toMatchObject({
      pumpOn: true,
      confirmed: false,
      source: "sensor_automatic",
      mode: "automático",
    });
  });
});
