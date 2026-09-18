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
    if (!PLURAL[tool]) return brugte(items.length, running) + (running ? '…' : '')
    const [now, past] = PLURAL[tool]!
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
 * Led pr. slags værktøj — Claude Desktops regel (`Cf`, læst i deres kilde
 * 19/9-2026), 1:1 i desk og mobil:
 *
 * - kendte slags får hver sit led: «Kørte 2 kommandoer»
 * - alle ukendte samles i ÉT led: «brugte et værktøj» (deres «used a tool»)
 * - sorteret efter antal, højst tre led, adskilt af komma
 * - er der flere end tre, vises to plus «og N værktøjer mere»
 *
 * Før stod der «Kørte 2 kommandoer og kørte en ting» (Bjørn 19/9-2026: «Kørte
 * en ting?»). Den gamle regel om kaldenes rækkefølge er droppet: forlægget
 * sorterer, og «1:1» betyder 1:1.
 */
function blandetRunde(items: ToolItem[], running: boolean): string {
  const orden: string[] = []
  const antal = new Map<string, number>()
  let ukendte = 0
  for (const i of items) {
    const g = grundnavn(i.tool)
    if (!PLURAL[g]) { ukendte++; continue }
    if (!antal.has(g)) orden.push(g)
    antal.set(g, (antal.get(g) ?? 0) + 1)
  }

  const grupper: { tekst: string; n: number }[] = orden.map((tool) => {
    const n = antal.get(tool) ?? 0
    const [nu, da] = PLURAL[tool]!
    const [en, flere] = UNIT[tool] ?? ['ting', 'ting']
    return { tekst: `${running ? nu : da} ${antalOrd(n)} ${n === 1 ? en : flere}`, n }
  })
  // Ukendte værktøjer samles i ÉT led, som Claude Desktop («used a tool»),
  // frem for «kørte en ting» pr. navn.
  if (ukendte > 0) grupper.push({ tekst: brugte(ukendte, running), n: ukendte })
  // Claude Desktop sorterer efter antal (stabilt) og viser højst tre led.
  grupper.sort((a, b) => b.n - a.n)
  const vis = grupper.length > 3 ? 2 : 3
  const led = grupper.slice(0, vis).map((g, idx) => (idx === 0 ? g.tekst : g.tekst.charAt(0).toLowerCase() + g.tekst.slice(1)))
  const rest = grupper.slice(vis).reduce((s, g) => s + g.n, 0)
  const hale = running ? '…' : ''
  if (rest > 0) return `${led.join(', ')} og ${rest} værktøjer mere${hale}`
  return led.join(', ') + hale
}

/** «Brugte et værktøj» / «Brugte 3 værktøjer» — Claude Desktops `Used a tool`. */
function brugte(n: number, running: boolean): string {
  return `${running ? 'Bruger' : 'Brugte'} ${n === 1 ? 'et værktøj' : `${n} værktøjer`}`
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
