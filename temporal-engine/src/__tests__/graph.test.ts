import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { TemporalGraphStore } from "../graph/store";
import { tmpdir } from "node:os";
import { mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";

describe("TemporalGraphStore", () => {
  let store: TemporalGraphStore;
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = mkdtempSync(join(tmpdir(), "temporal-test-"));
    store = new TemporalGraphStore({
      storagePath: tmpDir,
      autoSaveIntervalMs: 0,
      maxNodes: 1000,
      maxEdges: 2000,
    });
  });

  afterEach(() => {
    store.destroy();
    rmSync(tmpDir, { recursive: true, force: true });
  });

  it("adds and retrieves a node", () => {
    const node = store.addNode({
      id: "test-1",
      type: "task",
      label: "Write tests",
      startTime: Date.now(),
      endTime: Date.now() + 3600000,
      metadata: {},
      tags: ["testing"],
      confidence: 0.9,
    });
    expect(node.id).toBe("test-1");
    expect(store.getNode("test-1")?.label).toBe("Write tests");
  });

  it("updates a node", () => {
    store.addNode({
      id: "u1", type: "task", label: "Old", startTime: 0,
      metadata: {}, tags: [], confidence: 0.5,
    });
    store.updateNode("u1", { label: "New", confidence: 0.9 });
    expect(store.getNode("u1")?.label).toBe("New");
    expect(store.getNode("u1")?.confidence).toBe(0.9);
  });

  it("deletes a node and its edges", () => {
    store.addNode({
      id: "a", type: "task", label: "A", startTime: 0,
      metadata: {}, tags: [], confidence: 0.5,
    });
    store.addNode({
      id: "b", type: "task", label: "B", startTime: 0,
      metadata: {}, tags: [], confidence: 0.5,
    });
    store.addEdge({ id: "e1", sourceId: "a", targetId: "b", type: "depends_on", weight: 1, metadata: {} });

    expect(store.getEdges("a").length).toBe(1);
    store.deleteNode("a");
    expect(store.getNode("a")).toBeUndefined();
    expect(store.getEdges("a").length).toBe(0);
  });

  it("queries nodes by type and time range", () => {
    const now = Date.now();
    store.addNode({
      id: "t1", type: "task", label: "Task 1", startTime: now,
      metadata: {}, tags: [], confidence: 0.5,
    });
    store.addNode({
      id: "e1", type: "event", label: "Event 1", startTime: now + 86400000,
      metadata: {}, tags: [], confidence: 0.5,
    });

    const tasks = store.queryNodes({ types: ["task"] });
    expect(tasks).toHaveLength(1);
    expect(tasks[0].id).toBe("t1");

    const future = store.queryNodes({ after: now + 3600000 });
    expect(future).toHaveLength(1);
    expect(future[0].id).toBe("e1");
  });

  it("manages edges between nodes", () => {
    store.addNode({
      id: "a", type: "task", label: "A", startTime: 0,
      metadata: {}, tags: [], confidence: 0.5,
    });
    store.addNode({
      id: "b", type: "task", label: "B", startTime: 0,
      metadata: {}, tags: [], confidence: 0.5,
    });
    const edge = store.addEdge({
      id: "e1", sourceId: "a", targetId: "b",
      type: "precedes", weight: 1, metadata: {},
    });
    expect(edge).not.toBeNull();
    expect(store.getEdges("a", "outgoing")).toHaveLength(1);
    expect(store.getEdges("b", "incoming")).toHaveLength(1);
  });

  it("finds paths between nodes", () => {
    store.addNode({
      id: "a", type: "task", label: "A", startTime: 0,
      metadata: {}, tags: [], confidence: 0.5,
    });
    store.addNode({
      id: "b", type: "task", label: "B", startTime: 0,
      metadata: {}, tags: [], confidence: 0.5,
    });
    store.addNode({
      id: "c", type: "task", label: "C", startTime: 0,
      metadata: {}, tags: [], confidence: 0.5,
    });
    store.addEdge({
      id: "e1", sourceId: "a", targetId: "b", type: "depends_on", weight: 1, metadata: {},
    });
    store.addEdge({
      id: "e2", sourceId: "b", targetId: "c", type: "depends_on", weight: 1, metadata: {},
    });

    const path = store.findPath({ fromId: "a", toId: "c" });
    expect(path).toHaveLength(3);
    expect(path.map((n) => n.id)).toEqual(["a", "b", "c"]);
  });

  it("handles timelines and overdue queries", () => {
    const now = Date.now();
    store.addNode({
      id: "past", type: "task", label: "Past", startTime: now - 86400000,
      endTime: now - 3600000, metadata: {}, tags: [], confidence: 0.5,
    });
    store.addNode({
      id: "future", type: "event", label: "Future", startTime: now + 86400000,
      metadata: {}, tags: [], confidence: 0.5,
    });

    const upcoming = store.getUpcoming();
    expect(upcoming).toHaveLength(1);
    expect(upcoming[0].id).toBe("future");

    const overdue = store.getOverdue();
    expect(overdue).toHaveLength(1);
    expect(overdue[0].id).toBe("past");
  });

  it("exports and imports snapshots", () => {
    store.addNode({
      id: "s1", type: "milestone", label: "Snapshot test", startTime: 0,
      metadata: {}, tags: [], confidence: 0.9,
    });

    const snapshot = store.exportSnapshot();
    expect(snapshot.nodes).toHaveLength(1);
    expect(snapshot.version).toBe(1);

    const store2 = new TemporalGraphStore({
      storagePath: join(tmpDir, "import-test"),
      autoSaveIntervalMs: 0,
    });
    store2.importSnapshot(snapshot);
    expect(store2.getNode("s1")?.label).toBe("Snapshot test");
    store2.destroy();
  });

  it("reports stats", () => {
    store.addNode({
      id: "st1", type: "task", label: "S1", startTime: 0,
      metadata: {}, tags: [], confidence: 0.5,
    });
    store.addNode({
      id: "st2", type: "event", label: "S2", startTime: 0,
      metadata: {}, tags: [], confidence: 0.5,
    });

    const s = store.stats();
    expect(s.nodeCount).toBe(2);
    expect(s.byType.task).toBe(1);
    expect(s.byType.event).toBe(1);
  });
});
