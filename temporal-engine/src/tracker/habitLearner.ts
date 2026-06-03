import type { TemporalNode, HabitPattern, TimeDistribution } from "../types";
import type { TemporalGraphStore } from "../graph/store";

interface ObservationWindow {
  hour: number;
  dayOfWeek: number;
  dayOfMonth: number;
  month: number;
}

export class HabitLearner {
  private habits: Map<string, HabitPattern> = new Map();
  private minObservations = 3;
  private patternConfidence: number;

  constructor(opts?: { minObservations?: number; patternConfidence?: number }) {
    this.minObservations = opts?.minObservations ?? 3;
    this.patternConfidence = opts?.patternConfidence ?? 0.7;
  }

  analyze(store: TemporalGraphStore): HabitPattern[] {
    const nodes = store.queryNodes({});
    const groups = this._groupByLabel(nodes);
    const discovered: HabitPattern[] = [];

    for (const [label, group] of groups) {
      if (group.length < this.minObservations) continue;
      const pattern = this._buildPattern(label, group);
      if (pattern && pattern.confidence >= this.patternConfidence) {
        this.habits.set(pattern.id, pattern);
        discovered.push(pattern);
      }
    }

    return discovered;
  }

  private _groupByLabel(nodes: TemporalNode[]): Map<string, TemporalNode[]> {
    const groups = new Map<string, TemporalNode[]>();
    for (const n of nodes) {
      const key = n.label.toLowerCase().trim();
      if (!key) continue;
      const arr = groups.get(key) ?? [];
      arr.push(n);
      groups.set(key, arr);
    }
    return groups;
  }

  private _buildPattern(label: string, nodes: TemporalNode[]): HabitPattern | null {
    const windows = nodes.map((n) => this._toObservationWindow(n));
    const timeDist = this._computeTimeDistribution(windows);
    const dayDist = this._computeDayDistribution(windows);
    const nodeId = nodes[0].id;
    const originalLabel = nodes[0].label;
    const firstObserved = Math.min(...nodes.map((n) => n.createdAt));
    const lastObserved = Math.max(...nodes.map((n) => n.updatedAt));

    const varianceRatio = timeDist.variance / (24 * 24);
    const frequencyScore = Math.min(nodes.length / 30, 1);
    const regularityScore = Math.max(0, 1 - varianceRatio);
    const confidence = Math.min(frequencyScore * 0.5 + regularityScore * 0.5, 1);

    if (confidence < this.patternConfidence) return null;

    return {
      id: `habit_${label.replace(/[^a-zA-Z0-9]/g, "_")}_${firstObserved}`,
      nodeId,
      label: originalLabel,
      frequency: nodes.length,
      timesObserved: nodes.length,
      timeDistribution: timeDist,
      dayDistribution: dayDist,
      confidence,
      lastObserved,
      firstObserved,
    };
  }

  private _toObservationWindow(node: TemporalNode): ObservationWindow {
    const d = new Date(node.startTime);
    return {
      hour: d.getHours() + d.getMinutes() / 60,
      dayOfWeek: d.getDay(),
      dayOfMonth: d.getDate(),
      month: d.getMonth(),
    };
  }

  private _computeTimeDistribution(windows: ObservationWindow[]): TimeDistribution {
    if (windows.length === 0) {
      return { meanHour: 12, variance: 6, peakWindow: { start: 9, end: 17 } };
    }
    const meanHour = windows.reduce((s, w) => s + w.hour, 0) / windows.length;
    const variance = windows.reduce((s, w) => s + (w.hour - meanHour) ** 2, 0) / windows.length;
    const peakWindow = this._findPeakWindow(windows);
    return { meanHour, variance, peakWindow };
  }

  private _computeDayDistribution(windows: ObservationWindow[]): number[] {
    const dist = new Array(7).fill(0);
    for (const w of windows) dist[w.dayOfWeek]++;
    const max = Math.max(...dist, 1);
    return dist.map((c) => c / max);
  }

  private _findPeakWindow(windows: ObservationWindow[]): { start: number; end: number } {
    const hourly = new Array(24).fill(0);
    for (const w of windows) {
      const h = Math.floor(w.hour);
      hourly[h]++;
    }
    let bestStart = 0;
    let bestCount = 0;
    for (let i = 0; i <= 20; i++) {
      const count = hourly[i] + hourly[i + 1] + hourly[i + 2] + hourly[i + 3];
      if (count > bestCount) {
        bestCount = count;
        bestStart = i;
      }
    }
    return { start: bestStart, end: bestStart + 4 };
  }

  getHabits(): HabitPattern[] {
    return Array.from(this.habits.values());
  }

  getHabit(label: string): HabitPattern | undefined {
    return Array.from(this.habits.values()).find(
      (h) => h.label.toLowerCase() === label.toLowerCase()
    );
  }

  clear(): void {
    this.habits.clear();
  }
}
