// ─── Temporal Node Types ────────────────────────────────────────────

export type NodeType =
  | "event"
  | "task"
  | "deadline"
  | "habit"
  | "milestone"
  | "routine"
  | "timeslot";

export type EdgeType =
  | "precedes"
  | "follows"
  | "overlaps"
  | "contains"
  | "during"
  | "depends_on"
  | "triggers"
  | "conflicts_with"
  | "part_of";

export interface TemporalNode {
  id: string;
  type: NodeType;
  label: string;
  description?: string;
  /** Unix epoch ms */
  startTime: number;
  /** Unix epoch ms; undefined = instantaneous or open-ended */
  endTime?: number;
  recurrence?: RecurrenceRule;
  metadata: Record<string, unknown>;
  tags: string[];
  confidence: number;
  createdAt: number;
  updatedAt: number;
}

export interface TemporalEdge {
  id: string;
  sourceId: string;
  targetId: string;
  type: EdgeType;
  weight: number;
  metadata: Record<string, unknown>;
  createdAt: number;
}

export interface RecurrenceRule {
  frequency: "daily" | "weekly" | "monthly" | "yearly" | "custom";
  interval: number;
  daysOfWeek?: number[];
  daysOfMonth?: number[];
  monthsOfYear?: number[];
  startDate?: string;
  endDate?: string;
  count?: number;
  cronExpression?: string;
}

// ─── Graph Query Types ──────────────────────────────────────────────

export interface GraphQuery {
  types?: NodeType[];
  tags?: string[];
  timeRange?: { start: number; end: number };
  before?: number;
  after?: number;
  limit?: number;
  offset?: number;
  includeEdges?: boolean;
}

export interface PathQuery {
  fromId: string;
  toId: string;
  maxDepth?: number;
  edgeTypes?: EdgeType[];
}

// ─── Prediction & Analysis Types ────────────────────────────────────

export interface PredictionResult {
  eventId: string;
  predictedStartTime: number;
  predictedEndTime?: number;
  confidence: number;
  probabilityDistribution: ProbabilityDistribution;
  factors: PredictionFactor[];
}

export interface ProbabilityDistribution {
  mean: number;
  variance: number;
  stdDev: number;
  p10: number;
  p50: number;
  p90: number;
}

export interface PredictionFactor {
  name: string;
  weight: number;
  impact: "positive" | "negative";
  description: string;
}

// ─── Habit / Pattern Types ──────────────────────────────────────────

export interface HabitPattern {
  id: string;
  nodeId: string;
  label: string;
  frequency: number;
  timesObserved: number;
  timeDistribution: TimeDistribution;
  dayDistribution: number[];
  confidence: number;
  lastObserved: number;
  firstObserved: number;
}

export interface TimeDistribution {
  meanHour: number;
  variance: number;
  peakWindow: { start: number; end: number };
}

// ─── Conflict & Impact Types ────────────────────────────────────────

export interface ScheduleConflict {
  id: string;
  type: "overlap" | "dependency_breach" | "resource_contention" | "deadline_risk";
  severity: "low" | "medium" | "high" | "critical";
  involvedNodeIds: string[];
  description: string;
  suggestion?: string;
  timeRange: { start: number; end: number };
}

export interface ImpactScore {
  nodeId: string;
  score: number;
  breakdown: Record<string, number>;
  affectedNodes: string[];
  rippleEffect: number;
}

// ─── Scheduler Types ────────────────────────────────────────────────

export type WorkerStatus = "idle" | "running" | "paused" | "error";
export type JobStatus = "active" | "paused" | "completed" | "failed";

export interface ScheduledJob {
  id: string;
  name: string;
  cronExpression: string;
  action: JobAction;
  status: JobStatus;
  lastRunAt?: number;
  nextRunAt: number;
  retryCount: number;
  maxRetries: number;
  metadata: Record<string, unknown>;
}

export type JobAction =
  | { type: "reminder"; nodeId: string; message: string }
  | { type: "reanalyze"; scope: "habits" | "conflicts" | "predictions" | "all" }
  | { type: "notification"; channel: string; payload: Record<string, unknown> }
  | { type: "webhook"; url: string; body: string }
  | { type: "gc"; maxAge: number };

// ─── Storage Types ──────────────────────────────────────────────────

export interface StorageSnapshot {
  version: number;
  exportedAt: number;
  nodes: TemporalNode[];
  edges: TemporalEdge[];
  habits: HabitPattern[];
  jobs: ScheduledJob[];
}

// ─── Event Bus Types ────────────────────────────────────────────────

export type TemporalEventType =
  | "node:created"
  | "node:updated"
  | "node:deleted"
  | "edge:created"
  | "edge:deleted"
  | "conflict:detected"
  | "conflict:resolved"
  | "habit:discovered"
  | "habit:updated"
  | "prediction:ready"
  | "job:triggered"
  | "job:completed"
  | "job:failed"
  | "worker:tick";

export interface TemporalEvent {
  type: TemporalEventType;
  timestamp: number;
  payload: unknown;
}

// ─── Integration Types ──────────────────────────────────────────────

export interface EngineConfig {
  storagePath?: string;
  autoSaveIntervalMs?: number;
  maxNodes?: number;
  maxEdges?: number;
  predictionHorizonDays?: number;
  confidences?: {
    patternDetection: number;
    prediction: number;
    conflictDetection: number;
  };
}
