import type { GatewayEvent } from '../gatewayTypes.js'

export type DreamingEvent =
  | 'dream.cycle.complete'
  | 'dream.cycle.failed'
  | 'dream.idle'
  | 'dream.skill.failed'
  | 'dream.skill.synthesized'
  | 'dream.workflow.recorded'

export interface WorkflowAction {
  durationMs?: number
  error?: string
  name: string
  summary?: string
}

export interface EpisodicWorkflow {
  actions: WorkflowAction[]
  assistantSummary?: string
  completedAt: number
  durationMs: number
  id: string
  intent?: string
  sessionId: null | string
  success: boolean
}

export interface WorkflowPattern {
  actionSignature: string
  confidence: number
  examples: string[]
  id: string
  lastSeenAt: number
  occurrenceCount: number
  successRate: number
}

export interface GeneratedSkill {
  createdAt: number
  description: string
  filePath: string
  id: string
  patternId: string
  rollbackId: string
  status: 'active' | 'failed' | 'rolled_back'
  title: string
  version: number
}

export interface MemorySummary {
  confidence: number
  createdAt: number
  id: string
  sourceWorkflowIds: string[]
  text: string
  tokenEstimate: number
}

export interface ImprovementHypothesis {
  confidence: number
  createdAt: number
  evidence: string[]
  id: string
  patternId?: string
  priority: number
  status: 'queued' | 'accepted' | 'rejected'
  text: string
}

export interface ProceduralWorkflow {
  actions: string[]
  confidence: number
  createdAt: number
  id: string
  patternId: string
  skillId?: string
  title: string
}

export interface SkillRollbackSnapshot {
  createdAt: number
  filePath: string
  id: string
  previousContent: null | string
  skillId: string
}

export interface DreamingState {
  episodicWorkflows: EpisodicWorkflow[]
  generatedSkills: GeneratedSkill[]
  hypotheses: ImprovementHypothesis[]
  patterns: WorkflowPattern[]
  proceduralWorkflows: ProceduralWorkflow[]
  rollbacks: SkillRollbackSnapshot[]
  summaries: MemorySummary[]
  updatedAt: number
  version: 1
}

export interface DreamingCycleResult {
  generatedSkills: GeneratedSkill[]
  hypotheses: ImprovementHypothesis[]
  patterns: WorkflowPattern[]
  proceduralWorkflows: ProceduralWorkflow[]
  summaries: MemorySummary[]
}

export interface DreamingEngineOptions {
  cycleIntervalMs?: number
  enabled?: boolean
  idleDelayMs?: number
  maxEpisodicWorkflows?: number
  minPatternOccurrences?: number
  storageDir?: string
}

export interface DreamingGateway {
  on(event: 'event', listener: (ev: GatewayEvent) => void): unknown
  off(event: 'event', listener: (ev: GatewayEvent) => void): unknown
}
