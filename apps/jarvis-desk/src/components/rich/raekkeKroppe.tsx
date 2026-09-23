/**
 * Kroppene i rækkevisningen — de få former, ikke de mange værktøjer.
 *
 * ## Hvorfor det er få former og ikke 366 visere
 *
 * Målt i DSH 22/9-2026: 63 værktøjer, 17 med dedikeret viser (~25 %), og
 * under dem kun 7 delte kort-primitiver. Vores fallback viser et kort
 * resumé og lader de rå data være tilgængelige ved behov.
 *
 * Vores værktøjskasse er 366 navne. Skrev vi en krop pr. værktøj, ville det
 * aldrig blive færdigt. Vi vælger derfor krop pr. RESULTATFORM, og lader
 * faldbacken bære halen. Det er den beslutning der gør visningen mulig.
 *
 * ## Etiketterne er engelske med vilje
 *
 * Bjørn 22/9-2026: «jeg kan godt li det står på eng. Altså rækkerne».
 * `TOOL_REGISTRY` er dansk og bruges af bobblevisningen — den rører vi ikke.
 * Rækkevisningen har derfor sin egen etiket-tabel og falder tilbage på
 * registrets label for alt vi ikke har navngivet.
 */
import { useEffect, useState, type ReactNode } from 'react'
import { codeToHtml } from 'shiki'
import { lookupTool, GAMLE_NAVNE } from '../../lib/toolRegistry'
import { hentAgentKald, agentIdFra, type AgentKald } from '../../lib/agentKald'
import type { ApiConfig } from '../../lib/api'

export type Familie = 'terminal' | 'diff' | 'fil' | 'skriv' | 'liste' | 'web' | 'spoergsmaal' | 'billede' | 'opgave' | 'fald'

interface Post { etiket: string; familie: Familie }

/**
 * Navnekortet — de navne der får en form.
 *
 * Familien følger RESULTATETS form, ikke værktøjets emne: et bash-kald giver
 * stdout + exit-kode (terminal), en søgning giver en hitliste (liste), en
 * skrivning giver en bekræftelse (skriv).
 *
 * Alt hvad der ikke står her falder til `fald` — den generiske feltliste. Det
 * er ikke en fejl: for små status-objekter (`central_query`, `daemon_status`,
 * `get_weather`, `read_self_state` …) ER feltlisten den rigtige form. At tvinge
 * dem ind i en anden familie ville gøre formen ringere, ikke bedre.
 *
 * ## Rettet 23/9-2026
 *
 * Kortet havde otte navne der ikke findes i registret (482 værktøjer):
 * `bash_session`, `operator_bash_session`, `memory_search`, `search_files`,
 * `glob`, `grep`, `ask_user`, `ask_question`. Det er værre end ubrugeligt — et
 * navn der ikke findes giver en form der LYVER, hvis navnet en dag tages i
 * brug til noget andet. Og de rigtige navne bag dem manglede: `bash_session_run`
 * er det fjerde mest brugte værktøj i systemet (1.492 kald) og fik hele tiden
 * den generiske dump, fordi nogen skrev navnet uden `_run`.
 *
 * Kilden til sandheden er `core/tools/simple_tools.py::get_tool_definitions`.
 * Denne liste skal holdes mod den — se vagt-testen i `raekkeKroppe.test.ts`.
 */
const KENDTE: Record<string, Post> = {
  // ── Terminal: stdout + exit-kode ──────────────────────────────────────
  bash: { etiket: 'Bash', familie: 'terminal' },
  operator_bash: { etiket: 'Bash', familie: 'terminal' },
  bash_session_run: { etiket: 'Bash', familie: 'terminal' },
  operator_bash_session_run: { etiket: 'Bash', familie: 'terminal' },
  bash_session_open: { etiket: 'Bash', familie: 'terminal' },
  operator_bash_session_open: { etiket: 'Bash', familie: 'terminal' },
  bash_session_close: { etiket: 'Bash', familie: 'terminal' },
  operator_bash_output: { etiket: 'Bash', familie: 'terminal' },
  operator_run_in_background: { etiket: 'Bash', familie: 'terminal' },
  operator_session_run: { etiket: 'Bash', familie: 'terminal' },
  phone_adb_shell: { etiket: 'Bash', familie: 'terminal' },
  // ── Læs ───────────────────────────────────────────────────────────────
  read_file: { etiket: 'Read', familie: 'fil' },
  operator_read_file: { etiket: 'Read', familie: 'fil' },
  // ── Skriv ─────────────────────────────────────────────────────────────
  write_file: { etiket: 'Write', familie: 'skriv' },
  operator_write_file: { etiket: 'Write', familie: 'skriv' },
  publish_file: { etiket: 'Write', familie: 'skriv' },
  remember_this: { etiket: 'Write', familie: 'skriv' },
  memory_upsert_section: { etiket: 'Write', familie: 'skriv' },
  send_telegram_message: { etiket: 'Write', familie: 'skriv' },
  notify_user: { etiket: 'Write', familie: 'skriv' },
  verify_file_contains: { etiket: 'Verify', familie: 'skriv' },
  // ── Redigering: diff ──────────────────────────────────────────────────
  edit_file: { etiket: 'Edit', familie: 'diff' },
  operator_edit_file: { etiket: 'Edit', familie: 'diff' },
  operator_multi_edit: { etiket: 'Edit', familie: 'diff' },
  // ── Liste: hitlister, tabeller, oversigter ────────────────────────────
  find_files: { etiket: 'Glob', familie: 'liste' },
  operator_glob: { etiket: 'Glob', familie: 'liste' },
  operator_grep: { etiket: 'Grep', familie: 'liste' },
  operator_list_dir: { etiket: 'List', familie: 'liste' },
  search: { etiket: 'Search', familie: 'liste' },
  search_memory: { etiket: 'Search', familie: 'liste' },
  search_sessions: { etiket: 'Search', familie: 'liste' },
  search_chat_history: { etiket: 'Search', familie: 'liste' },
  search_jarvis_brain: { etiket: 'Search', familie: 'liste' },
  semantic_search_code: { etiket: 'Search', familie: 'liste' },
  load_more_tools: { etiket: 'Search', familie: 'liste' },
  recall: { etiket: 'Search', familie: 'liste' },
  recall_memories: { etiket: 'Search', familie: 'liste' },
  smart_outline: { etiket: 'List', familie: 'liste' },
  git_log: { etiket: 'List', familie: 'liste' },
  read_chronicles: { etiket: 'List', familie: 'liste' },
  read_memory_topic: { etiket: 'List', familie: 'liste' },
  eventbus_recent: { etiket: 'List', familie: 'liste' },
  list_signal_surfaces: { etiket: 'List', familie: 'liste' },
  list_self_wakeups: { etiket: 'List', familie: 'liste' },
  list_agents: { etiket: 'List', familie: 'liste' },
  list_scheduled_tasks: { etiket: 'List', familie: 'liste' },
  list_side_tasks: { etiket: 'List', familie: 'liste' },
  // ── Web ───────────────────────────────────────────────────────────────
  web_search: { etiket: 'Search', familie: 'web' },
  web_fetch: { etiket: 'Fetch', familie: 'web' },
  operator_webfetch: { etiket: 'Fetch', familie: 'web' },
  web_scrape: { etiket: 'Fetch', familie: 'web' },
  // ── Spørgsmål ─────────────────────────────────────────────────────────
  pause_and_ask: { etiket: 'Ask', familie: 'spoergsmaal' },
  // ── Billede ───────────────────────────────────────────────────────────
  analyze_image: { etiket: 'Read image', familie: 'billede' },
  operator_screenshot: { etiket: 'Read image', familie: 'billede' },
  look_around: { etiket: 'Read image', familie: 'billede' },
  read_visual_memory: { etiket: 'Read image', familie: 'billede' },
  // ── Opgaveliste: én linje pr. punkt, ikke én pr. felt ─────────────────
  // `todo_set` havde 50 kald og `todo_update_status` 36 (23/9-2026) og faldt
  // til den generiske feltdump. Formen er linjer, ikke felter.
  todo_set: { etiket: 'Todo', familie: 'opgave' },
  todo_add: { etiket: 'Todo', familie: 'opgave' },
  todo_update_status: { etiket: 'Todo', familie: 'opgave' },
  todo_remove: { etiket: 'Todo', familie: 'opgave' },
  todo_list: { etiket: 'Todo', familie: 'opgave' },
}

/** Vælger etiket + familie for et værktøjsnavn.
 *
 * Et gammelt navn (se `GAMLE_NAVNE`) slås op på sit nuværende, så gemte ture
 * beholder deres form. `explore` er det vigtigste eksempel: den hedder
 * `scout_agent` nu (omdøbt 17/9-2026), og uden opslaget faldt hver gammel
 * spejder-tur til den generiske dump — selv om underagent-rækken stod klar
 * til at vise dens kald. Et dødt navn skal ud; et OMDØBT skal pege videre. */
export function postFor(navn: string): Post {
  const nu = GAMLE_NAVNE[navn] ?? navn
  return KENDTE[nu] ?? { etiket: lookupTool(nu).label, familie: 'fald' }
}

type Data = Record<string, unknown>
const objekt = (v: unknown): v is Data => typeof v === 'object' && v !== null && !Array.isArray(v)
const streng = (v: unknown): string => typeof v === 'string' ? v : ''
const pathNavn = (path: string): string => path.replace(/\\/g, '/').split('/').filter(Boolean).at(-1) || path

/** Serverens resultat kan være et JSON-objekt med en eller flere `result`-skaller. */
function pakUd(result: string | undefined): { værdi: unknown; ramme: Data | null } {
  if (!result) return { værdi: '', ramme: null }
  let værdi: unknown = result
  try { værdi = JSON.parse(result) } catch { return { værdi, ramme: null } }
  const ramme = objekt(værdi) ? værdi : null
  for (let i = 0; i < 3 && objekt(værdi) && 'result' in værdi; i++) {
    værdi = værdi.result
  }
  return { værdi, ramme }
}

function visTekst(v: unknown): string {
  if (typeof v === 'string') return v
  if (v === undefined || v === null) return ''
  return JSON.stringify(v, null, 2)
}

function fejlTekst(ramme: Data | null, værdi: unknown): string {
  return streng(ramme?.error) || (objekt(værdi) ? streng(værdi.error) : '')
}

/**
 * Exit-koden. Vores 366 værktøjer er ikke enige om feltnavnet — `bash_session`
 * har `exit_code`, den almindelige `bash` pakker et objekt med `stdout`, og de
 * fleste har slet ingen. Derfor leder vi efter flere navne og falder tilbage
 * på fejlflaget frem for at gætte et tal.
 *
 * Målt i DSH: `exit 0` tegner INGEN pille — kun ikke-nul markeres. Det er
 * halvdelen af forskellen mellem «rolig» og «terminal-agtig».
 */
export function exitKode(result: string | undefined, fejl: boolean): number {
  if (result) {
    try {
      const o = JSON.parse(result) as Record<string, unknown>
      const r = (o.result ?? o) as Record<string, unknown>
      for (const k of ['exit_code', 'returncode', 'exit_status', 'code']) {
        const v = r[k]
        if (typeof v === 'number') return v
      }
    } catch {
      // ikke JSON — proev tekstmarkoeren, som DSH bruger
    }
    const m = /\[exit code: (\d+)\]\s*$/.exec(result)
    if (m?.[1]) return Number(m[1])
  }
  return fejl ? 1 : 0
}

/** Stdout hvis resultatet er vores pakkede form; ellers hele strengen. */
export function udDel(result: string | undefined): string {
  if (!result) return ''
  const { værdi } = pakUd(result)
  if (objekt(værdi)) {
    const ud = [værdi.stdout, værdi.stderr].filter((x) => typeof x === 'string' && x).join('\n')
    if (ud) return ud
  }
  return visTekst(værdi)
}

/* ══ Delte resultatvisninger ════════════════════════════════════════════ */

export function Terminal({ cmd, ud, exit }: { cmd: string; ud: string; exit: number }) {
  return (
    <div className="rv-kort rv-term" data-exit={exit}>
      <div className="rv-kh">
        <span>{cmd}</span>
        <span className="rv-exit">exit code {exit}</span>
      </div>
      <pre>{ud}</pre>
    </div>
  )
}

export function Diff({ linjer }: { linjer: { k: 'add' | 'del' | 'ctx'; t: string }[] }) {
  return (
    <div className="rv-kort rv-diff">
      <pre>{linjer.map((l, i) => <span key={i} className="rv-l" data-k={l.k}>{l.t}{'\n'}</span>)}</pre>
    </div>
  )
}

export function IndUd({ ind, ud }: { ind: string; ud: string }) {
  return (
    <div className="rv-kort">
      <div className="rv-par"><div className="rv-mrk">IN</div><div className="rv-v">{ind}</div></div>
      <div className="rv-par"><div className="rv-mrk">OUT</div><div className="rv-v">{ud}</div></div>
    </div>
  )
}

function Fil({ path, tekst, meta }: { path: string; tekst: string; meta?: string }) {
  const linjer = tekst ? tekst.split('\n') : []
  return <div className="rv-kort rv-fil">
    <div className="rv-filH"><span>{pathNavn(path) || 'File'}</span><span className="rv-filM">{meta || `${linjer.length} lines`}</span></div>
    {tekst ? <FarvedeLinjer tekst={tekst} path={path} /> : <div className="rv-filTom">Empty file</div>}
  </div>
}

function Raadata({ ind, ud }: { ind: string; ud: string }) {
  return <details className="rv-raadata"><summary>Raw data</summary><IndUd ind={ind} ud={ud} /></details>
}

function Resultat({ tekst, ind, ud }: { tekst: ReactNode; ind: string; ud: string }) {
  return <div className="rv-resultat"><div className="rv-kort rv-resultatH">{tekst}</div><Raadata ind={ind} ud={ud} /></div>
}

function filSprog(path: string): string {
  const ext = pathNavn(path).split('.').at(-1)?.toLowerCase() || ''
  return ({ ts: 'typescript', tsx: 'tsx', js: 'javascript', jsx: 'jsx',
    html: 'html', css: 'css', json: 'json', py: 'python', md: 'markdown',
    yml: 'yaml', yaml: 'yaml', sh: 'bash' } as Record<string, string>)[ext] || 'text'
}

function FarvedeLinjer({ tekst, path }: { tekst: string; path: string }) {
  const lang = filSprog(path)
  const [html, setHtml] = useState<string | null>(null)
  useEffect(() => {
    let alive = true
    setHtml(null)
    if (lang !== 'text') {
      codeToHtml(tekst, { lang, themes: { light: 'github-light', dark: 'github-dark' }, defaultColor: false })
        .then((v) => { if (alive) setHtml(v) })
        .catch(() => { if (alive) setHtml(null) })
    }
    return () => { alive = false }
  }, [tekst, lang])
  if (html) return <div className="rv-filKode" data-lang={lang} dangerouslySetInnerHTML={{ __html: html }} />
  return <div className="rv-filKode" data-lang={lang}>{tekst.split('\n').map((linje, i) =>
    <div className="rv-filLinje" key={i}><span className="rv-filNr">{i + 1}</span><span>{linje || ' '}</span></div>
  )}</div>
}

function oversigt(v: unknown, fallback: string): ReactNode {
  if (Array.isArray(v)) return `${v.length} items`
  if (!objekt(v)) return (visTekst(v) || fallback).slice(0, 500)
  const poster = Object.entries(v).filter(([k]) => k !== 'status').slice(0, 8)
  if (poster.length === 0) return fallback
  return <dl className="rv-felter">{poster.map(([k, felt]) =>
    <div key={k}><dt>{k}</dt><dd>{Array.isArray(felt) ? `${felt.length} items`
      : objekt(felt) ? `${Object.keys(felt).length} fields` : visTekst(felt).slice(0, 240)}</dd></div>
  )}</dl>
}

export function Liste({ raekker }: { raekker: { p?: string; v: string }[] }) {
  return (
    <div className="rv-kort rv-liste">
      {raekker.map((r, i) => (
        <div key={i} className="rv-i">
          {r.p && <span className="rv-p">{r.p}</span>}
          <span>{r.v}</span>
        </div>
      ))}
    </div>
  )
}

export function Web({ traef }: { traef: { dom: string; titel: string }[] }) {
  return (
    <div className="rv-kort rv-web">
      {traef.map((t, i) => (
        <div key={i} className="rv-i">
          <div className="rv-dom">{t.dom}</div>
          <div className="rv-t">{t.titel}</div>
        </div>
      ))}
    </div>
  )
}

export function Spoergsmaal({ q, svar }: { q: string; svar: string }) {
  return (
    <div className="rv-kort rv-sp">
      <div className="rv-q">{q}</div>
      <div className="rv-a"><span className="rv-m">svar</span><span>{svar}</span></div>
    </div>
  )
}

export function Billede({ src, navn, meta }: { src?: string; navn: string; meta: string }) {
  return (
    <div className="rv-kort rv-bill">
      {src && <img src={src} alt={navn} />}
      <div>
        <div className="rv-n">{navn}</div>
        <div className="rv-m2">{meta}</div>
      </div>
    </div>
  )
}

/**
 * Underagentens egne kald. Hentes FØRST når rækken foldes ud — kroppen
 * monteres ikke før, så `useEffect` her er dovent af sig selv. Gjorde vi det
 * ved render, ville hver scout_agent-række i en lang tråd fyre et kald af
 * ved indlæsning; det er samme fejl som poll-stormen.
 */
/** Opgavelisten — ☑ færdig, ◐ i gang, ☐ venter.
 *
 * Formen er LINJER, ikke felter: en opgaveliste er en tilstand man læser ned
 * ad, og rækkefølgen er arbejdets — ikke alfabetisk. Den aktive linje
 * fremhæves, for den er dét man leder efter; uden fremhævningen læser listen
 * som en log man skal grave i.
 */
export function Opgaveliste({ poster }: { poster: { tekst: string; status: string }[] }) {
  const faerdige = poster.filter((p) => p.status === 'completed').length
  const igang = poster.filter((p) => p.status === 'in_progress').length
  return (
    <div className="rv-kort rv-opgave">
      <div className="rv-opgaveH">
        {faerdige} af {poster.length}
        {igang > 0 && <> · <span className="rv-opgaveNu">{igang} i gang</span></>}
      </div>
      {poster.map((p, i) => (
        <div key={i} className="rv-opgaveLinje" data-s={p.status}>
          <span className="rv-opgaveG" aria-hidden="true">
            {p.status === 'completed' ? '☑' : p.status === 'in_progress' ? '◐' : '☐'}
          </span>
          <span className="rv-opgaveT">{p.tekst}</span>
        </div>
      ))}
    </div>
  )
}

export function Underagent({
  agentId, resultat, config,
}: { agentId: string; resultat: string; config?: ApiConfig }) {
  const [kald, setKald] = useState<AgentKald[] | null>(null)
  const [fejl, setFejl] = useState(false)

  useEffect(() => {
    if (!config) return
    let levende = true
    hentAgentKald(config, agentId)
      .then((k) => { if (levende) setKald(k) })
      .catch(() => { if (levende) setFejl(true) })
    return () => { levende = false }
  }, [config, agentId])

  return (
    <div className="rv-underagent">
      <div className="rv-kort"><pre>{resultat}</pre></div>
      {/* Uden config kan vi ikke spoerge — sig det, frem for at vise en tom
          liste der ligner «agenten gjorde ingenting». */}
      {!config ? <div className="rv-uaTom">Ingen forbindelse — kan ikke hente agentens kald.</div>
       : fejl ? <div className="rv-uaTom">Agentens kald kunne ikke hentes.</div>
       : kald === null ? <div className="rv-uaTom">Henter agentens kald…</div>
       : kald.length === 0 ? <div className="rv-uaTom">Agenten kaldte ingen værktøjer.</div>
       : (
        <div className="rv-uaListe">
          <div className="rv-uaH">{kald.length} kald i underagenten</div>
          {kald.map((k, i) => (
            <div key={i} className="rv-uaKald" data-status={k.status || 'ok'}>
              <span className="rv-uaNavn">{k.tool_name || 'tool'}</span>
              <span className="rv-uaArg">{(k.arguments_json || '').slice(0, 120)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/** Vælg krop ud fra familie. Én indgang, så rækken ikke kender formerne. */
export function kropFor(
  navn: string,
  input: Record<string, unknown>,
  result: string | undefined,
  fejl: boolean,
  config?: ApiConfig,
): ReactNode {
  const { familie } = postFor(navn)
  // Underagent FOER familie-valget: `scout_agent` ville ellers falde i
  // faldbacken og vise raa JSON, mens agentens otte egne kald laa uroert i
  // `agent_tool_calls` med et endepunkt der allerede serverer dem.
  const agentId = agentIdFra(result)
  if (agentId) return <Underagent agentId={agentId} resultat={udDel(result)} config={config} />
  const ind = JSON.stringify(input, null, 2)
  const ud = udDel(result)
  const { værdi, ramme } = pakUd(result)
  const fejltekst = fejlTekst(ramme, værdi)
  const terminalMedOutput = familie === 'terminal' && objekt(værdi)
    && (typeof værdi.stdout === 'string' || typeof værdi.stderr === 'string') && !fejltekst
  if (!terminalMedOutput && (fejl || fejltekst || ['error', 'blocked', 'approval_needed', 'guard_blocked'].includes(streng(ramme?.status)))) {
    return <Resultat tekst={fejltekst || streng(ramme?.message) || 'The tool could not complete'} ind={ind} ud={result || ''} />
  }

  if (familie === 'terminal') {
    return <Terminal cmd={String(input.command ?? navn)} ud={ud} exit={exitKode(result, fejl)} />
  }
  if (familie === 'diff') {
    const oldText = streng(input.old_string) || streng(input.old_text)
    const newText = streng(input.new_string) || streng(input.new_text)
    const preview = objekt(værdi) ? streng(værdi.diff_preview) : ''
    // Operator-broen giver en reel diff_preview. Ellers kan vi vise det
    // udskiftningspar brugeren bad om, men kun efter et succesfuldt kald.
    const patch = preview || (ramme?.status === 'ok' && oldText ? `${oldText.split('\n').map((s) => '-' + s).join('\n')}\n${newText.split('\n').map((s) => '+' + s).join('\n')}` : '')
    if (!patch) return <Resultat tekst={oversigt(værdi, 'Edit pending')} ind={ind} ud={result || ''} />
    const linjer = patch.split('\n').filter((t) => !t.startsWith('--- ') && !t.startsWith('+++ ')).map((t) => ({
      k: t.startsWith('+') ? ('add' as const) : t.startsWith('-') ? ('del' as const) : ('ctx' as const),
      t: t.replace(/^[+-]/, ''),
    }))
    return <Diff linjer={linjer} />
  }
  if (familie === 'fil') {
    const path = streng(input.path) || streng(input.file_path) || streng(ramme?.path)
    const tekst = typeof værdi === 'string' ? værdi : objekt(værdi) ? streng(værdi.content) || streng(værdi.text) : ''
    const harFiltekst = result !== undefined && (typeof værdi === 'string'
      || (objekt(værdi) && ('content' in værdi || 'text' in værdi)))
    return harFiltekst ? <Fil path={path} tekst={tekst} /> : <Resultat tekst={oversigt(værdi, 'No file content')} ind={ind} ud={result || ''} />
  }
  if (familie === 'skriv') {
    const path = streng(input.path) || streng(input.file_path)
    const content = streng(input.content)
    const bytes = objekt(værdi) && typeof værdi.bytes_written === 'number' ? `${værdi.bytes_written} bytes` : ''
    if (content && ramme?.status === 'ok') return <Fil path={path} tekst={content} meta={bytes || 'Written'} />
    return <Resultat tekst={bytes || oversigt(værdi, 'Pending')} ind={ind} ud={result || ''} />
  }
  if (familie === 'liste') {
    const poster = Array.isArray(værdi) ? værdi : objekt(værdi) && Array.isArray(værdi.matches) ? værdi.matches : null
    if (poster) return <Liste raekker={poster.map((p) => objekt(p)
      ? { p: `${streng(p.file) || streng(p.path)}${typeof p.line === 'number' ? `:${p.line}` : ''}`, v: streng(p.text) || streng(p.name) || streng(p.summary) || streng(p.title) || streng(p.path) || 'Result' }
      : { v: visTekst(p) })} />
    return <Resultat tekst={oversigt(værdi, 'No matches')} ind={ind} ud={result || ''} />
  }
  if (familie === 'web') {
    const poster = Array.isArray(værdi) ? værdi : objekt(værdi) && Array.isArray(værdi.results) ? værdi.results : null
    if (poster) return <Web traef={poster.map((p) => objekt(p)
      ? { dom: streng(p.url) || streng(p.domain), titel: streng(p.title) || streng(p.snippet) || streng(p.text) }
      : { dom: '', titel: visTekst(p) })} />
    return <Resultat tekst={oversigt(værdi, 'No results')} ind={ind} ud={result || ''} />
  }
  if (familie === 'spoergsmaal') {
    const svar = typeof værdi === 'string' ? værdi : objekt(værdi) ? streng(værdi.answer) || streng(værdi.response) : ''
    return <Spoergsmaal q={streng(input.question) || streng(input.prompt)} svar={svar || (objekt(værdi) ? 'Answered' : ud)} />
  }
  if (familie === 'billede') {
    const sti = String(input.path ?? input.image_path ?? '')
    const maal = objekt(værdi) && typeof værdi.width === 'number' && typeof værdi.height === 'number'
      ? `${værdi.width} × ${værdi.height}` : ''
    const beskrivelse = objekt(værdi) ? streng(værdi.description) || streng(værdi.caption) : ''
    return <Billede navn={sti || navn} meta={[maal, beskrivelse].filter(Boolean).join(' · ') || (objekt(værdi) ? 'Image analyzed' : ud.slice(0, 120))} />
  }
  if (familie === 'opgave') {
    // Formen er `{count, todos:[{content, status}]}` for todo_set/todo_list og
    // `{todo:{…}}` for todo_update_status — begge læses som ÉN liste.
    const liste = objekt(værdi)
      ? (Array.isArray(værdi.todos) ? værdi.todos : objekt(værdi.todo) ? [værdi.todo] : null)
      : null
    if (liste) return <Opgaveliste poster={liste.map((p) => objekt(p)
      ? { tekst: streng(p.content) || streng(p.text) || streng(p.title) || visTekst(p), status: streng(p.status) || 'pending' }
      : { tekst: visTekst(p), status: 'pending' })} />
    return <Resultat tekst={oversigt(værdi, 'Opgaveliste')} ind={ind} ud={result || ''} />
  }
  return <Resultat tekst={oversigt(værdi, navn)} ind={ind} ud={result || ''} />
}
