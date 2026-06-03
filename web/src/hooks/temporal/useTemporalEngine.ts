import { useState, useEffect, useCallback, useRef } from "react";
import type {
  TemporalNode,
  TemporalEdge,
  ScheduleConflict,
  PredictionResult,
  HabitPattern,
  ImpactScore,
  GraphQuery,
  StorageSnapshot,
} from "./types";

interface RpcResponse<T> {
  result?: T;
  error?: { code: number; message: string };
}

interface PendingRequest {
  resolve: (v: unknown) => void;
  reject: (e: Error) => void;
}

/**
 * Hook that connects to the Temporal Engine via its JSON-RPC bridge.
 *
 * The bridge runs as a subprocess managed by the Python backend.
 * This hook communicates through the backend's proxy endpoint at
 * /api/temporal/rpc (WebSocket or POST).
 */
export function useTemporalEngine(baseUrl = "/api/temporal") {
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const pendingRef = useRef<Map<number | string, PendingRequest>>(new Map());
  const idCounterRef = useRef(0);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(`${baseUrl.replace(/^http/, "ws")}/ws`);
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);
      ws.onclose = () => setConnected(false);
      ws.onerror = () => setError(new Error("WebSocket connection failed"));

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.id != null) {
            const pending = pendingRef.current.get(msg.id);
            if (pending) {
              pendingRef.current.delete(msg.id);
              if (msg.error) {
                pending.reject(new Error(msg.error.message));
              } else {
                pending.resolve(msg.result);
              }
            }
          }
        } catch {
          // Ignore malformed messages
        }
      };
    } catch {
      setError(new Error("Failed to create WebSocket connection"));
    }
  }, [baseUrl]);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setConnected(false);
  }, []);

  const call = useCallback(
    async <T>(method: string, params: Record<string, unknown> = {}): Promise<T> => {
      return new Promise((resolve, reject) => {
        idCounterRef.current++;
        const id = idCounterRef.current;

        pendingRef.current.set(id, { resolve: resolve as (v: unknown) => void, reject });

        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(
            JSON.stringify({ jsonrpc: "2.0", id, method, params })
          );
        } else {
          // Fallback to HTTP POST
          fetch(`${baseUrl}/rpc`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ jsonrpc: "2.0", id, method, params }),
          })
            .then((r) => r.json())
            .then((msg: RpcResponse<T>) => {
              if (msg.error) reject(new Error(msg.error.message));
              else resolve(msg.result as T);
            })
            .catch(reject);
        }
      });
    },
    [baseUrl]
  );

  // ─── Node Operations ─────────────────────────────────────────────

  const addNode = useCallback(
    (node: Omit<TemporalNode, "createdAt" | "updatedAt">) =>
      call<TemporalNode>("add_node", node as unknown as Record<string, unknown>),
    [call]
  );

  const updateNode = useCallback(
    (id: string, patch: Partial<TemporalNode>) =>
      call<TemporalNode>("update_node", { id, patch }),
    [call]
  );

  const deleteNode = useCallback(
    (id: string) => call<boolean>("delete_node", { id }),
    [call]
  );

  const getNode = useCallback(
    (id: string) => call<TemporalNode | null>("get_node", { id }),
    [call]
  );

  const queryNodes = useCallback(
    (q: GraphQuery) => call<TemporalNode[]>("query_nodes", q as unknown as Record<string, unknown>),
    [call]
  );

  const getTimeline = useCallback(
    (from: number, to: number) => call<TemporalNode[]>("get_timeline", { from, to }),
    [call]
  );

  const getUpcoming = useCallback(
    (limit = 20) => call<TemporalNode[]>("get_upcoming", { limit }),
    [call]
  );

  const getOverdue = useCallback(
    () => call<TemporalNode[]>("get_overdue"),
    [call]
  );

  // ─── Edge Operations ─────────────────────────────────────────────

  const addEdge = useCallback(
    (edge: Omit<TemporalEdge, "createdAt">) =>
      call<TemporalEdge | null>("add_edge", edge as unknown as Record<string, unknown>),
    [call]
  );

  const deleteEdge = useCallback(
    (id: string) => call<boolean>("delete_edge", { id }),
    [call]
  );

  const getEdges = useCallback(
    (nodeId: string, direction: "outgoing" | "incoming" | "both" = "both") =>
      call<TemporalEdge[]>("get_edges", { nodeId, direction }),
    [call]
  );

  // ─── Habits ──────────────────────────────────────────────────────

  const analyzeHabits = useCallback(
    () => call<HabitPattern[]>("analyze_habits"),
    [call]
  );

  const getHabits = useCallback(
    () => call<HabitPattern[]>("get_habits"),
    [call]
  );

  const getHabit = useCallback(
    (label: string) => call<HabitPattern | null>("get_habit", { label }),
    [call]
  );

  // ─── Predictions ─────────────────────────────────────────────────

  const predictCompletion = useCallback(
    (nodeId: string) => call<PredictionResult>("predict_completion", { nodeId }),
    [call]
  );

  const predictOptimalWindow = useCallback(
    (nodeId: string) =>
      call<{ windowStart: number; windowEnd: number; score: number }>(
        "predict_optimal_window",
        { nodeId }
      ),
    [call]
  );

  const predictFutureLoad = useCallback(
    () =>
      call<
        { date: string; taskCount: number; estimatedHours: number; confidence: number }[]
      >("predict_future_load"),
    [call]
  );

  // ─── Conflicts ───────────────────────────────────────────────────

  const detectConflicts = useCallback(
    () => call<ScheduleConflict[]>("detect_conflicts"),
    [call]
  );

  const scoreImpact = useCallback(
    (nodeId: string) => call<ImpactScore>("score_impact", { nodeId }),
    [call]
  );

  const scoreAllImpact = useCallback(
    () => call<ImpactScore[]>("score_all_impact"),
    [call]
  );

  // ─── Import / Export ─────────────────────────────────────────────

  const exportSnapshot = useCallback(
    () => call<StorageSnapshot>("export_snapshot"),
    [call]
  );

  const importSnapshot = useCallback(
    (snapshot: StorageSnapshot) => call<void>("import_snapshot", { snapshot }),
    [call]
  );

  const stats = useCallback(
    () =>
      call<{ nodeCount: number; edgeCount: number; byType: Record<string, number> }>(
        "stats"
      ),
    [call]
  );

  // ─── Scheduler ───────────────────────────────────────────────────

  const listJobs = useCallback(
    () => call<import("../../../../temporal-engine/src/types").ScheduledJob[]>("list_jobs"),
    [call]
  );

  const addJob = useCallback(
    (job: import("../../../../temporal-engine/src/types").ScheduledJob) =>
      call<void>("add_job", job as unknown as Record<string, unknown>),
    [call]
  );

  const removeJob = useCallback(
    (id: string) => call<boolean>("remove_job", { id }),
    [call]
  );

  const pauseJob = useCallback(
    (id: string) => call<boolean>("pause_job", { id }),
    [call]
  );

  const resumeJob = useCallback(
    (id: string) => call<boolean>("resume_job", { id }),
    [call]
  );

  const workerStatus = useCallback(
    () => call<string>("worker_status"),
    [call]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => disconnect();
  }, [disconnect]);

  return {
    connected,
    loading,
    error,
    connect,
    disconnect,

    // Nodes
    addNode,
    updateNode,
    deleteNode,
    getNode,
    queryNodes,
    getTimeline,
    getUpcoming,
    getOverdue,

    // Edges
    addEdge,
    deleteEdge,
    getEdges,

    // Habits
    analyzeHabits,
    getHabits,
    getHabit,

    // Predictions
    predictCompletion,
    predictOptimalWindow,
    predictFutureLoad,

    // Conflicts
    detectConflicts,
    scoreImpact,
    scoreAllImpact,

    // Import / Export
    exportSnapshot,
    importSnapshot,
    stats,

    // Scheduler
    listJobs,
    addJob,
    removeJob,
    pauseJob,
    resumeJob,
    workerStatus,
  };
}
