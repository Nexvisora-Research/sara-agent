import type {
  TemporalNode,
  PredictionResult,
  ProbabilityDistribution,
  PredictionFactor,
} from "../types";
import type { TemporalGraphStore } from "../graph/store";
import type { HabitLearner } from "../tracker/habitLearner";

export class PredictiveScheduler {
  private horizonDays: number;

  constructor(opts?: { horizonDays?: number }) {
    this.horizonDays = opts?.horizonDays ?? 30;
  }

  predictCompletion(node: TemporalNode, store: TemporalGraphStore, habits?: HabitLearner): PredictionResult {
    const historical = this._findSimilarCompleted(node, store);
    const dist = this._estimateDistribution(historical, node);
    const factors = this._computeFactors(node, store, habits);

    const confidence = this._computeConfidence(dist, factors);

    return {
      eventId: node.id,
      predictedStartTime: node.startTime + dist.mean * 60 * 60 * 1000,
      predictedEndTime: node.endTime
        ? node.endTime + dist.mean * 60 * 60 * 1000
        : undefined,
      confidence,
      probabilityDistribution: dist,
      factors,
    };
  }

  predictOptimalWindow(node: TemporalNode, habits?: HabitLearner): {
    windowStart: number;
    windowEnd: number;
    score: number;
  } {
    const now = Date.now();
    const nodeDuration = node.endTime ? node.endTime - node.startTime : 60 * 60 * 1000;

    if (!habits) {
      return {
        windowStart: now,
        windowEnd: now + nodeDuration,
        score: 0.5,
      };
    }

    const userHabits = habits.getHabits();
    if (userHabits.length === 0) {
      return {
        windowStart: now,
        windowEnd: now + nodeDuration,
        score: 0.5,
      };
    }

    let bestScore = -Infinity;
    let bestWindow = { windowStart: now, windowEnd: now + nodeDuration, score: 0 };

    for (let dayOffset = 0; dayOffset < this.horizonDays; dayOffset++) {
      for (let hour = 0; hour < 24; hour++) {
        const candidateStart = new Date(now);
        candidateStart.setDate(candidateStart.getDate() + dayOffset);
        candidateStart.setHours(hour, 0, 0, 0);
        const candidateEnd = candidateStart.getTime() + nodeDuration;

        if (candidateEnd < now) continue;

        let score = 0;
        for (const h of userHabits) {
          const hourDist = Math.abs(h.timeDistribution.meanHour - hour);
          const dayWeight = h.dayDistribution[candidateStart.getDay()] ?? 0;
          const hourScore = Math.max(0, 1 - hourDist / 12);
          score += hourScore * dayWeight * h.confidence;
        }

        const avgScore = userHabits.length > 0 ? score / userHabits.length : 0;
        if (avgScore > bestScore) {
          bestScore = avgScore;
          bestWindow = {
            windowStart: candidateStart.getTime(),
            windowEnd: candidateEnd,
            score: avgScore,
          };
        }
      }
    }

    return bestWindow;
  }

  predictFutureLoad(store: TemporalGraphStore): {
    date: string;
    taskCount: number;
    estimatedHours: number;
    confidence: number;
  }[] {
    const now = Date.now();
    const results: { date: string; taskCount: number; estimatedHours: number; confidence: number }[] = [];

    for (let d = 0; d < this.horizonDays; d++) {
      const dayStart = new Date(now);
      dayStart.setDate(dayStart.getDate() + d);
      dayStart.setHours(0, 0, 0, 0);
      const dayEnd = new Date(dayStart);
      dayEnd.setHours(23, 59, 59, 999);

      const dayNodes = store.queryNodes({
        timeRange: { start: dayStart.getTime(), end: dayEnd.getTime() },
      });

      const tasks = dayNodes.filter((n) => n.type === "task");
      const totalHours = tasks.reduce((sum, t) => {
        if (t.endTime) return sum + (t.endTime - t.startTime) / (1000 * 60 * 60);
        return sum + 1;
      }, 0);

      results.push({
        date: dayStart.toISOString().slice(0, 10),
        taskCount: tasks.length,
        estimatedHours: Math.round(totalHours * 10) / 10,
        confidence: tasks.length > 0 ? Math.min(0.5 + tasks.length * 0.05, 0.95) : 0.1,
      });
    }

    return results;
  }

  private _findSimilarCompleted(node: TemporalNode, store: TemporalGraphStore): TemporalNode[] {
    const all = store.queryNodes({});
    const now = Date.now();
    return all.filter(
      (n) =>
        n.id !== node.id &&
        n.type === node.type &&
        n.label.toLowerCase().includes(node.label.toLowerCase().slice(0, 5)) &&
        n.endTime !== undefined &&
        n.endTime < now
    );
  }

  private _estimateDistribution(historical: TemporalNode[], node: TemporalNode): ProbabilityDistribution {
    const defaultDuration = node.endTime
      ? (node.endTime - node.startTime) / (1000 * 60 * 60)
      : 1;

    if (historical.length < 2) {
      return {
        mean: defaultDuration,
        variance: defaultDuration * 0.5,
        stdDev: Math.sqrt(defaultDuration * 0.5),
        p10: defaultDuration * 0.5,
        p50: defaultDuration,
        p90: defaultDuration * 1.5,
      };
    }

    const durations = historical
      .filter((n) => n.endTime !== undefined)
      .map((n) => (n.endTime! - n.startTime) / (1000 * 60 * 60));

    const mean = durations.reduce((s, d) => s + d, 0) / durations.length;
    const variance = durations.reduce((s, d) => s + (d - mean) ** 2, 0) / durations.length;
    const stdDev = Math.sqrt(variance);
    const sorted = [...durations].sort((a, b) => a - b);

    const p10 = sorted[Math.floor(sorted.length * 0.1)] ?? mean * 0.5;
    const p50 = sorted[Math.floor(sorted.length * 0.5)] ?? mean;
    const p90 = sorted[Math.floor(sorted.length * 0.9)] ?? mean * 1.5;

    return { mean, variance, stdDev, p10, p50, p90 };
  }

  private _computeFactors(
    node: TemporalNode,
    store: TemporalGraphStore,
    habits?: HabitLearner
  ): PredictionFactor[] {
    const factors: PredictionFactor[] = [];

    const dependencies = store.getEdges(node.id, "incoming")
      .filter((e) => e.type === "depends_on");
    factors.push({
      name: "dependency_count",
      weight: 0.2,
      impact: dependencies.length > 2 ? "negative" : "positive",
      description: `${dependencies.length} blocking dependencies`,
    });

    if (node.endTime) {
      const durationHours = (node.endTime - node.startTime) / (1000 * 60 * 60);
      factors.push({
        name: "duration",
        weight: 0.15,
        impact: durationHours > 4 ? "negative" : "positive",
        description: `${durationHours.toFixed(1)}h estimated duration`,
      });
    }

    if (habits) {
      const match = habits.getHabit(node.label);
      if (match) {
        factors.push({
          name: "habit_match",
          weight: 0.25,
          impact: "positive",
          description: `Observed ${match.timesObserved}x, ${(match.confidence * 100).toFixed(0)}% confident pattern`,
        });
      }
    }

    const tags = node.tags;
    if (tags.includes("urgent") || tags.includes("critical")) {
      factors.push({
        name: "urgency",
        weight: 0.2,
        impact: "negative",
        description: "Tagged as urgent/critical — higher execution risk",
      });
    }

    if (tags.includes("recurring") || tags.includes("routine")) {
      factors.push({
        name: "recurrence",
        weight: 0.2,
        impact: "positive",
        description: "Recurring event — predictable execution pattern",
      });
    }

    return factors;
  }

  private _computeConfidence(dist: ProbabilityDistribution, factors: PredictionFactor[]): number {
    const varianceScore = Math.max(0, 1 - dist.variance / (dist.mean * 2 || 1));
    const factorScore = factors.reduce((s, f) => s + f.weight * (f.impact === "positive" ? 1 : -1), 0);
    const normalizedFactor = Math.max(0, Math.min(1, 0.5 + factorScore));
    return Math.min(varianceScore * 0.6 + normalizedFactor * 0.4, 0.95);
  }
}
