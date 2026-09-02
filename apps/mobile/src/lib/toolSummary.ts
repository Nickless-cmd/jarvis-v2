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

/** Verbum pr. værktøj: [nutid, datid]. */
const VERBS: Record<string, [string, string]> = {
  bash: ['Kører', 'Kørte'],
  read_file: ['Læser', 'Læste'],
  write_file: ['Skriver', 'Skrev'],
  edit_file: ['Redigerer', 'Redigerede'],
  verify_file_contains: ['Verificerer', 'Verificerede'],
  list_dir: ['Ser i', 'Så i'],
  grep: ['Søger efter', 'Søgte efter'],
  web_search: ['Søger på nettet efter', 'Søgte på nettet efter'],
  memory_search: ['Søger i hukommelsen efter', 'Søgte i hukommelsen efter'],
  memory_write: ['Husker', 'Huskede']
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
    for (const key of SUBJECT_KEYS) {
      const v = obj[key]
      if (typeof v === 'string' && v.trim()) return shorten(v)
    }
  } catch {
    // Streaming: argumenterne er endnu ikke gyldig JSON. Fisk værdien ud
    // alligevel — at vente på det afsluttende } ville betyde at linjen står
    // tom netop mens den er mest interessant.
    for (const key of SUBJECT_KEYS) {
      const m = new RegExp(`"${key}"\\s*:\\s*"([^"]{1,200})`).exec(s)
      if (m?.[1]) return shorten(m[1])
    }
  }
  return ''
}

export function describeTool(name: string, args: string, running: boolean): string {
  const tool = (name || '').trim() || 'værktøj'
  const [now, past] = VERBS[tool] ?? ['Kører', 'Kørte']
  const verb = running ? now : past
  const subject = subjectFromArgs(args)
  if (subject) return `${verb} ${subject}${running ? '…' : ''}`
  return `${verb} ${tool}${running ? '…' : ''}`
}

/** Persisterede rækker: «[tool_result:…] [bash]: output». */
export function describeToolResult(content: string): string {
  const m = /\[([a-z_0-9]+)\]\s*:/i.exec(content || '')
  const tool = m?.[1] ?? ''
  const [, past] = VERBS[tool] ?? ['Kører', 'Kørte']
  return tool ? `${past} ${tool}` : 'Brugte et værktøj'
}
