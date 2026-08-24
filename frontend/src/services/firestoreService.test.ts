import { vi } from "vitest";
import type { SensorTelemetrySnapshot } from "./waterTelemetry";

const onSnapshotMock = vi.fn();

vi.mock("./firestoreConfig", () => ({
  db: { app: "test" },
  firebaseConfigError: null,
}));

vi.mock("firebase/firestore", () => ({
  collection: vi.fn((_db, name) => ({ name })),
  query: vi.fn((...args) => ({ args })),
  getDocs: vi.fn(),
  where: vi.fn(),
  orderBy: vi.fn(),
  limit: vi.fn(),
  onSnapshot: (...args: unknown[]) => onSnapshotMock(...args),
  Timestamp: class Timestamp {},
}));

describe("firestoreService listener", () => {
  beforeEach(() => {
    onSnapshotMock.mockReset();
  });

  it("emits connected status for an empty snapshot", async () => {
    let next: (snapshot: unknown) => void = () => undefined;
    onSnapshotMock.mockImplementation((_query, _options, onNext) => {
      next = onNext as (snapshot: unknown) => void;
      return vi.fn();
    });

    const { listenSensorTelemetry } = await import("./firestoreService");
    const received: unknown[] = [];
    listenSensorTelemetry((snapshot) => received.push(snapshot));

    next({
      docs: [],
      metadata: { fromCache: false },
    });

    expect(received).toMatchObject([
      {
        status: "connected",
        latestEvent: null,
        events: [],
      },
    ]);
  });

  it("normalizes realtime changes from Firestore documents", async () => {
    let next: (snapshot: unknown) => void = () => undefined;
    onSnapshotMock.mockImplementation((_query, _options, onNext) => {
      next = onNext as (snapshot: unknown) => void;
      return vi.fn();
    });

    const { listenSensorTelemetry } = await import("./firestoreService");
    const received: SensorTelemetrySnapshot[] = [];
    listenSensorTelemetry((snapshot) => received.push(snapshot));

    next({
      docs: [
        {
          id: "sensor-1",
          data: () => ({
            sensor: "alto",
            estado: "subiu",
            timestamp: "2026-08-24T18:32:10Z",
          }),
        },
      ],
      metadata: { fromCache: false },
    });

    expect(received[0].status).toBe("connected");
    expect(received[0].latestEvent).toMatchObject({
      sensor: "alto",
      estado: "subiu",
    });
  });

  it("emits error status when the listener fails", async () => {
    let onError: (error: Error) => void = () => undefined;
    onSnapshotMock.mockImplementation((_query, _options, _onNext, errorHandler) => {
      onError = errorHandler as (error: Error) => void;
      return vi.fn();
    });

    const { listenSensorTelemetry } = await import("./firestoreService");
    const received: SensorTelemetrySnapshot[] = [];
    listenSensorTelemetry((snapshot) => received.push(snapshot));

    onError(new Error("permission denied"));

    expect(received[0].status).toBe("error");
    expect(received[0].error).toBe("permission denied");
  });
});
