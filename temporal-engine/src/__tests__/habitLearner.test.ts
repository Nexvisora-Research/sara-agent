import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { TemporalGraphStore } from "../graph/store";
import { HabitLearner } from "../tracker/habitLearner";
import { tmpdir } from "node:os";
import { mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";

function makeNode(id: string, label: string, hour: number, dayOffset = 0, _dayOfWeek = 1) {
  const d = new Date("2026-01-05T00:00:00Z"); // Monday
  d.setDate(d.getDate() + dayOffset);
  d.setHours(hour, 0, 0, 0);
  return {
    id,
    type: "event" as const,
    label,
    startTime: d.getTime(),
    endTime: d.getTime() + 3600000,
    metadata: {} as Record<string, unknown>,
    tags: [] as string[],
    confidence: 1,
  };
}

describe("HabitLearner", () => {
  let store: TemporalGraphStore;
  let learner: HabitLearner;
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = mkdtempSync(join(tmpdir(), "habit-test-"));
    store = new TemporalGraphStore({
      storagePath: tmpDir,
      autoSaveIntervalMs: 0,
    });
    learner = new HabitLearner({ minObservations: 3, patternConfidence: 0.4 });
  });

  afterEach(() => {
    store.destroy();
    rmSync(tmpDir, { recursive: true, force: true });
  });

  it("discovers a daily habit pattern", () => {
    for (let d = 0; d < 10; d++) {
      store.addNode(makeNode(`m-${d}`, "Morning standup", 9, d));
    }

    const habits = learner.analyze(store);
    const standup = habits.find((h) => h.label === "Morning standup");
    expect(standup).toBeDefined();
    expect(standup!.timesObserved).toBe(10);
    expect(standup!.frequency).toBe(10);
    expect(standup!.timeDistribution.meanHour).toBeCloseTo(9, 0);
    expect(standup!.confidence).toBeGreaterThan(0.4);
  });

  it("detects no pattern with too few observations", () => {
    for (let d = 0; d < 2; d++) {
      store.addNode(makeNode(`s-${d}`, "Sporadic", 14, d));
    }
    const habits = learner.analyze(store);
    expect(habits.find((h) => h.label === "Sporadic")).toBeUndefined();
  });

  it("retrieves a known habit", () => {
    for (let d = 0; d < 5; d++) {
      store.addNode(makeNode(`c-${d}`, "Coffee break", 15, d));
    }
    learner.analyze(store);
    const habit = learner.getHabit("Coffee break");
    expect(habit).toBeDefined();
    expect(habit!.label).toBe("Coffee break");
  });

  it("clears all habits", () => {
    for (let d = 0; d < 5; d++) {
      store.addNode(makeNode(`x-${d}`, "Test habit", 10, d));
    }
    learner.analyze(store);
    expect(learner.getHabits().length).toBeGreaterThan(0);
    learner.clear();
    expect(learner.getHabits()).toHaveLength(0);
  });
});
