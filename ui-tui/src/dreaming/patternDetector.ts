import type { EpisodicWorkflow, WorkflowPattern } from './types.js'

const clamp = (value: number) => Math.max(0, Math.min(1, value))

const actionSignature = (workflow: EpisodicWorkflow) =>
  workflow.actions
    .map(action => action.name.trim().toLowerCase())
    .filter(Boolean)
    .join(' -> ')

const patternId = (signature: string) =>
  `pattern_${Buffer.from(signature).toString('base64url').slice(0, 24) || 'empty'}`

export class WorkflowPatternDetector {
  constructor(private readonly minOccurrences = 2) {}

  detect(workflows: EpisodicWorkflow[]): WorkflowPattern[] {
    const groups = new Map<string, EpisodicWorkflow[]>()

    for (const workflow of workflows) {
      const signature = actionSignature(workflow)

      if (!signature) {
        continue
      }

      groups.set(signature, [...(groups.get(signature) ?? []), workflow])
    }

    return [...groups.entries()]
      .filter(([, rows]) => rows.length >= this.minOccurrences)
      .map(([signature, rows]) => this.toPattern(signature, rows))
      .sort((a, b) => b.confidence - a.confidence || b.occurrenceCount - a.occurrenceCount)
  }

  private toPattern(signature: string, rows: EpisodicWorkflow[]): WorkflowPattern {
    const occurrenceScore = clamp(rows.length / Math.max(this.minOccurrences + 3, 5))
    const successRate = rows.filter(row => row.success).length / rows.length
    const recency = Math.max(...rows.map(row => row.completedAt))
    const hasUsefulIntent = rows.some(row => Boolean(row.intent?.trim()))
    const confidence = clamp(0.45 * occurrenceScore + 0.4 * successRate + (hasUsefulIntent ? 0.15 : 0.05))

    return {
      actionSignature: signature,
      confidence,
      examples: rows
        .slice(-3)
        .map(row => row.intent || row.assistantSummary || row.actions.map(action => action.name).join(', '))
        .filter(Boolean),
      id: patternId(signature),
      lastSeenAt: recency,
      occurrenceCount: rows.length,
      successRate
    }
  }
}
