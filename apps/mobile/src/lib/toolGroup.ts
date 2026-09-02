/**
 * Værktøjsarbejde grupperes PR. RUNDE — ikke pr. kald.
 *
 * Sådan gør Codex-appen det (målt i tråden 2026-09-02): fortælling → ÉN
 * sammenfoldet linje → fortælling → ÉN linje. Ikke ti linjer i træk.
 *
 *     Outboxen er nu testet mod den afgørende crash-sekvens: …
 *     </> Redigerede test_push_dispatcher.py  ›
 *     Task 6 lukker to forskellige risici: …
 *     </> Ændrede 16 filer  ›
 *
 * Uden gruppering stablede vi fire «Kører verify_file_contains…» oven på
 * hinanden — samme information fire gange, og tråden mistede sin ro.
 * Linjen ændrer sig UNDER runden og kan foldes ud til de enkelte kald.
 */

export interface ToolItem {
  /** Beskrivelsen af det enkelte kald: «Læste USER.md». */
  label: string
  running: boolean
  /** Værktøjets navn — bruges til at afgøre om runden er ensartet. */
  tool: string
  /** Antal ting kaldet rørte, hvis resultatet siger det (fx «16 filer»). */
  count?: number
}

/** Bøjninger for de sammenfattende linjer. */
const PLURAL: Record<string, [string, string]> = {
  edit_file: ['Redigerer', 'Redigerede'],
  write_file: ['Skriver', 'Skrev'],
  read_file: ['Læser', 'Læste'],
  verify_file_contains: ['Verificerer', 'Verificerede'],
  bash: ['Kører', 'Kørte']
}

const UNIT: Record<string, [string, string]> = {
  edit_file: ['fil', 'filer'],
  write_file: ['fil', 'filer'],
  read_file: ['fil', 'filer'],
  verify_file_contains: ['tjek', 'tjek'],
  bash: ['kommando', 'kommandoer']
}

/**
 * Én linje for hele runden.
 *
 * Ét kald → dets egen beskrivelse, uændret. Flere ens → «Redigerede 3 filer».
 * Flere forskellige → «Kørte 5 værktøjer». Tallet er ANTAL KALD, med mindre
 * resultaterne selv har talt noget op (count) — så bruges den sum, fordi
 * «Ændrede 16 filer» siger mere end «Kørte 3 værktøjer».
 */
export function summarizeRound(items: ToolItem[]): string {
  if (items.length === 0) return ''
  const running = items.some((i) => i.running)
  if (items.length === 1) return items[0]!.label

  const tools = new Set(items.map((i) => i.tool))
  const counted = items.reduce((sum, i) => sum + (i.count ?? 0), 0)

  if (tools.size === 1) {
    const tool = items[0]!.tool
    const [now, past] = PLURAL[tool] ?? ['Kører', 'Kørte']
    const [one, many] = UNIT[tool] ?? ['ting', 'ting']
    const n = counted > 0 ? counted : items.length
    return `${running ? now : past} ${n} ${n === 1 ? one : many}${running ? '…' : ''}`
  }

  const n = items.length
  return `${running ? 'Kører' : 'Kørte'} ${n} værktøjer${running ? '…' : ''}`
}

/**
 * Læs en optælling ud af et værktøjs-resultat.
 *
 * Codex skriver «Ændrede 16 filer» fordi resultatet SIGER 16. Vi gætter ikke:
 * findes tallet ikke, returneres undefined, og linjen falder tilbage på
 * antal kald.
 */
export function countFromResult(content: string): number | undefined {
  const s = content || ''
  const m =
    /(\d+)\s+(?:filer|files|linjer|lines|matches|træffere|resultater)/i.exec(s) ??
    /(?:changed|ændrede|modified)\s+(\d+)/i.exec(s)
  if (!m) return undefined
  const n = Number(m[1])
  return Number.isFinite(n) && n > 0 ? n : undefined
}
