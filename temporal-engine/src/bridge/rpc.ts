/**
 * JSON-RPC bridge for Python backend integration.
 *
 * The Python backend spawns this module as a long-lived subprocess or
 * imports it via a Node.js child process. Communication happens over
 * stdin/stdout JSON-RPC 2.0 messages.
 *
 * Protocol:
 *   → {"jsonrpc":"2.0","id":1,"method":"query_nodes","params":{...}}
 *   ← {"jsonrpc":"2.0","id":1,"result":{...}}
 *   ← {"jsonrpc":"2.0","id":null,"method":"event","params":{...}}  (push)
 */

import { TemporalGraphStore } from "../graph/store";
import { HabitLearner } from "../tracker/habitLearner";
import { PredictiveScheduler } from "../predictor/scheduler";
import { ConflictDetector } from "../analyzer/conflictDetector";
import { BackgroundWorker } from "../scheduler/worker";
import type { EngineConfig, TemporalNode } from "../types";

interface RpcRequest {
  jsonrpc: "2.0";
  id: number | string | null;
  method: string;
  params: Record<string, unknown>;
}

interface RpcResponse {
  jsonrpc: "2.0";
  id: number | string | null;
  result?: unknown;
  error?: { code: number; message: string; data?: unknown };
}

type MethodHandler = (params: Record<string, unknown>) => Promise<unknown> | unknown;

export class TemporalEngineBridge {
  private store: TemporalGraphStore;
  private habits: HabitLearner;
  private predictor: PredictiveScheduler;
  private conflictDetector: ConflictDetector;
  private worker: BackgroundWorker;
  private handlers: Map<string, MethodHandler> = new Map();
  private stdin: NodeJS.ReadStream;
  private stdout: NodeJS.WriteStream;
  private buffer = "";
  private running = false;

  constructor(config: EngineConfig = {}) {
    this.store = new TemporalGraphStore({
      storagePath: config.storagePath,
      autoSaveIntervalMs: config.autoSaveIntervalMs,
      maxNodes: config.maxNodes,
      maxEdges: config.maxEdges,
    });
    this.habits = new HabitLearner({
      patternConfidence: config.confidences?.patternDetection,
    });
    this.predictor = new PredictiveScheduler({
      horizonDays: config.predictionHorizonDays,
    });
    this.conflictDetector = new ConflictDetector();
    this.worker = new BackgroundWorker({ tickIntervalMs: 60_000 });
    this.stdin = process.stdin;
    this.stdout = process.stdout;

    this._registerHandlers();

    this.worker.setTickHandler(async (jobs) => {
      for (const job of jobs) {
        if (job.action.type === "reanalyze") {
          switch (job.action.scope) {
            case "habits":
              this.habits.analyze(this.store);
              break;
            case "conflicts":
              this.conflictDetector.detectAll(this.store);
              break;
            case "all":
              this.habits.analyze(this.store);
              this.conflictDetector.detectAll(this.store);
              break;
          }
        }
      }
    });
  }

  start(): void {
    if (this.running) return;
    this.running = true;
    this.worker.start();
    this._readLoop();
  }

  stop(): void {
    this.running = false;
    this.worker.stop();
    this.store.destroy();
  }

  private _registerHandlers(): void {
    // Graph
    this.handlers.set("add_node", (p) => this.store.addNode(p as unknown as Omit<TemporalNode, "createdAt" | "updatedAt">));
    this.handlers.set("update_node", (p) => this.store.updateNode(p.id as string, p.patch as Partial<TemporalNode>));
    this.handlers.set("delete_node", (p) => this.store.deleteNode(p.id as string));
    this.handlers.set("get_node", (p) => this.store.getNode(p.id as string));
    this.handlers.set("query_nodes", (p) => this.store.queryNodes(p as Parameters<typeof this.store.queryNodes>[0]));
    this.handlers.set("add_edge", (p) => this.store.addEdge(p as Parameters<typeof this.store.addEdge>[0]));
    this.handlers.set("delete_edge", (p) => this.store.deleteEdge(p.id as string));
    this.handlers.set("get_edges", (p) => this.store.getEdges(p.nodeId as string, p.direction as "outgoing" | "incoming" | "both"));
    this.handlers.set("get_timeline", (p) => this.store.getTimeline(p.from as number, p.to as number));
    this.handlers.set("get_upcoming", (p) => this.store.getUpcoming(p.limit as number));
    this.handlers.set("get_overdue", () => this.store.getOverdue());
    this.handlers.set("export_snapshot", () => this.store.exportSnapshot());
    this.handlers.set("import_snapshot", (p) => this.store.importSnapshot(p.snapshot as Parameters<typeof this.store.importSnapshot>[0]));
    this.handlers.set("stats", () => this.store.stats());

    // Habits
    this.handlers.set("analyze_habits", () => this.habits.analyze(this.store));
    this.handlers.set("get_habits", () => this.habits.getHabits());
    this.handlers.set("get_habit", (p) => this.habits.getHabit(p.label as string));

    // Predictions
    this.handlers.set("predict_completion", (p) => {
      const node = this.store.getNode(p.nodeId as string);
      if (!node) throw new Error(`Node not found: ${p.nodeId}`);
      return this.predictor.predictCompletion(node, this.store, this.habits);
    });
    this.handlers.set("predict_optimal_window", (p) => {
      const node = this.store.getNode(p.nodeId as string);
      if (!node) throw new Error(`Node not found: ${p.nodeId}`);
      return this.predictor.predictOptimalWindow(node, this.habits);
    });
    this.handlers.set("predict_future_load", () => this.predictor.predictFutureLoad(this.store));

    // Conflicts
    this.handlers.set("detect_conflicts", () => this.conflictDetector.detectAll(this.store));
    this.handlers.set("detect_overlaps", () => this.conflictDetector.detectOverlaps(this.store));
    this.handlers.set("detect_deadline_risks", () => this.conflictDetector.detectDeadlineRisks(this.store));
    this.handlers.set("detect_dependency_breaches", () => this.conflictDetector.detectDependencyBreaches(this.store));
    this.handlers.set("score_impact", (p) => this.conflictDetector.scoreFutureImpact(p.nodeId as string, this.store));
    this.handlers.set("score_all_impact", () => this.conflictDetector.scoreAllFutureImpact(this.store));

    // Scheduler
    this.handlers.set("list_jobs", () => this.worker.listJobs());
    this.handlers.set("add_job", (p) => this.worker.addJob(p as unknown as Parameters<typeof this.worker.addJob>[0]));
    this.handlers.set("remove_job", (p) => this.worker.removeJob(p.id as string));
    this.handlers.set("pause_job", (p) => this.worker.pauseJob(p.id as string));
    this.handlers.set("resume_job", (p) => this.worker.resumeJob(p.id as string));
    this.handlers.set("worker_status", () => this.worker.getStatus());
    this.handlers.set("worker_start", () => this.worker.start());
    this.handlers.set("worker_stop", () => this.worker.stop());

    // Lifecycle
    this.handlers.set("ping", () => "pong");
    this.handlers.set("shutdown", () => { this.stop(); return "ok"; });
  }

  private _readLoop(): void {
    this.stdin.setEncoding("utf-8");
    this.stdin.on("data", (chunk: string) => {
      this.buffer += chunk;
      this._processBuffer();
    });
    this.stdin.on("end", () => this.stop());
  }

  private _processBuffer(): void {
    const lines = this.buffer.split("\n");
    this.buffer = lines.pop() ?? "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        const req = JSON.parse(trimmed) as RpcRequest;
        this._handleRequest(req).catch((err) => {
          this._sendResponse(req.id, undefined, err);
        });
      } catch {
        this._sendResponse(null, undefined, new Error("Parse error"));
      }
    }
  }

  private async _handleRequest(req: RpcRequest): Promise<void> {
    if (req.jsonrpc !== "2.0") {
      return this._sendResponse(req.id, undefined, new Error("Invalid JSON-RPC version"));
    }

    const handler = this.handlers.get(req.method);
    if (!handler) {
      return this._sendResponse(req.id, undefined, new Error(`Method not found: ${req.method}`));
    }

    try {
      const result = await handler(req.params ?? {});
      this._sendResponse(req.id, result);
    } catch (err) {
      this._sendResponse(req.id, undefined, err instanceof Error ? err : new Error(String(err)));
    }
  }

  private _sendResponse(id: number | string | null, result?: unknown, error?: Error): void {
    const res: RpcResponse = { jsonrpc: "2.0", id };
    if (error) {
      res.error = { code: -1, message: error.message };
    } else {
      res.result = result;
    }
    this.stdout.write(JSON.stringify(res) + "\n");
  }
}
