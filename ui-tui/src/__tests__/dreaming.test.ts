import { mkdtempSync, readFileSync, rmSync, existsSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { EventEmitter } from 'node:events'

import { afterEach, describe, expect, it } from 'vitest'

import { DreamingEngine } from '../dreaming/index.js'
import type { GatewayEvent } from '../gatewayTypes.js'

class FakeGateway extends EventEmitter {
  emitGateway(ev: GatewayEvent) {
    this.emit('event', ev)
  }
}

const tempRoots: string[] = []

const makeTempRoot = () => {
  const root = mkdtempSync(join(tmpdir(), 'sara-dreaming-'))

  tempRoots.push(root)

  return root
}

const waitFor = <T>(engine: DreamingEngine, event: string) =>
  new Promise<T>(resolve => engine.once(event, value => resolve(value as T)))

afterEach(() => {
  for (const root of tempRoots.splice(0)) {
    rmSync(root, { force: true, recursive: true })
  }
})

describe('DreamingEngine', () => {
  it('records completed gateway turns as episodic workflows', async () => {
    const gateway = new FakeGateway()
    const engine = new DreamingEngine({ cycleIntervalMs: 60_000, idleDelayMs: 0, storageDir: makeTempRoot() })

    engine.attachGateway(gateway)
    await engine.start()

    const recorded = waitFor(engine, 'dream.workflow.recorded')

    engine.recordUserPrompt('Summarize the current git status', 'session-1')
    gateway.emitGateway({ session_id: 'session-1', type: 'message.start' })
    gateway.emitGateway({
      payload: { context: 'git status --short', name: 'exec_command', tool_id: 'tool-1' },
      session_id: 'session-1',
      type: 'tool.start'
    })
    gateway.emitGateway({
      payload: { duration_s: 0.2, name: 'exec_command', summary: 'clean', tool_id: 'tool-1' },
      session_id: 'session-1',
      type: 'tool.complete'
    })
    gateway.emitGateway({
      payload: { text: 'The tree is clean.' },
      session_id: 'session-1',
      type: 'message.complete'
    })

    await recorded

    const state = engine.snapshot()

    expect(state.episodicWorkflows).toHaveLength(1)
    expect(state.episodicWorkflows[0]?.intent).toBe('Summarize the current git status')
    expect(state.episodicWorkflows[0]?.actions[0]?.name).toBe('exec_command')

    await engine.stop()
  })

  it('dreams repeated workflows into skills, hypotheses, summaries, and procedural memory', async () => {
    const root = makeTempRoot()
    const gateway = new FakeGateway()
    const engine = new DreamingEngine({ cycleIntervalMs: 60_000, idleDelayMs: 0, storageDir: root })

    engine.attachGateway(gateway)
    await engine.start()

    for (let i = 0; i < 45; i++) {
      const recorded = waitFor(engine, 'dream.workflow.recorded')

      engine.recordUserPrompt(`Inspect logs ${i}`, 'session-1')
      gateway.emitGateway({ session_id: 'session-1', type: 'message.start' })
      gateway.emitGateway({
        payload: { context: 'tail logs', name: 'exec_command', tool_id: `tool-a-${i}` },
        session_id: 'session-1',
        type: 'tool.start'
      })
      gateway.emitGateway({
        payload: { duration_s: 0.1, name: 'exec_command', summary: 'logs read', tool_id: `tool-a-${i}` },
        session_id: 'session-1',
        type: 'tool.complete'
      })
      gateway.emitGateway({
        payload: { context: 'summarize', name: 'memory_search', tool_id: `tool-b-${i}` },
        session_id: 'session-1',
        type: 'tool.start'
      })
      gateway.emitGateway({
        payload: { duration_s: 0.1, name: 'memory_search', summary: 'memory searched', tool_id: `tool-b-${i}` },
        session_id: 'session-1',
        type: 'tool.complete'
      })
      gateway.emitGateway({
        payload: { text: `Done ${i}` },
        session_id: 'session-1',
        type: 'message.complete'
      })

      await recorded
    }

    const result = await engine.runIfIdle()
    const state = engine.snapshot()
    const skill = state.generatedSkills[0]

    expect(result?.patterns[0]?.actionSignature).toBe('exec_command -> memory_search')
    expect(skill?.status).toBe('active')
    expect(skill?.filePath && existsSync(skill.filePath)).toBe(true)
    expect(state.hypotheses[0]?.status).toBe('queued')
    expect(state.proceduralWorkflows[0]?.actions).toEqual(['exec_command', 'memory_search'])
    expect(state.summaries.length).toBeGreaterThan(0)

    const skillText = readFileSync(skill!.filePath, 'utf8')

    expect(skillText).toContain('## Procedure')

    const rolledBack = await engine.markSkillFailed(skill!.id, 'validation failed downstream')

    expect(rolledBack).toBe(true)
    expect(existsSync(skill!.filePath)).toBe(false)
    expect(engine.snapshot().generatedSkills[0]?.status).toBe('rolled_back')

    await engine.stop()
  })
})
