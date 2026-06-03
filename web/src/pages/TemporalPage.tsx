import { useState, useEffect, useCallback } from "react";
import { useTemporalEngine } from "@/hooks/temporal";
import type {
  TemporalNode,
  ScheduleConflict,
  HabitPattern,
  ImpactScore,
} from "@/hooks/temporal/types";

type Tab = "timeline" | "conflicts" | "habits" | "predictions" | "impact";

export default function TemporalPage() {
  const engine = useTemporalEngine();
  const [activeTab, setActiveTab] = useState<Tab>("timeline");
  const [nodes, setNodes] = useState<TemporalNode[]>([]);
  const [conflicts, setConflicts] = useState<ScheduleConflict[]>([]);
  const [habits, setHabits] = useState<HabitPattern[]>([]);
  const [impacts, setImpacts] = useState<ImpactScore[]>([]);
  const [loadForecast, setLoadForecast] = useState<
    { date: string; taskCount: number; estimatedHours: number; confidence: number }[]
  >([]);
  const [status, setStatus] = useState<string>("Disconnected");

  const refresh = useCallback(async () => {
    try {
      setStatus("Loading...");
      engine.connect();
      const [n, c, h, i, l] = await Promise.all([
        engine.queryNodes({ limit: 100 }),
        engine.detectConflicts(),
        engine.analyzeHabits(),
        engine.scoreAllImpact(),
        engine.predictFutureLoad(),
      ]);
      setNodes(n);
      setConflicts(c);
      setHabits(h);
      setImpacts(i);
      setLoadForecast(l);
      setStatus("Connected");
    } catch {
      setStatus("Error loading data");
    }
  }, [engine]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const tabs: { key: Tab; label: string }[] = [
    { key: "timeline", label: "Timeline" },
    { key: "conflicts", label: `Conflicts (${conflicts.length})` },
    { key: "habits", label: `Habits (${habits.length})` },
    { key: "predictions", label: "Forecast" },
    { key: "impact", label: "Impact" },
  ];

  return (
    <div className="p-4 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Temporal Intelligence</h1>
        <div className="flex items-center gap-2 text-sm">
          <span
            className={`w-2 h-2 rounded-full ${
              status === "Connected"
                ? "bg-green-500"
                : status === "Loading..."
                  ? "bg-yellow-500"
                  : "bg-red-500"
            }`}
          />
          <span className="text-muted-foreground">{status}</span>
          <button
            onClick={refresh}
            className="px-3 py-1 text-xs border rounded hover:bg-accent"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-5 gap-3 mb-4">
        <StatCard label="Nodes" value={nodes.length} />
        <StatCard
          label="Conflicts"
          value={conflicts.length}
          color={conflicts.length > 0 ? "text-red-500" : undefined}
        />
        <StatCard label="Habits" value={habits.length} />
        <StatCard label="Overdue" value={nodes.filter((n) => n.endTime && n.endTime < Date.now()).length} />
        <StatCard label="Upcoming" value={nodes.filter((n) => n.startTime > Date.now()).length} />
      </div>

      {/* Tab Bar */}
      <div className="flex gap-1 border-b mb-4">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === t.key
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="space-y-2">
        {activeTab === "timeline" && <TimelineTab nodes={nodes} />}
        {activeTab === "conflicts" && <ConflictsTab conflicts={conflicts} />}
        {activeTab === "habits" && <HabitsTab habits={habits} />}
        {activeTab === "predictions" && <ForecastTab forecast={loadForecast} />}
        {activeTab === "impact" && <ImpactTab impacts={impacts} />}
      </div>
    </div>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────

function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color?: string;
}) {
  return (
    <div className="border rounded p-3 text-center">
      <div className={`text-2xl font-bold ${color ?? ""}`}>{value}</div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </div>
  );
}

function TimelineTab({ nodes }: { nodes: TemporalNode[] }) {
  const sorted = [...nodes].sort((a, b) => a.startTime - b.startTime);
  const now = Date.now();

  return (
    <div className="space-y-1">
      {sorted.length === 0 && (
        <p className="text-muted-foreground text-sm p-4 text-center">
          No temporal nodes yet. Add events or tasks to see them here.
        </p>
      )}
      {sorted.map((n) => (
        <div
          key={n.id}
          className={`flex items-center gap-3 p-3 border rounded text-sm ${
            n.endTime && n.endTime < now
              ? "opacity-50"
              : ""
          }`}
        >
          <span className={`w-2 h-2 rounded-full ${
            n.type === "deadline" ? "bg-red-500" :
            n.type === "task" ? "bg-blue-500" :
            n.type === "event" ? "bg-green-500" :
            n.type === "milestone" ? "bg-yellow-500" :
            "bg-gray-500"
          }`} />
          <span className="font-medium w-20 text-xs text-muted-foreground">
            {n.type}
          </span>
          <span className="flex-1">{n.label}</span>
          <span className="text-xs text-muted-foreground">
            {new Date(n.startTime).toLocaleDateString()}{" "}
            {new Date(n.startTime).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </span>
          {n.endTime && (
            <span className="text-xs text-muted-foreground">
              {((n.endTime - n.startTime) / (1000 * 60)).toFixed(0)}m
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

function ConflictsTab({ conflicts }: { conflicts: ScheduleConflict[] }) {
  const bySeverity = (s: string) =>
    conflicts.filter((c) => c.severity === s);

  return (
    <div className="space-y-2">
      {conflicts.length === 0 && (
        <p className="text-muted-foreground text-sm p-4 text-center">
          No conflicts detected. Your schedule looks clear.
        </p>
      )}
      {(["critical", "high", "medium", "low"] as const).map((sev) => {
        const items = bySeverity(sev);
        if (items.length === 0) return null;
        return (
          <div key={sev}>
            <h3 className="text-sm font-medium capitalize mb-1">
              {sev} ({items.length})
            </h3>
            {items.map((c) => (
              <div
                key={c.id}
                className={`p-3 border rounded mb-1 text-sm ${
                  sev === "critical"
                    ? "border-red-500 bg-red-50 dark:bg-red-950"
                    : sev === "high"
                      ? "border-orange-400 bg-orange-50 dark:bg-orange-950"
                      : ""
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="font-medium">{c.type.replace(/_/g, " ")}</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded ${
                    sev === "critical" ? "bg-red-200 text-red-800" :
                    sev === "high" ? "bg-orange-200 text-orange-800" :
                    "bg-gray-200 text-gray-800"
                  }`}>
                    {sev}
                  </span>
                </div>
                <p className="mt-1">{c.description}</p>
                {c.suggestion && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    Suggestion: {c.suggestion}
                  </p>
                )}
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}

function HabitsTab({ habits }: { habits: HabitPattern[] }) {
  const sorted = [...habits].sort((a, b) => b.confidence - a.confidence);

  return (
    <div className="space-y-2">
      {sorted.length === 0 && (
        <p className="text-muted-foreground text-sm p-4 text-center">
          Not enough data to detect patterns. Continue using Sara and habits will appear here.
        </p>
      )}
      {sorted.map((h) => (
        <div key={h.id} className="p-3 border rounded text-sm">
          <div className="flex items-center justify-between mb-1">
            <span className="font-medium">{h.label}</span>
            <span className="text-xs text-muted-foreground">
              {(h.confidence * 100).toFixed(0)}% confidence
            </span>
          </div>
          <div className="flex gap-4 text-xs text-muted-foreground">
            <span>Observed {h.timesObserved}x</span>
            <span>Peak: {h.timeDistribution.peakWindow.start}:00–{h.timeDistribution.peakWindow.end}:00</span>
            <span>Mean: {h.timeDistribution.meanHour.toFixed(1)}:00</span>
          </div>
          <div className="flex gap-0.5 mt-1">
            {h.dayDistribution.map((d, i) => (
              <div
                key={i}
                className="flex-1 h-1.5 rounded"
                style={{
                  backgroundColor: `hsl(${220 - d * 200}, 70%, ${50 + d * 30}%)`,
                }}
                title={`Day ${i}: ${(d * 100).toFixed(0)}%`}
              />
            ))}
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            Sun Mon Tue Wed Thu Fri Sat
          </div>
        </div>
      ))}
    </div>
  );
}

function ForecastTab({
  forecast,
}: {
  forecast: { date: string; taskCount: number; estimatedHours: number; confidence: number }[];
}) {
  const maxHours = Math.max(...forecast.map((f) => f.estimatedHours), 1);

  return (
    <div className="space-y-1">
      <p className="text-xs text-muted-foreground mb-2">
        Predicted workload for the next {forecast.length} days
      </p>
      {forecast.map((f) => (
        <div key={f.date} className="flex items-center gap-3 text-sm">
          <span className="w-24 text-xs text-muted-foreground">
            {new Date(f.date).toLocaleDateString(undefined, {
              weekday: "short",
              month: "short",
              day: "numeric",
            })}
          </span>
          <div className="flex-1 h-5 bg-secondary rounded overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded transition-all flex items-center px-1"
              style={{ width: `${(f.estimatedHours / maxHours) * 100}%` }}
            >
              {f.estimatedHours > maxHours * 0.3 && (
                <span className="text-[10px] text-white font-medium">
                  {f.estimatedHours}h
                </span>
              )}
            </div>
          </div>
          <span className="w-8 text-xs text-right text-muted-foreground">
            {f.taskCount}tasks
          </span>
          <span className="w-12 text-xs text-right text-muted-foreground">
            {(f.confidence * 100).toFixed(0)}%
          </span>
        </div>
      ))}
    </div>
  );
}

function ImpactTab({ impacts }: { impacts: ImpactScore[] }) {
  const sorted = [...impacts].sort((a, b) => b.score - a.score);

  return (
    <div className="space-y-2">
      {sorted.length === 0 && (
        <p className="text-muted-foreground text-sm p-4 text-center">
          Add nodes with dependencies to see impact scores.
        </p>
      )}
      {sorted.map((imp) => (
        <div key={imp.nodeId} className="p-3 border rounded text-sm">
          <div className="flex items-center justify-between mb-1">
            <span className="font-medium">Node {imp.nodeId.slice(0, 8)}</span>
            <span className="text-xs font-bold">
              Impact: {(imp.score * 100).toFixed(0)}%
            </span>
          </div>
          <div className="w-full h-1.5 bg-secondary rounded overflow-hidden mb-2">
            <div
              className="h-full bg-orange-500 rounded transition-all"
              style={{ width: `${imp.score * 100}%` }}
            />
          </div>
          <div className="grid grid-cols-4 gap-2 text-xs text-muted-foreground mb-1">
            {Object.entries(imp.breakdown).map(([k, v]) => (
              <div key={k}>
                <span className="block">{k.replace(/_/g, " ")}</span>
                <span className="font-medium text-foreground">
                  {(v * 100).toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
          <div className="text-xs text-muted-foreground">
            Affects {imp.affectedNodes.length} node
            {imp.affectedNodes.length !== 1 ? "s" : ""} downstream
            (ripple: {imp.rippleEffect})
          </div>
        </div>
      ))}
    </div>
  );
}
