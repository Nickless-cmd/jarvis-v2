/**
 * Én linje der siger hvad Jarvis FAKTISK laver — ikke bare hvilket værktøj.
 *
 * «Kører edit_file…» fortæller ingenting. Codex-tråden viser i stedet målet:
 *
 *     </> Redigerede test_push_dispatcher.py
 *     </> Ændrede 16 filer
 *
 * Derfor trækkes emnet ud af værktøjets argumenter — sti, kommando, søgeord —
 * og verbet bøjes efter om det stadig kører. Kan der intet emne findes, falder
 * vi tilbage på værktøjsnavnet frem for at finde på noget.
 */

/**
 * Verbum pr. værktøj: [nutid, datid]. 1:1 med desk'ens `toolRound.ts` —
 * to flader der siger forskelligt om den samme tur er værre end én dårlig
 * linje (Bjørn 19/9-2026: telefonen skrev «Kørte cd /media/…» og «Kørte en
 * ting», hvor desk skrev «Kørte npm test»).
 */
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
  remember_this: ['Husker', 'Huskede'],
  archive_brain_entry: ['Arkiverer', 'Arkiverede'],
  bash_session_run: ['Kører', 'Kørte'],
  search: ['Søger efter', 'Søgte efter'],
  find_files: ['Finder', 'Fandt'],
  explore: ['Undersøger', 'Undersøgte'],
  recall: ['Genkalder', 'Genkaldte'],
  search_memory: ['Søger i hukommelsen efter', 'Søgte i hukommelsen efter'],
  memory_upsert_section: ['Opdaterer hukommelsen', 'Opdaterede hukommelsen'],
  central_query: ['Spørger centralen om', 'Spurgte centralen om'],
  channel: ['Skriver i', 'Skrev i'],
  scout_agent: ['Sender en spejder efter', 'Sendte en spejder efter'],
  skill_invoke: ['Bruger', 'Brugte'],
  analyze_image: ['Analyserer', 'Analyserede'],
  schedule_self_wakeup: ['Sætter en påmindelse om', 'Satte en påmindelse om'],
  phone_adb_shell: ['Styrer telefonen', 'Styrede telefonen'],
  home_assistant: ['Styrer', 'Styrede'],
  load_more_tools: ['Henter flere værktøjer', 'Hentede flere værktøjer']
}

/** `operator_read_file` og `read_file` er samme handling for læseren. */
export function grundnavn(name: string): string {
  return (name || '').trim().replace(/^operator_/, '')
}

/**
 * Kommandoens egentlige handling — ikke dens første ord. Næsten hver kommando
 * begynder med `cd /media/projects/jarvis-v2 && …`; linjen skal sige hvad der
 * skete bagefter. 1:1 med desk'ens `kommandoEmne`.
 */
const SCENE_LED = new Set(['cd', 'export', 'source', '.', 'set', 'conda'])
const PRAEFIKS = new Set(['sudo', 'nohup', 'env', 'time', 'timeout', 'exec', 'command', 'xargs'])
/** Omdirigering og lignende er ikke kommandoens genstand: `cat > fil.py` handler om filen. */
const OPERATOR = /^(?:\d?[<>]{1,2}|&\d?|<<[-']?\w*)$/

export function kommandoEmne(cmd: string): string {
  const s = (cmd || '').trim().replace(/\s+/g, ' ')
  if (!s) return ''
  // En subshell `(npx jest …)` er stadig `npx jest` — parentesen er ikke handlingen.
  for (const led of s.split(/&&|\|\||;/).map((d) => d.trim().replace(/^\(+|\)+$/g, '').trim()).filter(Boolean)) {
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
  // Kun mappeskift og lignende — så er DET hvad der skete.
  return s.split(' ').slice(0, 2).join(' ').slice(0, 40)
}

/** Argument-nøgler der plejer at bære emnet, i prioriteret rækkefølge. */
const SUBJECT_KEYS = [
  'path',
  'file_path',
  'filepath',
  'file',
  'target',
  'target_path',
  'command',
  'cmd',
  'query',
  'q',
  'pattern',
  'text',
  'name'
]

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

/** Find emnet i et (evt. ufuldstændigt) JSON-argument-objekt. */
export function subjectFromArgs(raw: string): string {
  const s = (raw || '').trim()
  if (!s) return ''
  try {
    const obj = JSON.parse(s) as Record<string, unknown>
    // En kommando læses som en kommando, ikke som en tekststump.
    const cmd = obj['command'] ?? obj['cmd']
    if (typeof cmd === 'string' && cmd.trim()) return kommandoEmne(cmd)
    for (const key of SUBJECT_KEYS) {
      const v = obj[key]
      if (typeof v === 'string' && v.trim()) return shorten(v)
    }
  } catch {
    // Streaming: argumenterne er endnu ikke gyldig JSON. Fisk værdien ud
    // alligevel — at vente på det afsluttende } ville betyde at linjen står
    // tom netop mens den er mest interessant.
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

export function describeTool(name: string, args: string, running: boolean): string {
  // `args` er en (evt. ufuldstændig) JSON-streng på mobilen.
  const egen = egenBeskrivelse(name, undefined, args)
  if (egen) return egen
  const tool = grundnavn(name) || 'værktøj'
  const [now, past] = VERBS[tool] ?? ['Kører', 'Kørte']
  const verb = running ? now : past
  const subject = subjectFromArgs(args)
  if (subject) return `${verb} ${subject}${running ? '…' : ''}`
  return `${verb} ${tool}${running ? '…' : ''}`
}

/** Persisterede rækker: «[tool_result:…] [bash]: output». */
export function describeToolResult(content: string): string {
  const m = /\[([a-z_0-9]+)\]\s*:/i.exec(content || '')
  const tool = grundnavn(m?.[1] ?? '')
  const [, past] = VERBS[tool] ?? ['Kører', 'Kørte']
  return tool ? `${past} ${tool}` : 'Brugte et værktøj'
}
