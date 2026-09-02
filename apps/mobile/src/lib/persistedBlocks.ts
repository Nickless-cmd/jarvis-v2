import type { ChatMessage } from './types'

/**
 * Serverens strukturerede blokke for en gemt assistent-tur.
 *
 * `content` er hele turen klasket sammen til én streng: værktøjerne først og
 * alle synteser smeltet til én blok. `content_json` har den ÆGTE rækkefølge —
 * text → tool_use → tool_result → text → … — som den blev til.
 *
 * Verificeret på en rigtig tur efter server-rettelsen 2026-09-02:
 *
 *     0 text «Vi starter med skridt 1 — læser fri diskplads…»
 *     1 tool_use bash        2 tool_result
 *     3 text «1) Fri diskplads: 20G fri…»
 *     4 tool_use bash        5 tool_result
 *     6 text «2) Værtsnavn: Jarvis…»
 *
 * Uden dette led ville app'en stadig vise den gamle klump — serveren havde
 * ret, men skærmen ville ikke vise det.
 */
export interface PersistedBlock {
  type: 'text' | 'tool_use' | 'tool_result' | 'progress' | string
  text?: string
  name?: string
  input?: Record<string, unknown>
  tool_use_id?: string
  content?: string
  status?: string
}

/**
 * Parse blokkene. Ugyldig form → null, så vi falder tilbage på `content`.
 *
 * API'et leverer feltet som et FÆRDIGPARSET array — ikke som en JSON-streng.
 * Første forsøg antog en streng og kaldte .trim(), hvilket væltede hele
 * MessageList med «undefined is not a function». Begge former håndteres nu,
 * for en type der kommer over nettet er en påstand, ikke en garanti.
 */
export function parseBlocks(message: ChatMessage): PersistedBlock[] | null {
  const raw = message.content_json
  if (!raw) return null
  let parsed: unknown = raw
  if (typeof raw === 'string') {
    const s = raw.trim()
    if (!s) return null
    try {
      parsed = JSON.parse(s)
    } catch {
      return null
    }
  }
  if (!Array.isArray(parsed)) return null
  const blocks = parsed.filter((b) => b && typeof b === 'object') as PersistedBlock[]
  return blocks.length ? blocks : null
}

/**
 * Bærer blokkene en rækkefølge vi ikke allerede har fra `content`?
 *
 * Kun hvis der er værktøjer OG mindst ét tekststykke. Er der bare én
 * tekstblok og ingen værktøjer, siger blokkene det samme som `content`, og så
 * er det billigere og sikrere at rendere den kendte vej.
 */
export function hasOrdering(blocks: PersistedBlock[] | null): boolean {
  if (!blocks) return false
  const tools = blocks.filter((b) => b.type === 'tool_use').length
  const texts = blocks.filter((b) => b.type === 'text' && (b.text ?? '').trim()).length
  return tools > 0 && texts > 0
}

/** Progress-sporet er et separat, fladt spor (spec §5) — ikke en del af tråden. */
export function threadBlocks(blocks: PersistedBlock[]): PersistedBlock[] {
  return blocks.filter((b) => b.type !== 'progress')
}
