import type { ImprovementHypothesis, WorkflowPattern } from './types.js'

const hypothesisId = (pattern: WorkflowPattern) => `hypothesis_${pattern.id}`

export class AutonomousImprovementQueue {
  build(patterns: WorkflowPattern[], existing: ImprovementHypothesis[]): ImprovementHypothesis[] {
    const byId = new Map(existing.map(item => [item.id, item]))

    for (const pattern of patterns) {
      const id = hypothesisId(pattern)
      const current = byId.get(id)

      if (current?.status === 'accepted') {
        continue
      }

      byId.set(id, {
        confidence: pattern.confidence,
        createdAt: current?.createdAt ?? Date.now(),
        evidence: pattern.examples,
        id,
        patternId: pattern.id,
        priority: this.priority(pattern),
        status: current?.status ?? 'queued',
        text: `Repeated workflow "${pattern.actionSignature}" may be worth optimizing into a reusable Sara skill.`
      })
    }

    return [...byId.values()].sort((a, b) => b.priority - a.priority || b.confidence - a.confidence).slice(0, 100)
  }

  private priority(pattern: WorkflowPattern): number {
    return Math.round((pattern.confidence * 60 + pattern.occurrenceCount * 8 + pattern.successRate * 20) * 100) / 100
  }
}
