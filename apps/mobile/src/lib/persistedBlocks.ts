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
  type: 'text' | 'tool_use' | 'tool_result' | 'progress' | 'thinking' | 'image' | 'file' | string
  text?: string
  name?: string
  input?: Record<string, unknown>
  /**
   * tool_use: kaldets id — det samme serveren bruger i `tool_use_ids` på en
   * runde-etiket.
   *
   * Feltet fandtes i dataen hele tiden; typen kendte det bare ikke, og derfor
   * blev det aldrig båret videre. Uden det kan etiketten ikke slås op på en
   * gemt tur, og overskriften forsvandt i det øjeblik streamen sluttede.
   */
  id?: string
  /** tool_use_summary: rundens sætning (Claude Desktops form, 19/9-2026). */
  summary?: string
  /** tool_use_summary: de kald sætningen dækker. */
  preceding_tool_use_ids?: string[]
  /** tool_use_summary: tænke-resuméet for gruppen (visningen «thinking»). */
  thinking_summary?: string
  /**
   * tool_use: værktøjets resultat, når serveren har lagt det ved.
   *
   * Bærer `linjer_tilfoejet`/`linjer_fjernet` når der er målt. Er ofte `null`,
   * og så regnes tallene af argumenterne i stedet.
   */
  result?: unknown
  tool_use_id?: string
  content?: string
  status?: string
  /** thinking: hvor længe han tænkte. Mangler den, blev der ikke målt. */
  seconds?: number
  /** image/file: reference, ALDRIG data — hentning går over det user-scopede endpoint. */
  attachment_id?: string
  /**
   * file: UDGIVET fils egen adresse.
   *
   * `publish_file` lægger filen i `files/` og skriver sin URL i blokken — den
   * bærer derfor INTET `attachment_id`. Uden dette felt kunne filteret nedenfor
   * ikke skelne «en halv reference» fra «en udgivet fil», og alt Jarvis selv
   * lagde ud faldt bort før skærmen så det. Målt 15/9-2026: blokken lå i
   * beskeden hele tiden, den nåede bare aldrig frem.
   */
  url?: string
  /** file: hvor filen kommer fra — `published` = Jarvis' egen udgivelse. */
  kilde?: string
  filename?: string
  mime_type?: string
  size_bytes?: number
}

/** Turens tænkning, hvis serveren målte den. */
export function thinkingBlock(blocks: PersistedBlock[] | null): PersistedBlock | null {
  if (!blocks) return null
  return blocks.find((b) => b.type === 'thinking') ?? null
}

/**
 * Vedhæftninger på en besked, i den rækkefølge de blev sendt.
 *
 * Der er TO slags referencer, og de hentes hver for sig (se `blokUrl`):
 *
 *   - `attachment_id` — en upload eller et genereret billede, hentet over det
 *     user-scopede `/attachments/...`
 *   - `url` — en fil Jarvis selv har udgivet med `publish_file`, hentet over
 *     `/files/{navn}`
 *
 * Før krævede filteret et `attachment_id`, og en udgivet fil — som aldrig har
 * et — faldt ud allerede her. Blokken var i beskeden hele tiden; den nåede
 * bare ikke skærmen. `MessageAttachments` kunne hele tiden vise den.
 */
export function attachmentBlocks(blocks: PersistedBlock[] | null): PersistedBlock[] {
  if (!blocks) return []
  return blocks.filter((b) => {
    if (b.type !== 'image' && b.type !== 'file') return false
    return !!((b.attachment_id ?? '').trim() || (b.url ?? '').trim())
  })
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
  // `skill_surface` tæller som et kald: uden den gik en tur hvor runtimen
  // lagde en skill i prompten, men Jarvis ikke kaldte noget, den gamle
  // tekst-vej — og skill-linjen nåede aldrig skærmen (19/9-2026).
  const tools = blocks.filter((b) => b.type === 'tool_use' || b.type === 'skill_surface').length
  const texts = blocks.filter((b) => b.type === 'text' && (b.text ?? '').trim()).length
  return tools > 0 && texts > 0
}

/**
 * Progress-sporet er et separat, fladt spor (spec §5) — ikke en del af tråden.
 * Vedhæftninger filtreres også fra; de renderes over boblen.
 *
 * ## Hvorfor tænkning nu BLIVER i rækkefølgen
 *
 * Før blev den filtreret fra, fordi designet var «én foldet tænke-linje over
 * turen». Det holdt kun så længe en tur tænkte én gang. Jarvis tænker mellem
 * hvert værktøjskald, og resultatet var at kun den FØRSTE tanke overlevede:
 * `thinkingBlock` tager `.find()`, og de øvrige blev filtreret bort her.
 *
 * Bjørn 12/9-2026: «det er kun den første tænkte der bliver i chatview, dem
 * der er under forsvinder efter streamen». Præcis dét — og kun efter streamen,
 * fordi den LEVENDE visning bygger rækkerne af blokkene i rækkefølge og derfor
 * altid har vist dem alle. De to visninger var uenige om samme tur.
 */
export function threadBlocks(blocks: PersistedBlock[]): PersistedBlock[] {
  return blocks.filter(
    (b) => b.type !== 'progress' && b.type !== 'image' && b.type !== 'file'
  )
}


/**
 * Rundernes GEMTE sætninger, slået op på hvert kald de dækker.
 *
 * Før blev sætningen kun streamet, og i det øjeblik turen var gemt, var den
 * væk. Nu gemmer serveren den som en `tool_use_summary`-blok — Claude
 * Desktops egen form, `{summary, preceding_tool_use_ids}` — og den slås op på
 * samme nøgle som den live: kaldets id.
 */
export function gemteEtiketter(messages: ChatMessage[]): Record<string, string> {
  const ud: Record<string, string> = {}
  for (const m of messages) {
    const blokke = parseBlocks(m)
    if (!blokke) continue
    for (const b of blokke) {
      if (b.type !== 'tool_use_summary' || typeof b.summary !== 'string' || !b.summary.trim()) continue
      for (const id of Array.isArray(b.preceding_tool_use_ids) ? b.preceding_tool_use_ids : []) {
        ud[String(id)] = b.summary
      }
    }
  }
  return ud
}


/** Gemte tænke-resuméer slået op på hvert kald de dækker (visningen «thinking»). */
export function gemteResumeer(messages: ChatMessage[]): Record<string, string> {
  const ud: Record<string, string> = {}
  for (const m of messages) {
    const blokke = parseBlocks(m)
    if (!blokke) continue
    for (const b of blokke) {
      if (b.type !== 'tool_use_summary' || typeof b.thinking_summary !== 'string' || !b.thinking_summary.trim()) continue
      for (const id of Array.isArray(b.preceding_tool_use_ids) ? b.preceding_tool_use_ids : []) {
        ud[String(id)] = b.thinking_summary
      }
    }
  }
  return ud
}
