import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { TemporalGraphStore } from "../graph/store";
import { PredictiveScheduler } from "../predictor/scheduler";
import { HabitLearner } from "../tracker/habitLearner";
import { tmpdir } from "node:os";
import { mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";

describe("PredictiveScheduler", () => {
  let store: TemporalGraphStore;
  let predictor: PredictiveScheduler;
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = mkdtempSync(join(tmpdir(), "predict-test-"));
    store = new TemporalGraphStore({
      storagePath: tmpDir,
      autoSaveIntervalMs: 0,
    });
    predictor = new PredictiveScheduler({ horizonDays: 7 });
  });

  afterEach(() => {
    store.destroy();
    rmSync(tmpDir, { recursive: true, force: true });
  });

  it("predicts completion for a node with historical data", () => {
    const now = Date.now();
    for (let i = 0; i < 5; i++) {
      store.addNode({
        id: `hist-${i}`,
        type: "task",
        label: "Write report",
        startTime: now - (i + 1) * 86400000,
        endTime: now - (i + 1) * 86400000 + 7200000,
        metadata: {},
        tags: [],
        confidence: 1,
      });
    }

    const node = store.addNode({
      id: "current",
      type: "task",
      label: "Write report",
      startTime: now,
      endTime: now + 3600000,
      metadata: {},
      tags: [],
      confidence: 1,
    });

    const result = predictor.predictCompletion(node!, store);
    expect(result.eventId).toBe("current");
    expect(result.confidence).toBeGreaterThan(0);
    expect(result.probabilityDistribution.mean).toBeGreaterThan(0);
    expect(result.probabilityDistribution.p50).toBeGreaterThan(0);
    expect(result.factors.length).toBeGreaterThan(0);
  });

  it("predicts optimal window using habit data", () => {
    const node = store.addNode({
      id: "opt-test",
      type: "task",
      label: "Deep work",
      startTime: Date.now(),
      endTime: Date.now() + 7200000,
      metadata: {},
      tags: [],
      confidence: 1,
    });

    const habits = new HabitLearner({ minObservations: 1, patternConfidence: 0.1 });

    const result = predictor.predictOptimalWindow(node!, habits);
    expect(result.windowStart).toBeGreaterThan(0);
    expect(result.windowEnd).toBeGreaterThan(result.windowStart);
    expect(result.score).toBeGreaterThanOrEqual(0);
  });

  it("forecasts future load", () => {
    const now = Date.now();
    for (let d = 0; d < 3; d++) {
      for (let h = 0; h < 3; h++) {
        store.addNode({
          id: `load-${d}-${h}`,
          type: "task",
          label: `Task ${d}-${h}`,
          startTime: now + d * 86400000 + h * 3600000,
          endTime: now + d * 86400000 + h * 3600000 + 3600000,
          metadata: {},
          tags: [],
          confidence: 1,
        });
      }
    }

    const forecast = predictor.predictFutureLoad(store);
    expect(forecast.length).toBe(7);
    expect(forecast[0].taskCount).toBe(3);
    expect(forecast[0].estimatedHours).toBe(3);
  });
});
