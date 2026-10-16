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

/**
 * Find det FØRSTE komplette JSON-objekt i en streng — uanset hvad der står bagefter.
 *
 * Målt 16/10-2026, og det er den ÆGTE rod-årsag til at kortet døde: serveren
 * hægter en nudge på det SIDSTE tool-resultat i runden
 * (`core/services/visible_followup_results.py:70-79`,
 * `content=last.content.rstrip() + _NUDGE`), og den nudge ender inde i den
 * PERSISTEREDE `tool_result.content`:
 *
 *   { "kind": "pause_and_ask", … }
 *
 *   (⟳ Før du fortsætter: skriv én kort sætning …)
 *
 * `JSON.parse` på hele strengen fejler derfor med «Unexpected non-whitespace
 * character after JSON» — og `parseResult` returnerede null, så kortet
 * forsvandt i det øjeblik streamen sluttede og den gemte tur overtog.
 *
 * Målt på ALLE 13 pause_and_ask-resultater i Bjørns samtale: alle 13 var
 * ugyldig JSON af præcis denne grund. Desk slap, fordi SessionContext bærer de
 * foldede lokale blokke over — mobilen læser udelukkende de persisterede.
 *
 * Desk har samme robusthed i `agentKald.ts`: «rent JSON.parse fejler — vi leder
 * efter selve feltet». Her leder vi efter det første balancerede objekt.
 */
function foersteJsonObjekt(tekst: string): unknown {
  const start = tekst.indexOf('{')
  if (start < 0) return null
  let dybde = 0
  let iStreng = false
  let escape = false
  for (let i = start; i < tekst.length; i++) {
    const c = tekst[i]
    if (escape) { escape = false; continue }
    if (c === '\\') { if (iStreng) escape = true; continue }
    if (c === '"') { iStreng = !iStreng; continue }
    if (iStreng) continue
    if (c === '{') dybde++
    else if (c === '}') {
      dybde--
      if (dybde === 0) {
        try { return JSON.parse(tekst.slice(start, i + 1)) } catch { return null }
      }
    }
  }
  return null
}

function parseResult(result: unknown): PauseAsk | null {
  let data = result
  if (typeof data === 'string') {
    const tekst = data
    if (!tekst.includes('pause_and_ask')) return null
    try {
      data = JSON.parse(tekst)
    } catch {
      data = foersteJsonObjekt(tekst)
    }
    if (data === null || data === undefined) return null
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

/**
 * Er dette kaldet `pause_and_ask`?
 *
 * Navnet kan stå på TO steder, og det er hele grunden til at kortet døde to
 * gange i træk. Er værktøjet ikke loadet i runden, går kaldet gennem
 * TRANSPORTEN `call_loaded_tool`, og det rigtige navn ligger i `input.navn`:
 *
 *   {"type": "tool_use", "name": "call_loaded_tool",
 *    "input": {"navn": "pause_and_ask", "argumenter": {…}}}
 *
 * Den GEMTE tur beholder transport-navnet — live får blokken efter udpakning.
 * Målt 16/10-2026 mod DB'en på en rigtig tur: `name` var `call_loaded_tool`.
 * Det første fix ledte efter `pause_and_ask` på `block.name` og sprang den
 * derfor over, præcis som den gamle kode sprang den over på `block.result`.
 */
function erPauseAsk(block: { type?: string; name?: string; input?: unknown } | null | undefined): boolean {
  if (!block || block.type !== 'tool_use') return false
  if (block.name === 'pause_and_ask') return true
  if (block.name !== 'call_loaded_tool') return false
  const input = block.input
  if (!input || typeof input !== 'object') return false
  return (input as { navn?: unknown }).navn === 'pause_and_ask'
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
    if (!erPauseAsk(block)) continue
    // `erPauseAsk` er et ja/nej, ikke en type-guard — union-typen kender derfor
    // ikke felterne. Før indsnævrede `block.name !== 'pause_and_ask'` dem; det
    // tjek ligger nu i hjælperen, så felterne læses eksplicit her.
    const t = block as { result?: unknown; id?: string }
    const raa = t.result ?? (t.id ? fraResultat.get(t.id) : undefined)
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
  type: string; name?: string; id?: string; tool_use_id?: string; input?: unknown
}>(blocks: T[] | null): T[] | null {
  if (!blocks) return null
  const complete = blocks.filter((block): block is T => block != null)
  const ids = new Set(complete
    .filter(erPauseAsk)
    .map((block) => block.id)
    .filter((id): id is string => Boolean(id)))
  if (!ids.size && !complete.some(erPauseAsk)) return complete
  return complete.filter((block) =>
    !erPauseAsk(block) &&
    !(block.type === 'tool_result' && !!block.tool_use_id && ids.has(block.tool_use_id)))
}
