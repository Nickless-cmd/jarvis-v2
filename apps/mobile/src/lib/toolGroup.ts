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
  /**
   * Linjer ændret af DETTE kald. null når værktøjet ikke redigerer noget.
   *
   * Regnet af klienten ud af kaldets egne argumenter — se `toolDiff`. Det er
   * ikke det samme tal som badgen over komponisten: dén måler HELE
   * arbejdstræet, denne måler ét kald.
   */
  diff?: { tilfoejet: number; fjernet: number } | null
  running: boolean
  /** Værktøjets navn — bruges til at afgøre om runden er ensartet. */
  tool: string
  /**
   * Kaldets id, når streamen har givet et.
   *
   * Bruges KUN til at slå rundens etiket op: serveren sender den med de
   * `tool_use_ids` den opsummerer, og et opslag på id hæfter den på de rigtige
   * kald frem for på en plads i tråden.
   */
  id?: string
  /** Antal ting kaldet rørte, hvis resultatet siger det (fx «16 filer»). */
  count?: number
}

import { grundnavn } from './toolSummary'

/** Bøjninger for de sammenfattende linjer. */
const PLURAL: Record<string, [string, string]> = {
  edit_file: ['Redigerer', 'Redigerede'],
  multi_edit: ['Redigerer', 'Redigerede'],
  write_file: ['Skriver', 'Skrev'],
  read_file: ['Læser', 'Læste'],
  verify_file_contains: ['Verificerer', 'Verificerede'],
  bash: ['Kører', 'Kørte']
}

const UNIT: Record<string, [string, string]> = {
  edit_file: ['fil', 'filer'],
  multi_edit: ['fil', 'filer'],
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

  const tools = new Set(items.map((i) => grundnavn(i.tool)))
  const counted = items.reduce((sum, i) => sum + (i.count ?? 0), 0)

  if (tools.size === 1) {
    const tool = grundnavn(items[0]!.tool)
    const [now, past] = PLURAL[tool] ?? ['Kører', 'Kørte']
    const [one, many] = UNIT[tool] ?? ['ting', 'ting']
    const n = counted > 0 ? counted : items.length
    return `${running ? now : past} ${n} ${n === 1 ? one : many}${running ? '…' : ''}`
  }

  return blandetRunde(items, running)
}

/** «en» frem for «1»: linjen er en sætning, ikke en tabel. */
function antalOrd(n: number): string {
  return n === 1 ? 'en' : String(n)
}

/**
 * Led pr. værktøj, i den rækkefølge kaldene skete.
 *
 * Den gamle linje sagde «Kørte 5 værktøjer» — en optælling af noget der ikke
 * interesserer nogen: hvor mange funktionskald der var. Hvad der SKETE stod
 * der ikke. Nu står der «Kørte en kommando, redigerede 3 filer».
 *
 * Rækkefølgen er kaldenes egen. En sortering (fx efter antal) ville bytte om
 * på årsag og virkning i en linje der læses som en fortælling om turen.
 *
 * Et ukendt værktøj får sit eget led frem for at blive tiet ihjel — ellers
 * ville et nyt værktøj forsvinde ud af sætningen, og linjen ville lyve om
 * hvad turen gjorde.
 */
function blandetRunde(items: ToolItem[], running: boolean): string {
  const orden: string[] = []
  const antal = new Map<string, number>()
  for (const i of items) {
    // `operator_bash` og `bash` er samme handling — ét led, ikke «og kørte en ting».
    const g = grundnavn(i.tool)
    if (!antal.has(g)) orden.push(g)
    antal.set(g, (antal.get(g) ?? 0) + 1)
  }

  const led = orden.map((tool, idx) => {
    const n = antal.get(tool) ?? 0
    const [nu, da] = PLURAL[tool] ?? ['Kører', 'Kørte']
    const [en, flere] = UNIT[tool] ?? ['ting', 'ting']
    const verbum = running ? nu : da
    // Kun det første led bærer stort begyndelsesbogstav — resten er led i
    // samme sætning, ikke selvstændige overskrifter.
    const v = idx === 0 ? verbum : verbum.charAt(0).toLowerCase() + verbum.slice(1)
    return `${v} ${antalOrd(n)} ${n === 1 ? en : flere}`
  })

  const hale = running ? '…' : ''
  if (led.length === 1) return led[0]! + hale
  return `${led.slice(0, -1).join(', ')} og ${led[led.length - 1]}${hale}`
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

/**
 * Gruppens samlede linjeændringer — eller null når ingen af kaldene ændrede noget.
 *
 * `null` frem for `{0,0}`: en runde der kun læste og søgte skal stå UDEN tal,
 * ikke med to nuller. Samme regel som `toolDiff` selv, og som ringen og
 * upload-andelen: «ingenting at vise» og «nul» er to forskellige beskeder.
 */
export function summerDiff(items: ToolItem[]): { tilfoejet: number; fjernet: number } | null {
  let t = 0
  let f = 0
  let nogen = false
  for (const i of items) {
    if (!i.diff) continue
    t += i.diff.tilfoejet
    f += i.diff.fjernet
    nogen = true
  }
  return nogen ? { tilfoejet: t, fjernet: f } : null
}
