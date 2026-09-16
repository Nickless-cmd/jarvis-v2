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

/**
 * Pak runtimens indpakning af et tool-resultat ud.
 *
 * Et resultat fra explore/spawn_agent_task/quick_council_check når ALDRIG
 * klienten som ren JSON. Fire lag kan ligge udenom, og de kan optræde sammen:
 *
 *   ⚠ <advarsel>\n\n        simple_tool_executor.py (soft_warn)
 *   [UTROET kilde=… ]\n…\n[/UTROET]   untrusted_fencing.py (fence)
 *   \n[keys: …]             simple_tools.py, naar dumpen er klippet ved 8.000 tegn
 *
 * JSON.parse paa den raa streng kaster derfor hver eneste gang. Det var ikke
 * til at se: alle tests fodrede ren, haandskrevet JSON ind.
 */
export function unwrapToolResult(result?: string): string {
  if (!result) return ''
  let tekst = result.trim()
  // Soft-warn staar FOERST, uden for hegnet.
  tekst = tekst.replace(/^⚠[^\n]*\n\n/, '').trim()
  const hegn = tekst.match(/^\[UTROET kilde=[^\]]*\]\n([\s\S]*?)(?:\n\[\/UTROET\])?$/)
  if (hegn) tekst = hegn[1]!.trim()
  // Hale-noten fra en klippet dump er ikke en del af nyttelasten.
  tekst = tekst.replace(/\n\[keys: [\s\S]*$/, '').trim()
  return tekst
}

function objectResult(result?: string): Record<string, unknown> | null {
  const tekst = unwrapToolResult(result)
  if (!tekst) return null
  try {
    const value = JSON.parse(tekst)
    return value && typeof value === 'object' && !Array.isArray(value)
      ? value as Record<string, unknown>
      : null
  } catch {
    return null
  }
}

/** Sidste udvej: en KLIPPET dump er ugyldig JSON, men id'et staar der stadig. */
function agentIdsFraTekst(result?: string): string[] {
  const tekst = unwrapToolResult(result)
  if (!tekst) return []
  return [...tekst.matchAll(/"agent_id"\s*:\s*"([^"]+)"/g)].map((m) => m[1]!)
}

function textValue(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value.trim() : undefined
}

function agentReferences(tool: ToolEvidence): AgentReference[] {
  if (!AGENT_RESULT_TOOLS.has(tool.name)) return []
  // IKKE en tidlig return naar resultatet ikke kan parses: et hegnet, klippet
  // eller endnu-ikke-ankommet resultat er netop de tilfaelde udvejene nedenfor
  // findes for.
  const result = objectResult(tool.result)
  const refs: AgentReference[] = []
  const commonGoal = goalFrom(tool.input)
  const topId = result ? textValue(result.agent_id) : undefined
  if (topId) {
    refs.push({
      agentId: topId,
      role: result ? textValue(result.role) : undefined,
      goal: commonGoal,
      // KUN agent_status. simple_tools.py:2112 filtrerer `status` ud af dumpen,
      // saa den `status` der evt. overlever er TOOLETS — «ok» er ikke en
      // agent-tilstand, og «koerer»-tjekket ville aldrig lyse.
      status: result ? textValue(result.agent_status) : undefined,
      dispatchToolUseId: tool.id,
    })
  }
  if (result && Array.isArray(result.spawned)) {
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

  // To sidste udveje, saa fladen ikke er tom netop naar den betyder noget:
  //
  //  1. En KLIPPET dump kan ikke parses, men id'et staar der stadig.
  //  2. En dispatch UNDER koersel har slet intet resultat endnu. Sådan opførte
  //     main sig — en agent-dispatch VAR en agent-raekke — og det er praecis
  //     mens agenten arbejder man vil se den. Raekken har intet agent_id, og
  //     det skal kunne ses paa den: tom agentId betyder «detaljen kan ikke
  //     hentes, men kaldet findes».
  if (refs.length === 0) {
    for (const id of agentIdsFraTekst(tool.result)) {
      refs.push({ agentId: id, goal: commonGoal, dispatchToolUseId: tool.id })
    }
  }
  if (refs.length === 0) {
    refs.push({
      agentId: '',
      goal: commonGoal,
      status: tool.status === 'running' ? 'running' : undefined,
      dispatchToolUseId: tool.id,
    })
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
