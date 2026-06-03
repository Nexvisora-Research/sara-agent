import type { EpisodicWorkflow } from './types.js'

export interface ReplayBatch {
  confidence: number
  workflows: EpisodicWorkflow[]
}

export class MemoryReplayManager {
  constructor(private readonly maxReplayItems = 120) {}

  replay(workflows: EpisodicWorkflow[]): ReplayBatch {
    const candidates = workflows
      .filter(workflow => workflow.actions.length > 0)
      .sort((a, b) => this.workflowScore(b) - this.workflowScore(a))
      .slice(0, this.maxReplayItems)

    const successful = candidates.filter(workflow => workflow.success).length

    return {
      confidence: candidates.length ? successful / candidates.length : 0,
      workflows: candidates.sort((a, b) => a.completedAt - b.completedAt)
    }
  }

  private workflowScore(workflow: EpisodicWorkflow): number {
    const ageMs = Math.max(1, Date.now() - workflow.completedAt)
    const recency = 1 / Math.log10(ageMs / 1000 + 10)
    const success = workflow.success ? 1 : 0.25
    const actionDensity = Math.min(1, workflow.actions.length / 6)
    const intentBonus = workflow.intent ? 0.15 : 0

    return recency * 0.35 + success * 0.35 + actionDensity * 0.15 + intentBonus
  }
}
