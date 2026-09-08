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

  const n = tools.length
  return `${running ? 'Kører' : 'Kørte'} ${n} værktøjer${running ? '…' : ''}`
}
