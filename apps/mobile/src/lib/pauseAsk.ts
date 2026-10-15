import type { ChatMessage } from './types'
import type { ContentBlock } from './sseProtocol'
import { parseBlocks, type PersistedBlock } from './persistedBlocks'
import { denseBlocks } from './blockHelpers'

export type PauseAsk = {
  question: string
  options: string[]
  allowMultiple: boolean
  context: string
  urgency: 'low' | 'normal' | 'high'
}

function parseResult(result: unknown): PauseAsk | null {
  let data = result
  if (typeof data === 'string') {
    if (!data.includes('pause_and_ask')) return null
    try { data = JSON.parse(data) } catch { return null }
  }
  if (!data || typeof data !== 'object' || Array.isArray(data)) return null
  const value = data as Record<string, unknown>
  if (value.kind !== 'pause_and_ask') return null
  const question = String(value.question ?? '').trim()
  if (!question) return null
  const options = Array.isArray(value.options)
    ? value.options.map((item: unknown) => String(item).trim()).filter((item: string) => item.length > 0 && item.length <= 120).slice(0, 6)
    : []
  const urgency = value.urgency === 'high' || value.urgency === 'low' ? value.urgency : 'normal'
  return {
    question,
    options,
    allowMultiple: value.allow_multiple === true,
    context: String(value.context ?? '').trim().slice(0, 400),
    urgency,
  }
}

function pauseIn(blocks: (PersistedBlock | ContentBlock)[]): PauseAsk | null {
  // En PERSISTERET tur bærer resultatet i en SEPARAT `tool_result`-blok — ikke
  // som `result` på sin tool_use. Live er de to foldet sammen af reduceren (så
  // `block.result` findes), men `content_json` fra serveren har dem som TO
  // blokke, og `result` står ikke på tool_use-blokken.
  //
  // Uden dette opslag døde spørgsmålet i det øjeblik streamen sluttede og den
  // gemte tur overtog: live-vejen virkede, den persisterede gjorde ikke. Målt
  // 15/10-2026 — Bjørn: «vises under streamen og forsvinder når streamen
  // stopper, det sker kun i mobilen». Desk slap for det, fordi SessionContext
  // bærer de foldede lokale blokke over i den server-bekræftede besked; mobilen
  // har ikke det lag og læser udelukkende de persisterede blokke.
  const fraResultat = new Map<string, unknown>()
  for (const block of blocks) {
    if (!block || block.type !== 'tool_result') continue
    const r = block as { tool_use_id?: string; content?: unknown; result?: unknown }
    if (!r.tool_use_id) continue
    fraResultat.set(r.tool_use_id, r.content ?? r.result)
  }
  let found: PauseAsk | null = null
  for (const block of blocks) {
    if (!block || block.type !== 'tool_use' || block.name !== 'pause_and_ask') continue
    const raa = block.result ?? (block.id ? fraResultat.get(block.id) : undefined)
    found = parseResult(raa) ?? found
  }
  return found
}

export function activePauseAsk(messages: ChatMessage[], live: ContentBlock[]): PauseAsk | null {
  let active: PauseAsk | null = null
  for (const message of messages) {
    if (message.role === 'user') active = null
    if (message.role === 'assistant') active = pauseIn(parseBlocks(message) ?? []) ?? active
  }
  return pauseIn(denseBlocks(live)) ?? active
}

/** The active question has one host above the composer, not another tool row. */
export function withoutPauseAsk<T extends {
  type: string; name?: string; id?: string; tool_use_id?: string
}>(blocks: T[] | null): T[] | null {
  if (!blocks) return null
  const complete = blocks.filter((block): block is T => block != null)
  const ids = new Set(complete
    .filter((block) => block.type === 'tool_use' && block.name === 'pause_and_ask')
    .map((block) => block.id)
    .filter((id): id is string => Boolean(id)))
  if (!ids.size && !complete.some((block) => block.type === 'tool_use' && block.name === 'pause_and_ask')) return complete
  return complete.filter((block) =>
    !(block.type === 'tool_use' && block.name === 'pause_and_ask') &&
    !(block.type === 'tool_result' && !!block.tool_use_id && ids.has(block.tool_use_id)))
}
