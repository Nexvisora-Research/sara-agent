import type { DreamingEngine } from './engine.js'

let activeEngine: DreamingEngine | null = null

export const setDreamingEngine = (engine: DreamingEngine | null) => {
  activeEngine = engine
}

export const recordDreamingUserPrompt = (text: string, sessionId: null | string) => {
  activeEngine?.recordUserPrompt(text, sessionId)
}
