import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { TemporalGraphStore } from "../graph/store";
import { ConflictDetector } from "../analyzer/conflictDetector";
import { tmpdir } from "node:os";
import { mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";

describe("ConflictDetector", () => {
  let store: TemporalGraphStore;
  let detector: ConflictDetector;
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = mkdtempSync(join(tmpdir(), "conflict-test-"));
    store = new TemporalGraphStore({
      storagePath: tmpDir,
      autoSaveIntervalMs: 0,
    });
    detector = new ConflictDetector();
  });

  afterEach(() => {
    store.destroy();
    rmSync(tmpDir, { recursive: true, force: true });
  });

  it("detects overlapping events", () => {
    const now = Date.now();
    store.addNode({
      id: "a", type: "event", label: "Meeting A", startTime: now,
      endTime: now + 3600000, metadata: {}, tags: [], confidence: 1,
    });
    store.addNode({
      id: "b", type: "event", label: "Meeting B", startTime: now + 1800000,
      endTime: now + 5400000, metadata: {}, tags: [], confidence: 1,
    });

    const conflicts = detector.detectOverlaps(store);
    expect(conflicts).toHaveLength(1);
    expect(conflicts[0].type).toBe("overlap");
    expect(conflicts[0].involvedNodeIds).toContain("a");
    expect(conflicts[0].involvedNodeIds).toContain("b");
    expect(conflicts[0].suggestion).toBeTruthy();
  });

  it("detects no overlap for non-overlapping events", () => {
    const now = Date.now();
    store.addNode({
      id: "a", type: "event", label: "Early", startTime: now,
      endTime: now + 3600000, metadata: {}, tags: [], confidence: 1,
    });
    store.addNode({
      id: "b", type: "event", label: "Late", startTime: now + 3600000,
      endTime: now + 7200000, metadata: {}, tags: [], confidence: 1,
    });

    expect(detector.detectOverlaps(store)).toHaveLength(0);
  });

  it("detects deadline risks", () => {
    const now = Date.now();
    store.addNode({
      id: "deadline", type: "deadline", label: "Ship v2", startTime: now + 3600000,
      metadata: {}, tags: [], confidence: 1,
    });
    store.addNode({
      id: "task1", type: "task", label: "Write code", startTime: now,
      endTime: now + 3600000, metadata: {}, tags: [], confidence: 1,
    });

    store.addEdge({
      id: "dep", sourceId: "task1", targetId: "deadline",
      type: "depends_on", weight: 1, metadata: {},
    });

    // Tight deadline: 1h of work in 1h window = 100% utilization
    const risks = detector.detectDeadlineRisks(store);
    expect(risks.length).toBeGreaterThan(0);
    expect(risks[0].type).toBe("deadline_risk");
  });

  it("detects dependency breaches", () => {
    const now = Date.now();
    store.addNode({
      id: "depA", type: "task", label: "Setup DB", startTime: now,
      endTime: now + 3600000, metadata: {}, tags: [], confidence: 1,
    });
    store.addNode({
      id: "depB", type: "task", label: "Build UI", startTime: now + 1800000,
      endTime: now + 5400000, metadata: {}, tags: [], confidence: 1,
    });

    store.addEdge({
      id: "e1", sourceId: "depA", targetId: "depB",
      type: "depends_on", weight: 1, metadata: {},
    });

    // depB starts before depA finishes → breach
    const breaches = detector.detectDependencyBreaches(store);
    expect(breaches).toHaveLength(1);
    expect(breaches[0].type).toBe("dependency_breach");
  });

  it("scores future impact for a node", () => {
    const now = Date.now();
    store.addNode({
      id: "impact-a", type: "task", label: "Critical Path", startTime: now,
      endTime: now + 3600000, metadata: {}, tags: ["critical"], confidence: 1,
    });
    store.addNode({
      id: "impact-b", type: "task", label: "Follow-up", startTime: now + 3600000,
      endTime: now + 7200000, metadata: {}, tags: [], confidence: 1,
    });

    store.addEdge({
      id: "imp-edge", sourceId: "impact-a", targetId: "impact-b",
      type: "depends_on", weight: 1, metadata: {},
    });

    const score = detector.scoreFutureImpact("impact-a", store);
    expect(score.score).toBeGreaterThan(0);
    expect(score.affectedNodes).toContain("impact-b");
    expect(score.rippleEffect).toBe(1);
    expect(score.breakdown.tag_importance).toBeGreaterThan(0);
  });
});
