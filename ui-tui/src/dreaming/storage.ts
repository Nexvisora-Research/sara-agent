import { mkdir, readFile, rename, rm, writeFile } from 'node:fs/promises'
import { homedir } from 'node:os'
import { dirname, join } from 'node:path'

import type { DreamingState } from './types.js'

const STATE_FILE = 'dreaming-state.json'

export const createEmptyDreamingState = (): DreamingState => ({
  episodicWorkflows: [],
  generatedSkills: [],
  hypotheses: [],
  patterns: [],
  proceduralWorkflows: [],
  rollbacks: [],
  summaries: [],
  updatedAt: Date.now(),
  version: 1
})

const asArray = <T>(value: unknown): T[] => (Array.isArray(value) ? (value as T[]) : [])

const normalizeState = (raw: unknown): DreamingState => {
  if (!raw || typeof raw !== 'object') {
    return createEmptyDreamingState()
  }

  const row = raw as Partial<DreamingState>

  return {
    episodicWorkflows: asArray(row.episodicWorkflows),
    generatedSkills: asArray(row.generatedSkills),
    hypotheses: asArray(row.hypotheses),
    patterns: asArray(row.patterns),
    proceduralWorkflows: asArray(row.proceduralWorkflows),
    rollbacks: asArray(row.rollbacks),
    summaries: asArray(row.summaries),
    updatedAt: typeof row.updatedAt === 'number' ? row.updatedAt : Date.now(),
    version: 1
  }
}

export class DreamingStorage {
  readonly rootDir: string
  readonly statePath: string
  readonly skillsDir: string

  constructor(rootDir = process.env.sara_DREAMING_HOME || join(homedir(), '.sara', 'dreaming')) {
    this.rootDir = rootDir
    this.statePath = join(rootDir, STATE_FILE)
    this.skillsDir = join(rootDir, 'evolved-skills')
  }

  async ensure() {
    await mkdir(this.rootDir, { recursive: true, mode: 0o700 })
    await mkdir(this.skillsDir, { recursive: true, mode: 0o700 })
  }

  async load(): Promise<DreamingState> {
    await this.ensure()

    try {
      const text = await readFile(this.statePath, 'utf8')

      return normalizeState(JSON.parse(text))
    } catch (e) {
      if ((e as NodeJS.ErrnoException).code === 'ENOENT') {
        return createEmptyDreamingState()
      }

      throw e
    }
  }

  async save(state: DreamingState): Promise<void> {
    await this.ensure()

    const next = { ...state, updatedAt: Date.now() }
    const tmp = `${this.statePath}.${process.pid}.${Date.now()}.tmp`

    await writeFile(tmp, `${JSON.stringify(next, null, 2)}\n`, { mode: 0o600 })
    await rename(tmp, this.statePath)
  }

  skillPath(slug: string): string {
    return join(this.skillsDir, slug, 'SKILL.md')
  }

  async writeSkill(filePath: string, content: string): Promise<void> {
    await mkdir(dirname(filePath), { recursive: true, mode: 0o700 })
    await writeFile(filePath, content, { mode: 0o600 })
  }

  async deleteMaybe(filePath: string): Promise<void> {
    try {
      await rm(filePath)
    } catch (e) {
      if ((e as NodeJS.ErrnoException).code !== 'ENOENT') {
        throw e
      }
    }
  }

  async readMaybe(filePath: string): Promise<null | string> {
    try {
      return await readFile(filePath, 'utf8')
    } catch (e) {
      if ((e as NodeJS.ErrnoException).code === 'ENOENT') {
        return null
      }

      throw e
    }
  }
}
