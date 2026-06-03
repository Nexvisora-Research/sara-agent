import type { ScheduleConflict, ImpactScore, TemporalNode } from "../types";
import type { TemporalGraphStore } from "../graph/store";

export class ConflictDetector {
  detectOverlaps(store: TemporalGraphStore): ScheduleConflict[] {
    const conflicts: ScheduleConflict[] = [];
    const nodes = store.queryNodes({});
    const timedNodes = nodes.filter(
      (n) => n.endTime !== undefined && n.type !== "milestone"
    );

    for (let i = 0; i < timedNodes.length; i++) {
      for (let j = i + 1; j < timedNodes.length; j++) {
        const a = timedNodes[i];
        const b = timedNodes[j];
        if (!this._overlaps(a, b)) continue;

        const severity = this._severity(a, b);
        const conflict: ScheduleConflict = {
          id: `conflict_${a.id}_${b.id}`,
          type: "overlap",
          severity,
          involvedNodeIds: [a.id, b.id],
          description: `"${a.label}" overlaps with "${b.label}"`,
          suggestion: this._suggestResolution(a, b),
          timeRange: {
            start: Math.max(a.startTime, b.startTime),
            end: Math.min(a.endTime!, b.endTime!),
          },
        };
        conflicts.push(conflict);
      }
    }

    return conflicts;
  }

  detectDeadlineRisks(store: TemporalGraphStore): ScheduleConflict[] {
    const conflicts: ScheduleConflict[] = [];
    const now = Date.now();
    const deadlines = store.queryNodes({ types: ["deadline"] });
    const tasks = store.queryNodes({ types: ["task"] });

    for (const dl of deadlines) {
      const dependentTasks = tasks.filter((t) => {
        const edges = store.getEdges(t.id, "both");
        return edges.some((e) => e.targetId === dl.id && e.type === "depends_on");
      });

      const totalEstimatedHours = dependentTasks.reduce((sum, t) => {
        if (t.endTime) return sum + (t.endTime - t.startTime) / (1000 * 60 * 60);
        return sum + 1;
      }, 0);

      const hoursUntilDeadline = (dl.startTime - now) / (1000 * 60 * 60);
      const riskRatio = hoursUntilDeadline > 0 ? totalEstimatedHours / hoursUntilDeadline : 2;

      if (riskRatio > 0.8) {
        const severity = riskRatio > 1.5 ? "critical" : riskRatio > 1 ? "high" : "medium";
        conflicts.push({
          id: `deadline_risk_${dl.id}`,
          type: "deadline_risk",
          severity,
          involvedNodeIds: [dl.id, ...dependentTasks.map((t) => t.id)],
          description: `Deadline "${dl.label}" at risk: ${totalEstimatedHours.toFixed(1)}h of work in ${hoursUntilDeadline.toFixed(1)}h`,
          suggestion: `Consider reprioritizing tasks or extending the deadline for "${dl.label}"`,
          timeRange: { start: now, end: dl.startTime },
        });
      }
    }

    return conflicts;
  }

  detectDependencyBreaches(store: TemporalGraphStore): ScheduleConflict[] {
    const conflicts: ScheduleConflict[] = [];
    const nodes = store.queryNodes({});

    for (const node of nodes) {
      const incoming = store.getEdges(node.id, "incoming")
        .filter((e) => e.type === "depends_on");

      for (const edge of incoming) {
        const dependency = store.getNode(edge.sourceId);
        if (!dependency) continue;
        if (dependency.endTime && dependency.endTime > node.startTime) {
          conflicts.push({
            id: `dep_breach_${edge.id}`,
            type: "dependency_breach",
            severity: "high",
            involvedNodeIds: [dependency.id, node.id],
            description: `"${node.label}" depends on "${dependency.label}" which finishes after it starts`,
            suggestion: `Reschedule "${node.label}" to start after "${dependency.label}" completes`,
            timeRange: {
              start: node.startTime,
              end: dependency.endTime,
            },
          });
        }
      }
    }

    return conflicts;
  }

  detectAll(store: TemporalGraphStore): ScheduleConflict[] {
    return [
      ...this.detectOverlaps(store),
      ...this.detectDeadlineRisks(store),
      ...this.detectDependencyBreaches(store),
    ];
  }

  // ─── Impact Scoring ────────────────────────────────────────────────

  scoreFutureImpact(nodeId: string, store: TemporalGraphStore): ImpactScore {
    const node = store.getNode(nodeId);
    if (!node) {
      return { nodeId, score: 0, breakdown: {}, affectedNodes: [], rippleEffect: 0 };
    }

    const downstream = this._findDownstream(nodeId, store);
    const overlapConflicts = this.detectOverlaps(store)
      .filter((c) => c.involvedNodeIds.includes(nodeId));

    const dependencyScore = Math.min(downstream.length / 10, 1) * 0.3;
    const overlapScore = Math.min(overlapConflicts.length / 5, 1) * 0.25;

    let urgencyScore = 0;
    if (node.endTime) {
      const remaining = (node.endTime - Date.now()) / (1000 * 60 * 60);
      urgencyScore = remaining < 24 ? 0.3 : remaining < 72 ? 0.15 : 0.05;
    }

    const tagScore = (node.tags.includes("critical") || node.tags.includes("urgent") ? 0.15 : 0);

    const score = Math.min(dependencyScore + overlapScore + urgencyScore + tagScore, 1);

    return {
      nodeId,
      score,
      breakdown: {
        dependency_chain: dependencyScore,
        conflict_count: overlapScore,
        time_urgency: urgencyScore,
        tag_importance: tagScore,
      },
      affectedNodes: downstream.map((n) => n.id),
      rippleEffect: downstream.length,
    };
  }

  scoreAllFutureImpact(store: TemporalGraphStore): ImpactScore[] {
    const nodes = store.queryNodes({});
    return nodes
      .map((n) => this.scoreFutureImpact(n.id, store))
      .sort((a, b) => b.score - a.score);
  }

  // ─── Helpers ───────────────────────────────────────────────────────

  private _overlaps(a: TemporalNode, b: TemporalNode): boolean {
    if (a.endTime === undefined || b.endTime === undefined) return false;
    return a.startTime < b.endTime && b.startTime < a.endTime;
  }

  private _severity(a: TemporalNode, b: TemporalNode): "low" | "medium" | "high" | "critical" {
    const overlapDuration = Math.min(a.endTime!, b.endTime!) - Math.max(a.startTime, b.startTime);
    const aDuration = a.endTime! - a.startTime;
    const bDuration = b.endTime! - b.startTime;
    const overlapRatio = overlapDuration / Math.min(aDuration, bDuration);

    if (overlapRatio > 0.8) return "critical";
    if (overlapRatio > 0.5) return "high";
    if (overlapRatio > 0.25) return "medium";
    return "low";
  }

  private _suggestResolution(a: TemporalNode, b: TemporalNode): string {
    const aDuration = a.endTime! - a.startTime;
    const bDuration = b.endTime! - b.startTime;
    if (aDuration >= bDuration) {
      return `Move "${b.label}" to ${new Date(a.endTime!).toLocaleTimeString()} or later`;
    }
    return `Move "${a.label}" to ${new Date(b.endTime!).toLocaleTimeString()} or later`;
  }

  private _findDownstream(nodeId: string, store: TemporalGraphStore): TemporalNode[] {
    const visited = new Set<string>();
    const queue = [nodeId];
    const downstream: TemporalNode[] = [];
    const maxDepth = 10;
    let depth = 0;

    while (queue.length > 0 && depth < maxDepth) {
      const levelSize = queue.length;
      for (let i = 0; i < levelSize; i++) {
        const current = queue.shift()!;
        if (visited.has(current)) continue;
        visited.add(current);

        const edges = store.getEdges(current, "outgoing")
          .filter((e) => e.type === "depends_on" || e.type === "triggers");
        for (const edge of edges) {
          if (!visited.has(edge.targetId)) {
            const target = store.getNode(edge.targetId);
            if (target) {
              downstream.push(target);
              queue.push(edge.targetId);
            }
          }
        }
      }
      depth++;
    }

    return downstream;
  }
}
