/**
 * Værktøjsarbejde som ÉN linje pr. runde — 1:1 med mobil-appen.
 *
 * Bjørn 8/9-2026: «tool result til at ligne dem i mobil appen … det skal lige
 * 1:1». Første forsøg byggede efter mobilens `ToolResultCard` — kort med
 * accent-kant og skygge. Den komponent bruges ikke i tråden. Et adb-billede af
 * telefonen viste hvad der faktisk står der: `InlineToolGroup`, en stille linje
 * mellem afsnittene.
 *
 *     fortælling
 *     </> Kørte agent.ts
 *     fortælling
 *     </> Kørte 2 ting  ›
 *
 * Denne fil er mobilens `toolSummary.ts` + `toolGroup.ts` porteret. Én forskel,
 * og den er strukturel: desk får `input` som et objekt, mobilen som en (evt.
 * ufuldstændig) JSON-streng. Derfor ingen regex-fiskeri her — der er intet at
 * fiske i.
 */
import type { ContentBlock } from './sseProtocol'
import { diffFraResultat, diffStat } from './diffStat'

type ToolUse = Extract<ContentBlock, { type: 'tool_use' }>

/** Verbum pr. værktøj: [nutid, datid]. Mobilens liste, plus desk'ens
 *  operator-varianter — samme værktøj, andet navn. */
const VERBS: Record<string, [string, string]> = {
  bash: ['Kører', 'Kørte'],
  read_file: ['Læser', 'Læste'],
  write_file: ['Skriver', 'Skrev'],
  edit_file: ['Redigerer', 'Redigerede'],
  multi_edit: ['Redigerer', 'Redigerede'],
  verify_file_contains: ['Verificerer', 'Verificerede'],
  list_dir: ['Ser i', 'Så i'],
  glob: ['Søger efter', 'Søgte efter'],
  grep: ['Søger efter', 'Søgte efter'],
  web_search: ['Søger på nettet efter', 'Søgte på nettet efter'],
  web_fetch: ['Henter', 'Hentede'],
  memory_search: ['Søger i hukommelsen efter', 'Søgte i hukommelsen efter'],
  memory_write: ['Husker', 'Huskede'],
}

/** Argument-nøgler der plejer at bære emnet, i prioriteret rækkefølge. */
const SUBJECT_KEYS = [
  'path', 'file_path', 'filepath', 'file', 'target', 'target_path',
  'command', 'cmd', 'query', 'q', 'pattern', 'text', 'name',
]

/** `operator_read_file` og `read_file` er samme handling for læseren. */
function grundnavn(name: string): string {
  return (name || '').trim().replace(/^operator_/, '')
}

/** Kun filnavnet — en fuld sti fylder linjen uden at sige mere. */
function shorten(value: string): string {
  const v = value.trim().replace(/\s+/g, ' ')
  if (!v) return ''
  if (v.includes('/') && !v.includes(' ')) {
    const last = v.split('/').filter(Boolean).pop()
    if (last) return last
  }
  return v.length > 48 ? `${v.slice(0, 47)}…` : v
}

export function subjectFromInput(input: Record<string, unknown> | undefined): string {
  if (!input) return ''
  for (const key of SUBJECT_KEYS) {
    const v = input[key]
    if (typeof v === 'string' && v.trim()) return shorten(v)
  }
  return ''
}

/** «Kørte agent.ts» frem for «Kørte bash». Kan intet emne findes, falder vi
 *  tilbage på værktøjsnavnet frem for at finde på noget. */
export function describeTool(name: string, input: Record<string, unknown> | undefined, running: boolean): string {
  const tool = grundnavn(name) || 'værktøj'
  const [now, past] = VERBS[tool] ?? ['Kører', 'Kørte']
  const verb = running ? now : past
  const subject = subjectFromInput(input)
  if (subject) return `${verb} ${subject}${running ? '…' : ''}`
  return `${verb} ${tool}${running ? '…' : ''}`
}

const PLURAL: Record<string, [string, string]> = {
  edit_file: ['Redigerer', 'Redigerede'],
  multi_edit: ['Redigerer', 'Redigerede'],
  write_file: ['Skriver', 'Skrev'],
  read_file: ['Læser', 'Læste'],
  verify_file_contains: ['Verificerer', 'Verificerede'],
  bash: ['Kører', 'Kørte'],
}

const UNIT: Record<string, [string, string]> = {
  edit_file: ['fil', 'filer'],
  multi_edit: ['fil', 'filer'],
  write_file: ['fil', 'filer'],
  read_file: ['fil', 'filer'],
  verify_file_contains: ['tjek', 'tjek'],
  bash: ['kommando', 'kommandoer'],
}

/**
 * Læs en optælling ud af et resultat. Vi gætter ikke: findes tallet ikke,
 * falder linjen tilbage på antal kald.
 */
export function countFromResult(content: string | undefined): number | undefined {
  const s = content || ''
  const m =
    /(\d+)\s+(?:filer|files|linjer|lines|matches|træffere|resultater)/i.exec(s) ??
    /(?:changed|ændrede|modified)\s+(\d+)/i.exec(s)
  if (!m) return undefined
  const n = Number(m[1])
  return Number.isFinite(n) && n > 0 ? n : undefined
}

/**
 * Én linje for hele runden.
 *
 * Ét kald → dets egen beskrivelse. Flere ens → «Redigerede 3 filer». Flere
 * forskellige → «Kørte 5 værktøjer». Tallet er antal kald, med mindre
 * resultaterne selv har talt noget op — så bruges den sum, fordi «Ændrede 16
 * filer» siger mere end «Kørte 3 værktøjer».
 */
export function summarizeRound(tools: ToolUse[]): string {
  if (tools.length === 0) return ''
  const running = tools.some((t) => (t.status ?? 'running') === 'running')
  if (tools.length === 1) {
    const t = tools[0]!
    return describeTool(t.name, t.input, (t.status ?? 'running') === 'running')
  }

  const navne = new Set(tools.map((t) => grundnavn(t.name)))
  const counted = tools.reduce((sum, t) => sum + (countFromResult(t.result) ?? 0), 0)

  if (navne.size === 1) {
    const tool = grundnavn(tools[0]!.name)
    const [now, past] = PLURAL[tool] ?? ['Kører', 'Kørte']
    const [one, many] = UNIT[tool] ?? ['ting', 'ting']
    const n = counted > 0 ? counted : tools.length
    return `${running ? now : past} ${n} ${n === 1 ? one : many}${running ? '…' : ''}`
  }

  return blandetRunde(tools, running)
}

/** «en» frem for «1»: linjen er en sætning, ikke en tabel. */
function antalOrd(n: number): string {
  return n === 1 ? 'en' : String(n)
}

/**
 * Led pr. værktøj, i den rækkefølge kaldene skete. 1:1 med mobilens
 * `toolGroup.ts` — to flader der siger forskelligt om den samme tur er værre
 * end én dårlig linje.
 *
 * Den gamle linje sagde «Kørte 5 værktøjer»: en optælling af hvor mange
 * funktionskald der var, hvilket ikke interesserer nogen. Hvad der SKETE stod
 * der ikke. Nu står der «Kørte en kommando og redigerede 3 filer».
 *
 * Rækkefølgen er kaldenes egen — en sortering ville bytte om på årsag og
 * virkning i en linje der læses som en fortælling om turen. Et ukendt værktøj
 * får sit eget led frem for at blive tiet ihjel.
 */
function blandetRunde(tools: ToolUse[], running: boolean): string {
  const orden: string[] = []
  const antal = new Map<string, number>()
  for (const t of tools) {
    const g = grundnavn(t.name)
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
 * Rundens samlede linjeændringer — 1:1 med mobilens `summerDiff`.
 *
 * Gruppen er FOLDET som standard. Desk viste kun tallene inde i hvert kort, så
 * de var usynlige det meste af tiden; mobilen summer dem op i selve linjen.
 *
 * Samme kilde som `ToolCard`: serverens MÅLTE tal først, klientens beregning
 * ud fra argumenterne som faldback mens kaldet stadig kører. `null` for en
 * runde der kun læste — «ingenting at vise» er en anden besked end «nul».
 */
export function summerDiff(tools: ToolUse[]): { add: number; del: number } | null {
  let add = 0
  let del = 0
  let nogen = false
  for (const t of tools) {
    let args: Record<string, unknown> = t.input && Object.keys(t.input).length ? t.input : {}
    if (!Object.keys(args).length && t.partialJson) {
      try { args = JSON.parse(t.partialJson) } catch { args = {} }
    }
    const ds = diffFraResultat(t.result) ?? diffStat(t.name, args)
    if (!ds) continue
    add += ds.add
    del += ds.del
    nogen = true
  }
  return nogen ? { add, del } : null
}
