import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";
import type {
  TemporalNode,
  TemporalEdge,
  GraphQuery,
  PathQuery,
  StorageSnapshot,
  EdgeType,
  NodeType,
} from "../types";

export class TemporalGraphStore {
  private nodes: Map<string, TemporalNode> = new Map();
  private edges: Map<string, TemporalEdge> = new Map();
  private adjacency: Map<string, Set<string>> = new Map();

  private storagePath: string;
  private autoSave: boolean;
  private maxNodes: number;
  private maxEdges: number;
  private saveTimer: ReturnType<typeof setInterval> | null = null;
  private dirty = false;

  constructor(opts?: {
    storagePath?: string;
    autoSaveIntervalMs?: number;
    maxNodes?: number;
    maxEdges?: number;
  }) {
    const base = opts?.storagePath ?? join(homedir(), ".sara", "temporal");
    if (!existsSync(base)) mkdirSync(base, { recursive: true });
    this.storagePath = join(base, "graph.json");
    this.maxNodes = opts?.maxNodes ?? 50_000;
    this.maxEdges = opts?.maxEdges ?? 200_000;
    this.autoSave = (opts?.autoSaveIntervalMs ?? 30_000) > 0;

    this._load();
    if (this.autoSave) {
      const ms = opts?.autoSaveIntervalMs ?? 30_000;
      this.saveTimer = setInterval(() => this._flush(), ms);
    }
  }

  // ─── Node Operations ──────────────────────────────────────────────

  addNode(node: Omit<TemporalNode, "createdAt" | "updatedAt">): TemporalNode {
    if (this.nodes.size >= this.maxNodes) this._evictNodes();
    const now = Date.now();
    const n: TemporalNode = { ...node, createdAt: now, updatedAt: now };
    this.nodes.set(n.id, n);
    this.adjacency.set(n.id, new Set());
    this.dirty = true;
    return n;
  }

  updateNode(id: string, patch: Partial<TemporalNode>): TemporalNode | null {
    const existing = this.nodes.get(id);
    if (!existing) return null;
    const updated: TemporalNode = {
      ...existing,
      ...patch,
      id,
      createdAt: existing.createdAt,
      updatedAt: Date.now(),
    };
    this.nodes.set(id, updated);
    this.dirty = true;
    return updated;
  }

  deleteNode(id: string): boolean {
    if (!this.nodes.has(id)) return false;
    this.nodes.delete(id);
    this.adjacency.delete(id);
    const toRemove: string[] = [];
    for (const [eid, edge] of this.edges) {
      if (edge.sourceId === id || edge.targetId === id) toRemove.push(eid);
    }
    for (const eid of toRemove) this.edges.delete(eid);
    this.dirty = true;
    return true;
  }

  getNode(id: string): TemporalNode | undefined {
    return this.nodes.get(id);
  }

  queryNodes(q: GraphQuery): TemporalNode[] {
    let results = Array.from(this.nodes.values());

    if (q.types?.length) {
      results = results.filter((n) => q.types!.includes(n.type));
    }
    if (q.tags?.length) {
      results = results.filter((n) => q.tags!.some((t) => n.tags.includes(t)));
    }
    if (q.timeRange) {
      results = results.filter((n) => {
        const start = n.startTime;
        const end = n.endTime ?? n.startTime;
        return start <= q.timeRange!.end && end >= q.timeRange!.start;
      });
    }
    if (q.before !== undefined) {
      results = results.filter((n) => n.startTime <= q.before!);
    }
    if (q.after !== undefined) {
      results = results.filter((n) => n.startTime >= q.after!);
    }

    results.sort((a, b) => a.startTime - b.startTime);

    if (q.offset) results = results.slice(q.offset);
    if (q.limit) results = results.slice(0, q.limit);

    return results;
  }

  // ─── Edge Operations ──────────────────────────────────────────────

  addEdge(edge: Omit<TemporalEdge, "createdAt">): TemporalEdge | null {
    if (this.edges.size >= this.maxEdges) return null;
    if (!this.nodes.has(edge.sourceId) || !this.nodes.has(edge.targetId)) return null;
    const e: TemporalEdge = { ...edge, createdAt: Date.now() };
    this.edges.set(e.id, e);
    const adj = this.adjacency.get(edge.sourceId);
    if (adj) adj.add(edge.targetId);
    const rev = this.adjacency.get(edge.targetId);
    if (rev) rev.add(edge.sourceId);
    this.dirty = true;
    return e;
  }

  deleteEdge(id: string): boolean {
    const edge = this.edges.get(id);
    if (!edge) return false;
    this.edges.delete(id);
    this.dirty = true;
    return true;
  }

  getEdges(nodeId: string, direction: "outgoing" | "incoming" | "both" = "both"): TemporalEdge[] {
    const all: TemporalEdge[] = [];
    for (const edge of this.edges.values()) {
      if (direction === "outgoing" && edge.sourceId === nodeId) all.push(edge);
      else if (direction === "incoming" && edge.targetId === nodeId) all.push(edge);
      else if (direction === "both" && (edge.sourceId === nodeId || edge.targetId === nodeId)) all.push(edge);
    }
    return all;
  }

  // ─── Path & Traversal ─────────────────────────────────────────────

  findPath(q: PathQuery): TemporalNode[] {
    const visited = new Set<string>();
    const queue: { id: string; path: TemporalNode[] }[] = [];
    const start = this.nodes.get(q.fromId);
    if (!start) return [];
    queue.push({ id: q.fromId, path: [start] });
    visited.add(q.fromId);

    const maxDepth = q.maxDepth ?? 10;
    let depth = 0;

    while (queue.length > 0 && depth < maxDepth) {
      const levelSize = queue.length;
      for (let i = 0; i < levelSize; i++) {
        const current = queue.shift()!;
        const neighbors = this._getNeighbors(current.id, q.edgeTypes);
        for (const nid of neighbors) {
          if (nid === q.toId) {
            const target = this.nodes.get(nid);
            if (target) return [...current.path, target];
          }
          if (!visited.has(nid)) {
            visited.add(nid);
            const node = this.nodes.get(nid);
            if (node) {
              queue.push({ id: nid, path: [...current.path, node] });
            }
          }
        }
      }
      depth++;
    }
    return [];
  }

  private _getNeighbors(nodeId: string, edgeTypes?: EdgeType[]): string[] {
    const adj = this.adjacency.get(nodeId);
    if (!adj) return [];
    const result: string[] = [];
    for (const nid of adj) {
      const connectingEdges = this._edgesBetween(nodeId, nid);
      if (!edgeTypes || connectingEdges.some((e) => edgeTypes.includes(e.type))) {
        result.push(nid);
      }
    }
    return result;
  }

  private _edgesBetween(a: string, b: string): TemporalEdge[] {
    const result: TemporalEdge[] = [];
    for (const edge of this.edges.values()) {
      if (
        (edge.sourceId === a && edge.targetId === b) ||
        (edge.sourceId === b && edge.targetId === a)
      ) {
        result.push(edge);
      }
    }
    return result;
  }

  // ─── Timeline Queries ─────────────────────────────────────────────

  getTimeline(from: number, to: number): TemporalNode[] {
    return this.queryNodes({ timeRange: { start: from, end: to }, limit: this.maxNodes });
  }

  getUpcoming(limit = 20): TemporalNode[] {
    const now = Date.now();
    return this.queryNodes({ after: now, limit });
  }

  getOverdue(): TemporalNode[] {
    const now = Date.now();
    const all = Array.from(this.nodes.values());
    return all
      .filter((n) => n.endTime !== undefined && n.endTime < now)
      .sort((a, b) => (a.endTime ?? a.startTime) - (b.endTime ?? b.startTime));
  }

  // ─── Import / Export ──────────────────────────────────────────────

  exportSnapshot(): StorageSnapshot {
    return {
      version: 1,
      exportedAt: Date.now(),
      nodes: Array.from(this.nodes.values()),
      edges: Array.from(this.edges.values()),
      habits: [],
      jobs: [],
    };
  }

  importSnapshot(snapshot: StorageSnapshot): void {
    this.nodes.clear();
    this.edges.clear();
    this.adjacency.clear();
    for (const n of snapshot.nodes) {
      this.nodes.set(n.id, n);
      this.adjacency.set(n.id, new Set());
    }
    for (const e of snapshot.edges) {
      this.edges.set(e.id, e);
      this.adjacency.get(e.sourceId)?.add(e.targetId);
      this.adjacency.get(e.targetId)?.add(e.sourceId);
    }
    this.dirty = true;
  }

  // ─── Stats ────────────────────────────────────────────────────────

  stats(): { nodeCount: number; edgeCount: number; byType: Record<NodeType, number> } {
    const byType: Record<string, number> = {};
    for (const n of this.nodes.values()) {
      byType[n.type] = (byType[n.type] ?? 0) + 1;
    }
    return {
      nodeCount: this.nodes.size,
      edgeCount: this.edges.size,
      byType: byType as Record<NodeType, number>,
    };
  }

  // ─── Internal ─────────────────────────────────────────────────────

  private _load(): void {
    try {
      if (!existsSync(this.storagePath)) return;
      const raw = readFileSync(this.storagePath, "utf-8");
      const data = JSON.parse(raw) as { nodes: [string, TemporalNode][]; edges: [string, TemporalEdge][] };
      for (const [id, n] of data.nodes) {
        this.nodes.set(id, n);
        this.adjacency.set(id, new Set());
      }
      for (const [id, e] of data.edges) {
        this.edges.set(id, e);
        this.adjacency.get(e.sourceId)?.add(e.targetId);
        this.adjacency.get(e.targetId)?.add(e.sourceId);
      }
    } catch {
      // Corrupt file — start fresh
    }
  }

  private _flush(): void {
    if (!this.dirty) return;
    try {
      const data = {
        nodes: Array.from(this.nodes.entries()),
        edges: Array.from(this.edges.entries()),
      };
      writeFileSync(this.storagePath, JSON.stringify(data), "utf-8");
      this.dirty = false;
    } catch {
      // Write failure — skip
    }
  }

  private _evictNodes(): void {
    const sorted = Array.from(this.nodes.values()).sort((a, b) => a.createdAt - b.createdAt);
    const toEvict = Math.ceil(this.maxNodes * 0.1);
    for (let i = 0; i < toEvict && i < sorted.length; i++) {
      this.deleteNode(sorted[i].id);
    }
  }

  destroy(): void {
    if (this.saveTimer) clearInterval(this.saveTimer);
    this._flush();
  }
}
