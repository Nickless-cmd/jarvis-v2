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
    context: String(d.context ?? '').trim().slice(0, 400),
    urgency: u === 'low' || u === 'high' ? u : 'normal',
  }
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
