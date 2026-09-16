import { kilderFraTekst, type Kilde } from './kilder'
import type { ContentBlock } from './sseProtocol'

export interface ToolEvidence {
  id: string
  name: string
  input: Record<string, unknown>
  status: 'running' | 'done' | 'error'
  result?: string
}

export interface SourceEvidence extends Kilde {
  toolUseId?: string
  toolName?: string
  input?: Record<string, unknown>
  resultExcerpt?: string
  origin: 'tool_input' | 'tool_result' | 'assistant_text'
}

export interface AgentReference {
  agentId: string
  role?: string
  goal?: string
  status?: string
  dispatchToolUseId: string
}

export interface EnvironmentEvidence {
  tools: ToolEvidence[]
  sources: SourceEvidence[]
  agents: AgentReference[]
}

const AGENT_RESULT_TOOLS = new Set([
  'explore',
  'spawn_agent_task',
  'quick_council_check',
  'dispatch_code_mode_task',
])

function parsedInput(block: Extract<ContentBlock, { type: 'tool_use' }>): Record<string, unknown> {
  let partial: Record<string, unknown> = {}
  if (block.partialJson) {
    try {
      const value = JSON.parse(block.partialJson)
      if (value && typeof value === 'object' && !Array.isArray(value)) {
        partial = value as Record<string, unknown>
      }
    } catch {
      // A live partial is expected to be invalid until the block completes.
    }
  }
  return { ...partial, ...(block.input ?? {}) }
}

function goalFrom(input: Record<string, unknown>): string | undefined {
  for (const key of ['query', 'goal', 'task', 'prompt', 'description', 'question']) {
    const value = input[key]
    if (typeof value === 'string' && value.trim()) return value.replace(/\s+/g, ' ').trim()
  }
  return undefined
}

function objectResult(result?: string): Record<string, unknown> | null {
  if (!result) return null
  try {
    const value = JSON.parse(result)
    return value && typeof value === 'object' && !Array.isArray(value)
      ? value as Record<string, unknown>
      : null
  } catch {
    return null
  }
}

function textValue(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value.trim() : undefined
}

function agentReferences(tool: ToolEvidence): AgentReference[] {
  if (!AGENT_RESULT_TOOLS.has(tool.name)) return []
  const result = objectResult(tool.result)
  if (!result) return []
  const refs: AgentReference[] = []
  const commonGoal = goalFrom(tool.input)
  const topId = textValue(result.agent_id)
  if (topId) {
    refs.push({
      agentId: topId,
      role: textValue(result.role),
      goal: commonGoal,
      status: textValue(result.agent_status) ?? textValue(result.status),
      dispatchToolUseId: tool.id,
    })
  }
  if (Array.isArray(result.spawned)) {
    for (const item of result.spawned) {
      if (!item || typeof item !== 'object' || Array.isArray(item)) continue
      const row = item as Record<string, unknown>
      const agentId = textValue(row.agent_id)
      if (!agentId) continue
      refs.push({
        agentId,
        role: textValue(row.role),
        goal: textValue(row.goal) ?? commonGoal,
        status: textValue(row.status),
        dispatchToolUseId: tool.id,
      })
    }
  }
  return refs
}

function addSource(target: Map<string, SourceEvidence>, source: SourceEvidence): void {
  if (!target.has(source.url)) target.set(source.url, source)
}

export function buildEnvironmentEvidence(
  blockGroups: readonly ContentBlock[][],
): EnvironmentEvidence {
  const toolMap = new Map<string, ToolEvidence>()
  const assistantTexts: string[] = []

  for (const blocks of blockGroups) {
    for (const block of blocks) {
      if (!block) continue
      if (block.type === 'text') {
        assistantTexts.push(block.text)
        continue
      }
      if (block.type !== 'tool_use' || !block.id) continue
      toolMap.set(block.id, {
        id: block.id,
        name: block.name,
        input: parsedInput(block),
        status: block.status ?? 'done',
        ...(typeof block.result === 'string' ? { result: block.result } : {}),
      })
    }
  }

  const tools = [...toolMap.values()]
  const sourceMap = new Map<string, SourceEvidence>()
  for (const tool of tools) {
    for (const source of kilderFraTekst(JSON.stringify(tool.input))) {
      addSource(sourceMap, {
        ...source,
        toolUseId: tool.id,
        toolName: tool.name,
        input: tool.input,
        origin: 'tool_input',
      })
    }
    if (tool.result) {
      for (const source of kilderFraTekst(tool.result)) {
        addSource(sourceMap, {
          ...source,
          toolUseId: tool.id,
          toolName: tool.name,
          input: tool.input,
          resultExcerpt: tool.result.slice(0, 4000),
          origin: 'tool_result',
        })
      }
    }
  }
  for (const text of assistantTexts) {
    for (const source of kilderFraTekst(text)) {
      addSource(sourceMap, { ...source, origin: 'assistant_text' })
    }
  }

  const agentMap = new Map<string, AgentReference>()
  for (const tool of tools) {
    for (const agent of agentReferences(tool)) agentMap.set(agent.agentId, agent)
  }
  return { tools, sources: [...sourceMap.values()], agents: [...agentMap.values()] }
}

export function mergeEnvironmentEvidence(
  ...sets: readonly EnvironmentEvidence[]
): EnvironmentEvidence {
  const tools = new Map<string, ToolEvidence>()
  const sources = new Map<string, SourceEvidence>()
  const agents = new Map<string, AgentReference>()
  for (const set of sets) {
    for (const tool of set.tools) tools.set(tool.id, tool)
    for (const source of set.sources) {
      if (!sources.has(source.url)) sources.set(source.url, source)
    }
    for (const agent of set.agents) agents.set(agent.agentId, agent)
  }
  return { tools: [...tools.values()], sources: [...sources.values()], agents: [...agents.values()] }
}

export function sourcesForTool(tool: ToolEvidence): SourceEvidence[] {
  const block: ContentBlock = {
    type: 'tool_use', id: tool.id, name: tool.name, input: tool.input,
    status: tool.status, ...(tool.result === undefined ? {} : { result: tool.result }),
  }
  return buildEnvironmentEvidence([[block]]).sources
}
