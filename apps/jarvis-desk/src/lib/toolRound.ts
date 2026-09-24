/**
 * Værktøjsarbejde som én linje pr. runde, bygget på mobil-appens model.
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
 * Denne fil begyndte som en port af mobilens `toolSummary.ts` + `toolGroup.ts`.
 * Desk får `input` som et objekt og bruger titler og bekræftede resultater til
 * at beskrive visse handlinger mere præcist.
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
  operator_multi_edit: ['Redigerer', 'Redigerede'],
  verify_file_contains: ['Verificerer', 'Verificerede'],
  operator_list_dir: ['Ser i', 'Så i'],
  operator_glob: ['Søger efter', 'Søgte efter'],
  operator_grep: ['Søger efter', 'Søgte efter'],
  web_search: ['Søger på nettet efter', 'Søgte på nettet efter'],
  web_fetch: ['Henter', 'Hentede'],
  archive_brain_entry: ['Arkiverer', 'Arkiverede'],
  search_jarvis_brain: ['Søger i hukommelsen efter', 'Søgte i hukommelsen efter'],
  list_side_tasks: ['Viser flaggede opgaver', 'Viste flaggede opgaver'],
  flag_side_task: ['Flagger', 'Flaggede'],
  notify_user: ['Sender notifikation om', 'Sendte notifikation om'],
  schedule_task: ['Planlægger', 'Planlagde'],
  open_ui_panel: ['Åbner', 'Åbnede'],
  bash_session_run: ['Kører', 'Kørte'],
  search: ['Søger efter', 'Søgte efter'],
  find_files: ['Finder', 'Fandt'],
  recall: ['Genkalder', 'Genkaldte'],
  search_memory: ['Søger i hukommelsen efter', 'Søgte i hukommelsen efter'],
  memory_upsert_section: ['Opdaterer hukommelsen', 'Opdaterede hukommelsen'],
  central_query: ['Spørger centralen om', 'Spurgte centralen om'],
  discord_channel: ['Skriver i', 'Skrev i'],
  scout_agent: ['Sender en spejder efter', 'Sendte en spejder efter'],
  skill_invoke: ['Bruger', 'Brugte'],
  analyze_image: ['Analyserer', 'Analyserede'],
  schedule_self_wakeup: ['Sætter en påmindelse om', 'Satte en påmindelse om'],
  phone_adb_shell: ['Styrer telefonen', 'Styrede telefonen'],
  home_assistant: ['Styrer', 'Styrede'],
  load_more_tools: ['Henter flere værktøjer', 'Hentede flere værktøjer'],
}

/**
 * Kommandoens egentlige handling — ikke dens første ord.
 *
 * Bjørn 17/9-2026: linjen stod på «cd», fordi næsten hver kommando begynder
 * med `cd /media/projects/jarvis-v2 && …`. Serveren har samme oversættelse i
 * `_bash_hint`; den her gælder den tekst klienten selv bygger ud af
 * argumenterne mens de strømmer ind.
 */
const SCENE_LED = new Set(['cd', 'export', 'source', '.', 'set', 'conda',
  'for', 'while', 'until', 'if', 'then', 'else', 'elif', 'fi', 'do', 'done', 'echo', 'exit'])
const PRAEFIKS = new Set(['sudo', 'nohup', 'env', 'time', 'timeout', 'exec', 'command', 'xargs'])
/** Omdirigering og lignende er ikke kommandoens genstand: `cat > fil.py` handler om filen. */
const OPERATOR = /^(?:\d?[<>]{1,2}|&\d?|<<[-']?\w*)$/

export function kommandoEmne(cmd: string): string {
  const s = (cmd || '').trim().replace(/[\t\r ]+/g, ' ')
  if (!s) return ''
  // En subshell `(npx jest …)` er stadig `npx jest` — parentesen er ikke handlingen.
  for (const led of s.split(/&&|\|\||;|\||\n/).map((d) => d.trim().replace(/^\(+|\)+$/g, '').trim()).filter(Boolean)) {
    let ord = led.split(' ')
    while (ord.length && ord[0]!.includes('=') && !ord[0]!.startsWith('-')) ord = ord.slice(1)
    if (!ord.length || SCENE_LED.has(ord[0]!)) continue
    while (ord.length && PRAEFIKS.has(ord[0]!)) {
      ord = ord.slice(1)
      while (ord.length && (ord[0]!.startsWith('-') || /^\d+$/.test(ord[0]!))) ord = ord.slice(1)
    }
    if (!ord.length) continue
    const hoved = ord[0]!.split('/').pop() || ord[0]!
    const arg = ord.slice(1).find((o) => !o.startsWith('-') && !OPERATOR.test(o))
    const genstand = arg ? (arg.replace(/^["'`]|["'`]$/g, '').split('/').filter(Boolean).pop() ?? '') : ''
    return (genstand ? `${hoved} ${genstand}` : hoved).slice(0, 40)
  }
  // Kun en echo-overskrift: vis dens tekst uden dekorations-tegn.
  const foerste = s.split(/&&|\|\||;|\||\n/).map((d) => d.trim()).find((d) => /^echo\b/.test(d))
  if (foerste) {
    const titel = foerste.replace(/^echo\s*/, '').replace(/^["'=\s_-]+|["'=\s_-]+$/g, '').trim()
    return (titel || 'terminaloverskrift').slice(0, 40)
  }
  // Kun mappeskift og lignende — så er DET hvad der skete.
  return s.split(' ').slice(0, 2).join(' ').slice(0, 40)
}

/** Argument-nøgler der plejer at bære emnet, i prioriteret rækkefølge. */
const SUBJECT_KEYS = [
  'path', 'file_path', 'filepath', 'file', 'target', 'target_path',
  'command', 'cmd', 'query', 'q', 'pattern', 'title_substring', 'title', 'text', 'name', 'goal', 'focus',
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

export function subjectFromInput(input: Record<string, unknown> | undefined, partialJson?: string): string {
  if (input) {
    // En kommando læses som en kommando, ikke som en tekststump: «grep
    // tool_calls» frem for de første 48 tegn af `cd /media/… && grep …`.
    const cmd = input['command'] ?? input['cmd']
    if (typeof cmd === 'string' && cmd.trim()) return kommandoEmne(cmd)
    for (const key of SUBJECT_KEYS) {
      const v = input[key]
      if (typeof v === 'string' && v.trim()) return shorten(v)
    }
  }
  return subjectFromPartial(partialJson)
}

/**
 * Emnet fra argumenter der stadig STRØMMER ind — 1:1 med mobilens
 * `subjectFromArgs`.
 *
 * Bjørn 17/9-2026: linjen sagde «Kører bash…» hele kørslen igennem. `input` er
 * tomt til argumenterne er færdige; de ligger i `partialJson` imens. At vente
 * på det afsluttende } ville betyde at linjen står tom netop mens den er mest
 * interessant.
 */
export function subjectFromPartial(raw: string | undefined): string {
  const s = (raw || '').trim()
  if (!s) return ''
  try {
    const obj = JSON.parse(s) as Record<string, unknown>
    const cmd = obj['command'] ?? obj['cmd']
    if (typeof cmd === 'string' && cmd.trim()) return kommandoEmne(cmd)
    for (const key of SUBJECT_KEYS) {
      const v = obj[key]
      if (typeof v === 'string' && v.trim()) return shorten(v)
    }
  } catch {
    for (const key of SUBJECT_KEYS) {
      const m = new RegExp(`"${key}"\\s*:\\s*"((?:[^"\\\\]|\\\\.){1,200})`).exec(s)
      if (m?.[1]) {
        const v = m[1].replace(/\\n/g, ' ').replace(/\\"/g, '"')
        return key === 'command' || key === 'cmd' ? kommandoEmne(v) : shorten(v)
      }
    }
  }
  return ''
}

/**
 * Jarvis' egen linje for kaldet — `description`-feltet, Claude Desktops vej
 * (`zu`, læst 19/9-2026). Kun på kommando-værktøjerne, og kun når den er
 * brugbar: én linje, ikke bare kommandoen igen. Mens argumenterne strømmer,
 * tæller den først når feltet er LUKKET — ellers skiftede linjen pr. tegn.
 */
export function egenBeskrivelse(tool: string, input: Record<string, unknown> | undefined, partialJson?: string): string {
  if (grundnavn(tool) !== 'bash') return ''
  let d: unknown = input?.['description']
  let cmd: unknown = input?.['command']
  if (typeof d !== 'string' && partialJson) {
    const m = /"description"\s*:\s*"((?:[^"\\]|\\.)*)"/.exec(partialJson)
    if (m) {
      try { d = JSON.parse(`"${m[1]}"`) } catch { d = undefined }
    }
    const c = /"command"\s*:\s*"((?:[^"\\]|\\.)*)"/.exec(partialJson)
    if (c) {
      try { cmd = JSON.parse(`"${c[1]}"`) } catch { cmd = undefined }
    }
  }
  if (typeof d !== 'string') return ''
  const b = d.trim()
  if (!b || /[\n\r]/.test(b)) return ''
  const norm = (s: string) => s.replace(/\s+/g, ' ').trim().toLowerCase()
  if (typeof cmd === 'string' && norm(b) === norm(cmd)) return ''
  return b
}

/** `remember_this` returnerer et id ved succes. Et afsluttet kald uden resultat
 * er ukendt, og en tool-fejl kan være pakket ind i tekst i stedet for JSON. */
export function memoryWriteOutcome(status: ToolUse['status'], result?: string): 'running' | 'saved' | 'error' | 'unknown' {
  if (status === 'running' || !status) return 'running'
  if (status === 'error') return 'error'
  const raw = (result || '').trim()
  if (!raw) return 'unknown'
  if (/^\[Tool remember_this (?:error|blocked)/i.test(raw)) return 'error'
  try {
    const value = JSON.parse(raw) as Record<string, unknown>
    if (value.status === 'error' || value.status === 'blocked' || value.written === false) return 'error'
    if (value.status === 'ok' || value.written === true || (typeof value.id === 'string' && value.id)) return 'saved'
  } catch {
    // En formatteret tool-besked kan have tekst efter JSON-resultatet.
    if (/"status"\s*:\s*"error"|"written"\s*:\s*false/.test(raw)) return 'error'
    if (/"id"\s*:\s*"[^"]+"/.test(raw)) return 'saved'
  }
  return 'unknown'
}

function describeMemory(input: Record<string, unknown> | undefined, partialJson: string | undefined, status: ToolUse['status'], result?: string): string {
  // Mindeindholdet må ikke blive vist som en tilfældig uddragstekst i chatten.
  // Titlen er den korte, brugerrettede beskrivelse af det gemte.
  let rawTitle = input?.title
  if (typeof rawTitle !== 'string' && partialJson) {
    try { rawTitle = (JSON.parse(partialJson) as Record<string, unknown>).title } catch {
      const match = /"title"\s*:\s*"((?:[^"\\]|\\.)*)"/.exec(partialJson)
      if (match) {
        try { rawTitle = JSON.parse(`"${match[1]}"`) } catch { rawTitle = undefined }
      }
    }
  }
  const title = typeof rawTitle === 'string' ? shorten(rawTitle) : ''
  const what = title ? `“${title}” som minde` : 'et minde'
  switch (memoryWriteOutcome(status, result)) {
    case 'running': return `Gemmer ${what}…`
    case 'saved': return `Gemte ${what}`
    case 'error': return `Kunne ikke gemme ${what}`
    case 'unknown': return `Forsøgte at gemme ${what}`
  }
}

const NO_SUBJECT: Record<string, [string, string]> = {
  read_file: ['Læser en fil', 'Læste en fil'],
  write_file: ['Skriver en fil', 'Skrev en fil'],
  edit_file: ['Redigerer en fil', 'Redigerede en fil'],
  archive_brain_entry: ['Arkiverer et minde', 'Arkiverede et minde'],
  search_jarvis_brain: ['Søger i hukommelsen', 'Søgte i hukommelsen'],
  list_side_tasks: ['Viser flaggede opgaver', 'Viste flaggede opgaver'],
  flag_side_task: ['Flagger en opgave til senere', 'Flaggede en opgave til senere'],
  notify_user: ['Sender en notifikation', 'Sendte en notifikation'],
  schedule_task: ['Planlægger en opgave', 'Planlagde en opgave'],
  open_ui_panel: ['Åbner et panel', 'Åbnede et panel'],
}

export function describeTool(name: string, input: Record<string, unknown> | undefined, running: boolean, partialJson?: string, result?: string, status?: ToolUse['status']): string {
  const egen = egenBeskrivelse(name, input, partialJson)
  if (egen) return egen
  const tool = grundnavn(name) || 'værktøj'
  if (tool === 'remember_this') return describeMemory(input, partialJson, status ?? (running ? 'running' : 'done'), result)
  const verbs = VERBS[tool]
  if (!verbs) return running ? 'Bruger et værktøj…' : 'Brugte et værktøj'
  const [now, past] = verbs
  const verb = running ? now : past
  const subject = subjectFromInput(input, partialJson)
  if (subject) return `${verb} ${subject}${running ? '…' : ''}`
  const fallback = NO_SUBJECT[tool]?.[running ? 0 : 1]
  return fallback ? `${fallback}${running ? '…' : ''}` : running ? 'Bruger et værktøj…' : 'Brugte et værktøj'
}

const PLURAL: Record<string, [string, string]> = {
  edit_file: ['Redigerer', 'Redigerede'],
  operator_multi_edit: ['Redigerer', 'Redigerede'],
  write_file: ['Skriver', 'Skrev'],
  read_file: ['Læser', 'Læste'],
  verify_file_contains: ['Verificerer', 'Verificerede'],
  bash: ['Kører', 'Kørte'],
}

const UNIT: Record<string, [string, string]> = {
  edit_file: ['fil', 'filer'],
  operator_multi_edit: ['fil', 'filer'],
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
    return describeTool(t.name, t.input, (t.status ?? 'running') === 'running', t.partialJson, t.result, t.status)
  }

  const navne = new Set(tools.map((t) => grundnavn(t.name)))
  const counted = tools.reduce((sum, t) => sum + (countFromResult(t.result) ?? 0), 0)

  if (navne.size === 1) {
    const tool = grundnavn(tools[0]!.name)
    if (!PLURAL[tool]) return brugte(tools.length, running) + (running ? '…' : '')
    const [now, past] = PLURAL[tool]!
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
function blandetRunde(tools: ToolUse[], running: boolean): string {
  const orden: string[] = []
  const antal = new Map<string, number>()
  let ukendte = 0
  for (const i of tools) {
    const g = grundnavn(i.name)
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
