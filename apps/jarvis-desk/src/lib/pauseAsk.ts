/** pause_and_ask — Jarvis standser midt i et run og spørger.
 *
 *  Serveren returnerer {kind:"pause_and_ask", question, options[], …}, men
 *  tool-resultater blev eksternaliseret til disk 5/9-2026 og kommer tilbage
 *  som JSON-*strenge*. Desk viste dem derfor som rå JSON — spørgsmålet nåede
 *  aldrig frem som et spørgsmål. Samme fejl blev rettet i apps/ui (033f2ece8);
 *  desk havde den ikke, den havde slet ikke funktionen.
 */

export type PauseAsk = {
  question: string
  options: string[]
  allowMultiple?: boolean
  context: string
  urgency: 'low' | 'normal' | 'high'
}

/** Konservativ: kun strenge der bærer markøren forsøges parset, så almindeligt
 *  tool-output aldrig ender som "[object Object]". */
export function parsePauseAsk(result: unknown): PauseAsk | null {
  let o: unknown = result
  if (typeof o === 'string') {
    if (!o.includes('pause_and_ask')) return null
    try { o = JSON.parse(o) } catch { return null }
  }
  if (!o || typeof o !== 'object') return null
  const d = o as Record<string, unknown>
  if (d.kind !== 'pause_and_ask') return null

  const question = String(d.question ?? '').trim()
  if (!question) return null

  const raw = Array.isArray(d.options) ? d.options : []
  const options = raw
    .map((x) => String(x).trim())
    .filter((s) => s.length > 0 && s.length <= 120)
    .slice(0, 6)          // samme loft som serveren

  const u = String(d.urgency ?? 'normal')
  return {
    question,
    options,
    allowMultiple: d.allow_multiple === true,
    context: String(d.context ?? '').trim().slice(0, 400),
    urgency: u === 'low' || u === 'high' ? u : 'normal',
  }
}

export function pauseAskIn(blocks: ContentBlock[]): PauseAsk | null {
  let found: PauseAsk | null = null
  for (const block of blocks) {
    if (block?.type !== 'tool_use' || block.name !== 'pause_and_ask') continue
    found = parsePauseAsk(block.result) ?? found
  }
  return found
}

/** Bevar tool-blokken i session-state, men skjul den fra transcript-renderen når
 *  viewet hoster det aktive spørgsmål over composeren. Returnerer samme array,
 *  hvis der intet er at filtrere, så afsluttede MessageRows fortsat kan memoize. */
export function withoutPauseAsk(blocks: ContentBlock[]): ContentBlock[] {
  const hasPause = blocks.some((block) => block?.type === 'tool_use' && block.name === 'pause_and_ask')
  return hasPause
    ? blocks.filter((block) => block?.type !== 'tool_use' || block.name !== 'pause_and_ask')
    : blocks
}

/** Svaret skal blive den NÆSTE bruger-besked. Kortet sidder dybt i
 *  BlocksRenderer og deler ikke provider-gren med ChatView, så samme
 *  modul-pub/sub som coworkZone. */
type Lytter = (svar: string) => void
const lyttere = new Set<Lytter>()

export function emitPauseSvar(svar: string): void {
  for (const l of lyttere) { try { l(svar) } catch { /* en lytter må ikke vælte de andre */ } }
}

export function onPauseSvar(l: Lytter): () => void {
  lyttere.add(l)
  return () => { lyttere.delete(l) }
}

/** Spørgsmålets identitet — samme nøgle som kortet selv nulstiller på. */
export function pauseIdentitet(ask: PauseAsk): string {
  return JSON.stringify([ask.question, ask.options, ask.allowMultiple])
}

/** Lukkede spørgsmål. Ligger på modul-niveau og ikke i React-state, fordi
 *  kortet monteres i BÅDE ChatView og CodeView: et view-skift unmounter den
 *  ene og mounter den anden, og et lokalt flag ville vække spørgsmålet igen.
 *
 *  15/11-2026 (Bjørn): «pause_and_ask forsvinder ikk når man trykker send».
 *  Blokken ligger varigt i stream-state — den forsvinder først når run'et
 *  ryddes — så kortet blev stående som «Svar sendt» længe efter svaret var
 *  givet. Nu husker vi hvilke spørgsmål der er besvaret eller afvist. */
const lukkede = new Set<string>()
let version = 0
const abonnenter = new Set<() => void>()

export function erPauseLukket(ident: string): boolean {
  return lukkede.has(ident)
}

export function lukPause(ident: string): void {
  if (!ident || lukkede.has(ident)) return
  lukkede.add(ident)
  version += 1
  for (const a of abonnenter) { try { a() } catch { /* én abonnent må ikke vælte de andre */ } }
}

export function pauseLukketSnapshot(): number {
  return version
}

export function abonnérPauseLukket(l: () => void): () => void {
  abonnenter.add(l)
  return () => { abonnenter.delete(l) }
}

/** Krydset: brugeren vil ikke svare på spørgsmålet. Kortet lukkes, og et
 *  levende run får besked om at fortsætte — ellers ville det vente for evigt
 *  på et svar, og composeren ville låse (køen tømmes først når run'et slutter). */
type LukLytter = () => void
const lukLyttere = new Set<LukLytter>()

export function emitPauseLuk(): void {
  for (const l of lukLyttere) { try { l() } catch { /* en lytter må ikke vælte de andre */ } }
}

export function onPauseLuk(l: LukLytter): () => void {
  lukLyttere.add(l)
  return () => { lukLyttere.delete(l) }
}
import type { ContentBlock } from './sseProtocol'
