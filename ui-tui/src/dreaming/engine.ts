import { EventEmitter } from 'node:events'

import type { GatewayEvent } from '../gatewayTypes.js'

import { AutonomousImprovementQueue } from './improvementQueue.js'
import { WorkflowPatternDetector } from './patternDetector.js'
import { MemoryReplayManager } from './replayManager.js'
import { SemanticCompressor } from './semanticCompressor.js'
import { SkillSynthesizer } from './skillSynthesizer.js'
import { createEmptyDreamingState, DreamingStorage } from './storage.js'
import type {
  DreamingCycleResult,
  DreamingEngineOptions,
  DreamingEvent,
  DreamingGateway,
  DreamingState,
  EpisodicWorkflow,
  WorkflowAction,
  WorkflowPattern
} from './types.js'

const DEFAULT_IDLE_DELAY_MS = 10_000
const DEFAULT_CYCLE_INTERVAL_MS = 60_000
const DEFAULT_MAX_EPISODIC_WORKFLOWS = 300

interface ActiveWorkflow {
  actions: WorkflowAction[]
  assistantText: string
  id: string
  intent?: string
  sessionId: null | string
  startedAt: number
}

const workflowId = () => `workflow_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`

const assistantSummary = (text: string) => text.replace(/\s+/g, ' ').trim().slice(0, 240)

export class DreamingEngine extends EventEmitter {
  private active: ActiveWorkflow | null = null
  private attachedGateway: DreamingGateway | null = null
  private cycleTimer: null | ReturnType<typeof setInterval> = null
  private idle = true
  private idleSince = Date.now()
  private runningCycle = false
  private state: DreamingState = createEmptyDreamingState()

  private readonly cycleIntervalMs: number
  private readonly enabled: boolean
  private readonly idleDelayMs: number
  private readonly maxEpisodicWorkflows: number
  private readonly storage: DreamingStorage

  constructor(options: DreamingEngineOptions = {}) {
    super()
    this.setMaxListeners(0)
    this.enabled = options.enabled ?? process.env.sara_DREAMING_ENGINE !== '0'
    this.idleDelayMs = options.idleDelayMs ?? DEFAULT_IDLE_DELAY_MS
    this.cycleIntervalMs = options.cycleIntervalMs ?? DEFAULT_CYCLE_INTERVAL_MS
    this.maxEpisodicWorkflows = options.maxEpisodicWorkflows ?? DEFAULT_MAX_EPISODIC_WORKFLOWS
    this.storage = new DreamingStorage(options.storageDir)
  }

  async start() {
    if (!this.enabled || this.cycleTimer) {
      return
    }

    this.state = await this.storage.load()
    this.cycleTimer = setInterval(() => void this.runIfIdle(), this.cycleIntervalMs)
    this.cycleTimer.unref?.()
  }

  async stop() {
    if (this.cycleTimer) {
      clearInterval(this.cycleTimer)
      this.cycleTimer = null
    }

    if (this.attachedGateway) {
      this.attachedGateway.off('event', this.handleGatewayEvent)
      this.attachedGateway = null
    }

    await this.storage.save(this.state)
  }

  attachGateway(gateway: DreamingGateway) {
    if (!this.enabled || this.attachedGateway === gateway) {
      return
    }

    this.attachedGateway?.off('event', this.handleGatewayEvent)
    this.attachedGateway = gateway
    gateway.on('event', this.handleGatewayEvent)
  }

  recordUserPrompt(text: string, sessionId: null | string) {
    const trimmed = text.trim()

    if (!trimmed) {
      return
    }

    if (!this.active) {
      this.active = {
        actions: [],
        assistantText: '',
        id: workflowId(),
        intent: trimmed.slice(0, 500),
        sessionId,
        startedAt: Date.now()
      }

      return
    }

    this.active.intent = trimmed.slice(0, 500)
    this.active.sessionId = sessionId
  }

  async runIfIdle(): Promise<null | DreamingCycleResult> {
    if (!this.enabled || this.runningCycle || !this.idle || Date.now() - this.idleSince < this.idleDelayMs) {
      return null
    }

    this.runningCycle = true
    this.emitDream('dream.idle', { idleSince: this.idleSince })

    try {
      const result = await this.runCycle()

      this.emitDream('dream.cycle.complete', result)

      return result
    } catch (e) {
      this.emitDream('dream.cycle.failed', e)

      return null
    } finally {
      this.runningCycle = false
    }
  }

  async markSkillFailed(skillId: string, reason: string): Promise<boolean> {
    const skill = this.state.generatedSkills.find(item => item.id === skillId)
    const rollback = this.state.rollbacks.find(item => item.skillId === skillId)

    if (!skill || !rollback) {
      return false
    }

    const synthesizer = new SkillSynthesizer(this.storage)
    const rolledBack = await synthesizer.rollback({ ...skill, status: 'failed' }, rollback)

    this.state = {
      ...this.state,
      generatedSkills: this.state.generatedSkills.map(item => (item.id === skillId ? rolledBack : item)),
      hypotheses: [
        ...this.state.hypotheses,
        {
          confidence: 0.2,
          createdAt: Date.now(),
          evidence: [reason],
          id: `rollback_${skillId}`,
          patternId: skill.patternId,
          priority: 100,
          status: 'queued',
          text: `Rollback completed for generated skill "${skill.title}" after failure: ${reason}`
        }
      ]
    }
    await this.storage.save(this.state)
    this.emitDream('dream.skill.failed', rolledBack)

    return true
  }

  snapshot(): DreamingState {
    return structuredClone(this.state)
  }

  private async runCycle(): Promise<DreamingCycleResult> {
    const detector = new WorkflowPatternDetector()
    const replayManager = new MemoryReplayManager()
    const compressor = new SemanticCompressor()
    const improvementQueue = new AutonomousImprovementQueue()
    const synthesizer = new SkillSynthesizer(this.storage)
    const replay = replayManager.replay(this.state.episodicWorkflows)
    const patterns = detector.detect(replay.workflows)
    const generatedSkills = await synthesizer.synthesize(patterns, this.state.generatedSkills)
    const patternById = new Map(patterns.map(pattern => [pattern.id, pattern]))
    const rollbacks = []
    const proceduralWorkflows = []

    for (const skill of generatedSkills) {
      const pattern = patternById.get(skill.patternId)

      rollbacks.push(synthesizer.rollbackSnapshot(skill, null))

      if (pattern) {
        proceduralWorkflows.push(synthesizer.toProceduralWorkflow(skill, pattern))
      }

      this.emitDream('dream.skill.synthesized', skill)
    }

    const nextProcedural = this.mergeProcedural(this.state.proceduralWorkflows, proceduralWorkflows)
    const summaries = compressor.compress(this.state.episodicWorkflows, this.state.summaries)
    const hypotheses = improvementQueue.build(patterns, this.state.hypotheses)

    this.state = {
      ...this.state,
      generatedSkills: [...this.state.generatedSkills, ...generatedSkills].slice(-120),
      hypotheses,
      patterns,
      proceduralWorkflows: nextProcedural,
      rollbacks: [...this.state.rollbacks, ...rollbacks].slice(-120),
      summaries
    }
    await this.storage.save(this.state)

    return {
      generatedSkills,
      hypotheses,
      patterns,
      proceduralWorkflows,
      summaries
    }
  }

  private mergeProcedural(
    current: DreamingState['proceduralWorkflows'],
    next: DreamingState['proceduralWorkflows']
  ): DreamingState['proceduralWorkflows'] {
    const byPattern = new Map(current.map(item => [item.patternId, item]))

    for (const item of next) {
      byPattern.set(item.patternId, item)
    }

    return [...byPattern.values()].sort((a, b) => b.confidence - a.confidence).slice(0, 120)
  }

  private handleGatewayEvent = (ev: GatewayEvent) => {
    switch (ev.type) {
      case 'message.start':
        this.idle = false
        this.active = this.active ?? {
          actions: [],
          assistantText: '',
          id: workflowId(),
          sessionId: ev.session_id ?? null,
          startedAt: Date.now()
        }

        return

      case 'tool.start':
        this.idle = false
        this.ensureActive(ev).actions.push({
          name: ev.payload.name || 'tool'
        })

        return

      case 'tool.complete': {
        this.idle = false
        const active = this.ensureActive(ev)
        const last = [...active.actions].reverse().find(action => action.name === (ev.payload.name || 'tool') && !action.summary)

        if (last) {
          last.durationMs = ev.payload.duration_s ? ev.payload.duration_s * 1000 : undefined
          last.error = ev.payload.error
          last.summary = ev.payload.summary
        }

        return
      }

      case 'message.delta':
        if (ev.payload?.text) {
          this.ensureActive(ev).assistantText += ev.payload.text
        }

        return

      case 'message.complete':
        void this.completeWorkflow(ev)

        return

      case 'error':
        this.idle = true
        this.idleSince = Date.now()

        if (this.active) {
          void this.completeWorkflow(ev, false)
        }

        return

      default:
        return
    }
  }

  private ensureActive(ev: GatewayEvent): ActiveWorkflow {
    if (!this.active) {
      this.active = {
        actions: [],
        assistantText: '',
        id: workflowId(),
        sessionId: ev.session_id ?? null,
        startedAt: Date.now()
      }
    }

    return this.active
  }

  private async completeWorkflow(ev: GatewayEvent, success = true) {
    const active = this.active

    if (!active) {
      this.idle = true
      this.idleSince = Date.now()

      return
    }

    const text = ev.type === 'message.complete' ? ev.payload?.text || ev.payload?.rendered || active.assistantText : active.assistantText
    const workflow: EpisodicWorkflow = {
      actions: active.actions,
      assistantSummary: assistantSummary(text ?? ''),
      completedAt: Date.now(),
      durationMs: Date.now() - active.startedAt,
      id: active.id,
      intent: active.intent,
      sessionId: ev.session_id ?? active.sessionId,
      success: success && active.actions.every(action => !action.error)
    }

    this.active = null
    this.idle = true
    this.idleSince = Date.now()

    if (workflow.actions.length) {
      this.state = {
        ...this.state,
        episodicWorkflows: [...this.state.episodicWorkflows, workflow].slice(-this.maxEpisodicWorkflows)
      }
      await this.storage.save(this.state)
      this.emitDream('dream.workflow.recorded', workflow)
    }
  }

  private emitDream(event: DreamingEvent, payload: unknown) {
    this.emit(event, payload)
  }
}
