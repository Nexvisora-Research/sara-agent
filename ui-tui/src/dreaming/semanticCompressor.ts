import type { EpisodicWorkflow, MemorySummary } from './types.js'

const TOKEN_DIVISOR = 4

const estimateTokens = (text: string) => Math.ceil(text.length / TOKEN_DIVISOR)

const summarizeActions = (workflow: EpisodicWorkflow) =>
  workflow.actions
    .map(action => action.name)
    .filter(Boolean)
    .join(' -> ')

export class SemanticCompressor {
  constructor(private readonly keepRecentWorkflows = 40) {}

  compress(workflows: EpisodicWorkflow[], existing: MemorySummary[]): MemorySummary[] {
    const alreadySummarized = new Set(existing.flatMap(summary => summary.sourceWorkflowIds))
    const candidates = workflows.slice(0, Math.max(0, workflows.length - this.keepRecentWorkflows))
    const unsummarized = candidates.filter(workflow => !alreadySummarized.has(workflow.id))

    if (unsummarized.length < 5) {
      return existing
    }

    const chunks = this.chunk(unsummarized, 12)
    const created = chunks.map(chunk => this.createSummary(chunk))

    return [...existing, ...created].slice(-80)
  }

  private chunk<T>(items: T[], size: number): T[][] {
    const chunks: T[][] = []

    for (let i = 0; i < items.length; i += size) {
      chunks.push(items.slice(i, i + size))
    }

    return chunks
  }

  private createSummary(workflows: EpisodicWorkflow[]): MemorySummary {
    const successes = workflows.filter(workflow => workflow.success).length
    const commonActions = this.topActions(workflows).join(', ')
    const intents = workflows
      .map(workflow => workflow.intent?.trim())
      .filter(Boolean)
      .slice(0, 4)
      .join('; ')
    const actionFallback = workflows
      .slice(0, 4)
      .map(summarizeActions)
      .filter(Boolean)
      .join('; ')
    const text = [
      `Compressed ${workflows.length} workflows with ${Math.round((successes / workflows.length) * 100)}% success.`,
      commonActions ? `Common actions: ${commonActions}.` : '',
      intents ? `Representative intents: ${intents}.` : `Representative action flows: ${actionFallback}.`
    ]
      .filter(Boolean)
      .join(' ')

    return {
      confidence: Math.min(0.95, 0.55 + workflows.length / 40),
      createdAt: Date.now(),
      id: `summary_${Date.now()}_${workflows[0]?.id ?? 'unknown'}`,
      sourceWorkflowIds: workflows.map(workflow => workflow.id),
      text,
      tokenEstimate: estimateTokens(text)
    }
  }

  private topActions(workflows: EpisodicWorkflow[]): string[] {
    const counts = new Map<string, number>()

    for (const workflow of workflows) {
      for (const action of workflow.actions) {
        counts.set(action.name, (counts.get(action.name) ?? 0) + 1)
      }
    }

    return [...counts.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([name]) => name)
  }
}
