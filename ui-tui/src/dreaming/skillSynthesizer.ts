import type { DreamingStorage } from './storage.js'
import type { GeneratedSkill, ProceduralWorkflow, SkillRollbackSnapshot, WorkflowPattern } from './types.js'

const slugify = (value: string) =>
  value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 64) || 'workflow-skill'

const titleFromPattern = (pattern: WorkflowPattern) => {
  const first = pattern.actionSignature.split(' -> ')[0] ?? 'workflow'

  return `Dreamed ${first.replace(/[-_.]+/g, ' ')} Workflow`
}

const skillBody = (pattern: WorkflowPattern, title: string) => `---
name: ${slugify(title)}
description: Reusable workflow synthesized from repeated Sara episodic memory.
---

# ${title}

Use this skill when Sara sees a task that benefits from the repeated workflow:
\`${pattern.actionSignature}\`.

## Confidence

- Score: ${pattern.confidence.toFixed(2)}
- Occurrences: ${pattern.occurrenceCount}
- Success rate: ${(pattern.successRate * 100).toFixed(0)}%

## Procedure

${pattern.actionSignature
  .split(' -> ')
  .map((action, index) => `${index + 1}. Run or prepare \`${action}\` with the current task context.`)
  .join('\n')}

## Evidence

${pattern.examples.map(example => `- ${example.replace(/\s+/g, ' ').slice(0, 180)}`).join('\n') || '- No examples captured.'}
`

export class SkillSynthesizer {
  private readonly previousContentBySkill = new Map<string, null | string>()

  constructor(private readonly storage: DreamingStorage) {}

  async synthesize(patterns: WorkflowPattern[], existing: GeneratedSkill[]): Promise<GeneratedSkill[]> {
    const generated: GeneratedSkill[] = []
    const existingPatternIds = new Set(existing.filter(skill => skill.status === 'active').map(skill => skill.patternId))

    for (const pattern of patterns) {
      if (pattern.confidence < 0.62 || existingPatternIds.has(pattern.id)) {
        continue
      }

      generated.push(await this.createSkill(pattern))
    }

    return generated
  }

  async rollback(skill: GeneratedSkill, snapshot: SkillRollbackSnapshot): Promise<GeneratedSkill> {
    if (snapshot.previousContent === null) {
      await this.storage.deleteMaybe(skill.filePath)
    } else {
      await this.storage.writeSkill(skill.filePath, snapshot.previousContent)
    }

    return { ...skill, status: 'rolled_back' }
  }

  private async createSkill(pattern: WorkflowPattern): Promise<GeneratedSkill> {
    const title = titleFromPattern(pattern)
    const slug = slugify(`${title}-${pattern.id.slice(-8)}`)
    const filePath = this.storage.skillPath(slug)
    const content = skillBody(pattern, title)
    const previousContent = await this.storage.readMaybe(filePath)
    const skillId = `skill_${pattern.id}_${Date.now()}`
    const rollbackId = `rollback_${skillId}`

    this.validate(content)
    await this.storage.writeSkill(filePath, content)
    this.previousContentBySkill.set(skillId, previousContent)

    return {
      createdAt: Date.now(),
      description: `Synthesized from ${pattern.occurrenceCount} repeated workflows.`,
      filePath,
      id: skillId,
      patternId: pattern.id,
      rollbackId,
      status: 'active',
      title,
      version: 1
    }
  }

  toProceduralWorkflow(skill: GeneratedSkill, pattern: WorkflowPattern): ProceduralWorkflow {
    return {
      actions: pattern.actionSignature.split(' -> ').filter(Boolean),
      confidence: pattern.confidence,
      createdAt: Date.now(),
      id: `procedure_${pattern.id}`,
      patternId: pattern.id,
      skillId: skill.id,
      title: skill.title
    }
  }

  rollbackSnapshot(skill: GeneratedSkill, previousContent: null | string): SkillRollbackSnapshot {
    return {
      createdAt: Date.now(),
      filePath: skill.filePath,
      id: skill.rollbackId,
      previousContent: this.previousContentBySkill.get(skill.id) ?? previousContent,
      skillId: skill.id
    }
  }

  private validate(content: string) {
    if (!content.includes('# ') || !content.includes('## Procedure') || content.length < 120) {
      throw new Error('generated skill failed validation')
    }
  }
}
