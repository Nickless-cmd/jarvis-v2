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
import { safeImageSrc } from '../../lib/sanitize'
import { diffPar } from '../../lib/diffStat'
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
  // Git- og proces-værktøjerne sender LISTER — `{changes}`, `{diff}`,
  // `{branches}`, `{processes}`, `{wakeups}`. De faldt til den generiske
  // feltliste fordi de ikke stod her (målt 23/9-2026).
  git_status: { etiket: 'List', familie: 'liste' },
  git_diff: { etiket: 'List', familie: 'liste' },
  git_branch: { etiket: 'List', familie: 'liste' },
  process_list: { etiket: 'List', familie: 'liste' },
  process_tail: { etiket: 'List', familie: 'liste' },
  tail_log: { etiket: 'List', familie: 'liste' },
  central_query: { etiket: 'List', familie: 'liste' },
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

/**
 * Intern hale fra serveren.
 *
 * Hver runde hæfter serveren en kort instruks på det SIDSTE værktøjs-resultat
 * (`visible_followup_results._NUDGE` — statisk og append-only, så prompt-cachen
 * ikke ryger). Den er skrevet til MODELLEN, men gemmes med i turen. Så fejler
 * `JSON.parse` på halen: kroppen faldt tilbage til at dumpe hele JSON'en råt i
 * stedet for stdout, og `exitKode` kunne ikke læse tallet — den viste 0.
 *
 * Vi klipper den af ved visning. Mærket er `⟳`-parentesen; den skrives ingen
 * andre steder i systemet.
 */
const INTERN_HALE = /\s*\(⟳[\s\S]*\)\s*$/

function udenHale(tekst: string): string {
  return tekst.replace(INTERN_HALE, '')
}

/** Serverens resultat kan være et JSON-objekt med en eller flere `result`-skaller. */
function pakUd(result: string | undefined): { værdi: unknown; ramme: Data | null } {
  if (!result) return { værdi: '', ramme: null }
  const renset = udenHale(result)
  let værdi: unknown = renset
  try { værdi = JSON.parse(renset) } catch { return { værdi, ramme: null } }
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

/** Første meningsfulde linje af en rå tekst — til fejl uden struktur.
 *
 * En afvist handling fra broen (fx read-guarden) er ren TEKST, ikke JSON.
 * `fejlTekst` leder efter et `error`-felt og finder intet, så rækken stod med
 * «The tool could not complete» — mens den faktiske besked, der forklarer
 * HVORFOR kaldet blev afvist, lå ulæst inde i Raw data. Et JSON-dokument
 * springes over: første linje ville bare være `{`, og det siger ingenting.
 */
function foersteLinje(tekst: string): string {
  const linje = tekst.split('\n').map((s) => s.trim()).find(Boolean) || ''
  if (linje.startsWith('{') || linje.startsWith('[')) return ''
  return linje.length > 240 ? `${linje.slice(0, 240)}…` : linje
}

/** Er kaldet BEKRÆFTET af sit resultat?
 *
 * Gaten fandtes i forvejen, som `ramme?.status === 'ok'` — men den er for
 * SMAL: `operator_multi_edit` og `operator_edit_file` sender ingen status i
 * rammen. Deres bekræftelse ligger i selve resultatet: `replacements` er
 * antallet af ANVENDTE udskiftninger, `linjer_tilfoejet` er serverens målte
 * tal, `bytes_written` er filens nye størrelse. Alle tre findes først EFTER
 * handlingen, så de beviser den.
 *
 * Uden en bekræftelse må vi ikke bygge en diff af argumenterne: så viste vi
 * en ændring der ikke skete. Det er værre end et resumé, og det er hvad
 * testen «opfinder ikke en anvendt diff ud fra argumenter ved ukendt
 * resultat» vogter over.
 */
function bekræftet(ramme: Data | null, værdi: unknown): boolean {
  if (streng(ramme?.status) === 'ok') return true
  if (!objekt(værdi)) return false
  return typeof værdi.replacements === 'number'
    || typeof værdi.linjer_tilfoejet === 'number'
    || typeof værdi.bytes_written === 'number'
}

/**
 * ANSI-farvekoder i terminal-udskrift.
 *
 * `ls --color`, `git diff --color` og `grep --color` skriver SGR-sekvenser
 * (`\x1b[32m`) ind i stdout. Raekkevisningen lagde dem i en `<pre>` raa, saa
 * koderne stod som skrald midt i teksten. Vi OVERSAETTER dem i stedet for at
 * fjerne dem: farven ER information — den er hele grunden til at vaerktoejet
 * skrev den.
 *
 * Vi bygger React-spans, ikke HTML. Et fjendtligt vaerktoejsresultat kan
 * derfor ikke smugle markup ind; `dangerouslySetInnerHTML` bruges bevidst
 * ikke her, i modsaetning til Shiki-blokkene der selv escaper sin kode.
 *
 * Vi understoetter de 16 standardfarver samt fed/daempet. 256-farver og
 * baggrund falder tilbage til arvet farve — de ville kraeve en terminal vi
 * ikke er, og `git`, `ls` og `grep` bruger dem ikke i praksis.
 */
interface AnsiTilstand { fg: number | undefined; rgb: string | undefined; bold: boolean; dim: boolean }

const ANSI_TOM: AnsiTilstand = { fg: undefined, rgb: undefined, bold: false, dim: false }
// ESC er et kontroltegn — det ER definitionen af en ANSI-sekvens. Reglen
// findes for at fange utilsigtede kontroltegn i moenstre; her er det hele
// pointen.
// eslint-disable-next-line no-control-regex
const ANSI_RE = /\x1b\[([0-9;]*)m/g

function anvendSgr(koder: number[], t: AnsiTilstand): AnsiTilstand {
  const n: AnsiTilstand = { ...t }
  for (let i = 0; i < koder.length; i++) {
    const k = koder[i] ?? 0
    if (k === 0) { n.fg = undefined; n.rgb = undefined; n.bold = false; n.dim = false }
    else if (k === 1) n.bold = true
    else if (k === 2) n.dim = true
    else if (k === 22) { n.bold = false; n.dim = false }
    else if (k === 39) { n.fg = undefined; n.rgb = undefined }
    else if (k >= 30 && k <= 37) { n.fg = k - 30; n.rgb = undefined }
    else if (k >= 90 && k <= 97) { n.fg = k - 90 + 8; n.rgb = undefined }
    else if (k === 38 && koder[i + 1] === 2) {
      n.rgb = `rgb(${koder[i + 2] ?? 0}, ${koder[i + 3] ?? 0}, ${koder[i + 4] ?? 0})`
      n.fg = undefined
      i += 4
    }
  }
  return n
}

function ansiStykker(tekst: string): { t: string; s: AnsiTilstand }[] {
  const ud: { t: string; s: AnsiTilstand }[] = []
  let s = ANSI_TOM
  let sidst = 0
  ANSI_RE.lastIndex = 0
  let m: RegExpExecArray | null
  while ((m = ANSI_RE.exec(tekst)) !== null) {
    if (m.index > sidst) ud.push({ t: tekst.slice(sidst, m.index), s })
    const koder = (m[1] || '').split(';').map((x) => Number(x) || 0)
    s = koder.length === 1 && koder[0] === 0 ? ANSI_TOM : anvendSgr(koder, s)
    sidst = m.index + m[0].length
  }
  if (sidst < tekst.length) ud.push({ t: tekst.slice(sidst), s })
  return ud
}

function Ansi({ tekst }: { tekst: string }) {
  if (!tekst.includes('\x1b')) return <>{tekst}</>
  return <>{ansiStykker(tekst).map((d, i) => {
    const ren = d.s.fg === undefined && !d.s.rgb && !d.s.bold && !d.s.dim
    if (ren) return d.t
    return <span
      key={i}
      className={d.s.fg !== undefined ? `rv-ansi-${d.s.fg}` : undefined}
      style={{
        ...(d.s.rgb ? { color: d.s.rgb } : {}),
        ...(d.s.bold ? { fontWeight: 600 } : {}),
        ...(d.s.dim ? { opacity: 0.7 } : {}),
      }}
    >{d.t}</span>
  })}</>
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
      const o = JSON.parse(udenHale(result)) as Record<string, unknown>
      const r = (o.result ?? o) as Record<string, unknown>
      for (const k of ['exit_code', 'returncode', 'exit_status', 'code']) {
        const v = r[k]
        if (typeof v === 'number') return v
      }
    } catch {
      // ikke JSON — proev tekstmarkoeren, som DSH bruger
    }
    const m = /\[exit code: (\d+)\]\s*$/.exec(udenHale(result))
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

export function Terminal({ cmd, ud, exit, pending = false }: { cmd: string; ud: string; exit: number; pending?: boolean }) {
  return (
    <div className="rv-kort rv-term" data-exit={pending ? undefined : exit}>
      <div className="rv-kh">
        <span>{cmd}</span>
        {!pending && <span className="rv-exit">exit code {exit}</span>}
      </div>
      <pre {...(pending && !ud ? { 'data-pending': '' } : {})}>{ud ? <Ansi tekst={ud} /> : (pending ? 'Kører…' : '')}</pre>
    </div>
  )
}

export type DiffLinje = { k: 'add' | 'del' | 'ctx'; t: string }

/**
 * Diff-linjerne — med kode-farve naar vi kender sproget.
 *
 * Vi sender de RENE linjer (uden `+`/`−`) gennem Shiki i ét kald og saetter
 * linjens art som `data-k` via en transformer. To grunde til den vej: et kald
 * pr. linje ville vaere dyrt i en lang redigering, og markerne selv maa ikke
 * igennem grammatikken — `-` foran en linje er en operator for tokenizeren.
 *
 * Baggrunden for `add`/`del` laegges i CSS paa linjen, ikke paa tokenet, saa
 * rytmen i diffen bliver staaende oveni kode-farverne.
 */
export function Diff({ linjer, path }: { linjer: DiffLinje[]; path?: string }) {
  const ren = linjer.map((l) => l.t).join('\n')
  const lang = path ? filSprog(path) : 'text'
  const [html, setHtml] = useState<string | null>(null)
  // Afhaengigheden er en STRENG og ikke `linjer`: arrayet bygges paa ny ved
  // hver render af kaldsstedet, saa en array-reference i dep-listen ville
  // starte en ny highlighting i det uendelige.
  const noegle = linjer.map((l) => l.k + l.t).join('\u0000')
  useEffect(() => {
    let alive = true
    setHtml(null)
    if (lang !== 'text' && ren) {
      const ks = linjer.map((l) => l.k)
      codeToHtml(ren, {
        lang,
        themes: { light: 'github-light', dark: 'github-dark' },
        defaultColor: false,
        transformers: [{
          line(node, nr) {
            const props = node.properties as unknown as Record<string, unknown>
            props['data-k'] = ks[nr - 1] ?? 'ctx'
          },
        }],
      }).then((v) => { if (alive) setHtml(v) }).catch(() => { if (alive) setHtml(null) })
    }
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [noegle, lang])
  if (html) return <div className="rv-kort rv-diff" data-lang={lang} dangerouslySetInnerHTML={{ __html: html }} />
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

/**
 * Et minde der blev skrevet — hvad der blev husket, ikke id'et det fik.
 *
 * `remember_this` svarer kun med `{status, id}` og `memory_upsert_section`
 * med `{status, action}`. Selve indholdet findes KUN i argumenterne, saa
 * kroppen maa bygges af dem. Laeste vi resultatet, faldt raekken til
 * feltlisten og viste `id brn_…`: beviset paa skrivningen i stedet for det
 * der blev skrevet (Bjoern 23/9-2026: «det er jo ikk info jeg kan bruge til
 * noget»).
 *
 * Teksten klippes i CSS'en og ikke her — en hel MEMORY.md-sektion kan vaere
 * tusind tegn, og raekken skal ikke vokse med den.
 */
export function Minde({ titel, meta, tekst }: { titel: string; meta: string; tekst: string }) {
  return (
    <div className="rv-kort rv-minde">
      <div className="rv-mindeH">
        <span>{titel}</span>
        {meta && <span className="rv-mindeM">{meta}</span>}
      </div>
      {tekst && <div className="rv-mindeT">{tekst}</div>}
    </div>
  )
}

function Raadata({ ind, ud }: { ind: string; ud: string }) {
  return <details className="rv-raadata"><summary>Raw data</summary><IndUd ind={ind} ud={ud} /></details>
}

function inputFraStroem(raw: string | undefined): Data {
  if (!raw) return {}
  try {
    const parsed: unknown = JSON.parse(raw)
    return objekt(parsed) ? parsed : {}
  } catch { return {} }
}

/** `input` er tomt indtil kaldet afsluttes; den delvise JSON kan allerede bære kommandoen. */
function kommandoFraStroem(raw: string | undefined): string {
  const m = /"(?:command|cmd)"\s*:\s*"((?:\\.|[^"\\])*)/.exec(raw ?? '')
  if (!m?.[1]) return ''
  const tekst = m[1].replace(/\\$/, '')
  try { return JSON.parse(`"${tekst}"`) as string }
  catch { return tekst.replace(/\\n/g, '\n').replace(/\\"/g, '"').replace(/\\\\/g, '\\') }
}

function Resultat({ tekst, ind, ud }: { tekst: ReactNode; ind: string; ud: string }) {
  return <div className="rv-resultat"><div className="rv-kort rv-resultatH">{tekst}</div><Raadata ind={ind} ud={ud} /></div>
}

/**
 * Sproget bag en fil — navn FOER endelse.
 *
 * Endelsen alene dækkede kun halvdelen: `Makefile`, `Dockerfile`, `.env` og
 * `go.mod` har ingen brugbar endelse og faldt til `text`, altså ingen farve.
 * Navnekortet fanges først, fordi `Dockerfile.prod` har endelsen `.prod`.
 *
 * Kun sprog der findes i Shiki's bundt staar her. Et navn uden grammatik
 * kaster, `catch` sluger det, og filen vises ufarvet — det er tavst og ligner
 * en tilfaeldighed, saa vi holder listen konservativ.
 */
const NAVNE_SPROG: Record<string, string> = {
  dockerfile: 'dockerfile', containerfile: 'dockerfile', makefile: 'make',
  gemfile: 'ruby', rakefile: 'ruby', 'go.mod': 'go', 'go.sum': 'go',
  'cargo.toml': 'toml', 'cargo.lock': 'toml', 'pyproject.toml': 'toml',
  'package.json': 'json', 'tsconfig.json': 'json', '.gitignore': 'text',
  '.dockerignore': 'text', '.env': 'dotenv', '.editorconfig': 'ini',
  'nginx.conf': 'nginx', 'requirements.txt': 'text',
}

const ENDELSE_SPROG: Record<string, string> = {
  ts: 'typescript', tsx: 'tsx', mts: 'typescript', cts: 'typescript',
  js: 'javascript', jsx: 'jsx', mjs: 'javascript', cjs: 'javascript',
  html: 'html', htm: 'html', css: 'css', scss: 'scss', less: 'less',
  json: 'json', jsonc: 'jsonc', py: 'python', rb: 'ruby', go: 'go',
  rs: 'rust', java: 'java', kt: 'kotlin', swift: 'swift', c: 'c', h: 'c',
  cpp: 'cpp', cc: 'cpp', hpp: 'cpp', cs: 'csharp', php: 'php',
  md: 'markdown', yml: 'yaml', yaml: 'yaml', toml: 'toml', ini: 'ini',
  conf: 'ini', cfg: 'ini', sql: 'sql', sh: 'bash', bash: 'bash',
  zsh: 'bash', ps1: 'powershell', xml: 'xml', svg: 'xml', vue: 'vue',
  svelte: 'svelte', lua: 'lua', pl: 'perl', r: 'r', diff: 'diff',
  patch: 'diff', env: 'dotenv',
}

function filSprog(path: string): string {
  const navn = pathNavn(path).toLowerCase()
  const kendt = NAVNE_SPROG[navn]
  if (kendt) return kendt
  const ext = navn.split('.').at(-1) || ''
  return ENDELSE_SPROG[ext] || 'text'
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

/** Den første liste i et resultat — uanset hvilken nøgle den er pakket i.
 *
 * Målt 23/9-2026: `liste`-grenen ledte kun efter `matches`, så `process_list`
 * (`{processes}`), `list_self_wakeups` (`{wakeups}`) og `central_query`
 * (`{data:{items}}`) faldt alle til den generiske feltliste. Listen FANDTES —
 * grenen kunne bare ikke se den, fordi den lå bag en nøgle den ikke kendte.
 *
 * Ét niveau ned dækker `data`-indpakningen. Vi graver ikke dybere: et vilkårligt
 * dybt gennemsyn ville gøre enhver struktur til en liste. */
function foersteListe(v: unknown): unknown[] | null {
  if (Array.isArray(v)) return v.length ? v : null
  if (!objekt(v)) return null
  for (const felt of Object.values(v)) if (Array.isArray(felt) && felt.length) return felt
  for (const felt of Object.values(v)) {
    if (!objekt(felt)) continue
    for (const indre of Object.values(felt)) if (Array.isArray(indre) && indre.length) return indre
  }
  return null
}

/** En streng der ER en liste — én linje pr. element.
 *
 * `git_log` (`{log}`), `git_status` (`{changes}`) og `git_diff` (`{diff}`)
 * sender én streng med linjer, ikke et array. Formen er en liste; værdien er
 * tekst. Kræver mindst to linjer, så et enkelt svar (`{summary: "ok"}`) ikke
 * bliver en liste med ét punkt. */
function tekstLinjer(v: unknown): string[] | null {
  if (!objekt(v)) return null
  for (const [k, felt] of Object.entries(v)) {
    if (k === 'status' || typeof felt !== 'string') continue
    const linjer = felt.split('\n').map((s) => s.trimEnd()).filter((s) => s.trim() !== '')
    if (linjer.length > 1) return linjer
  }
  return null
}

/** Én linje for et listepunkt — de kendte felter først, ellers en kompakt
 * nøgle/værdi-sammenfatning.
 *
 * Målt 23/9-2026: faldt til `'Result'` for alt hvad der ikke bar
 * `text/name/summary/title/path`. `list_self_wakeups` bærer `prompt` og
 * `central_query` bærer `id`/`kind` — begge stod som «Result», altså en liste
 * der ikke viste noget. Et punkt uden genkendte felter skal vise SINE felter,
 * ikke et ord. */
function listeTekst(p: unknown): string {
  if (!objekt(p)) return visTekst(p)
  const kendt = streng(p.text) || streng(p.name) || streng(p.summary) || streng(p.title)
    || streng(p.prompt) || streng(p.content) || streng(p.path) || streng(p.value)
  if (kendt) return kendt
  const par = Object.entries(p)
    .filter(([k, felt]) => k !== 'status' && !Array.isArray(felt) && !objekt(felt))
    .slice(0, 4)
    .map(([k, felt]) => `${k}=${visTekst(felt)}`)
  return par.join(' · ') || visTekst(p)
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
  const [hentet, setHentet] = useState<string | null>(null)

  // En lokal sti kan ikke vises direkte: CSP'en blokerer `file://`, og
  // renderer'en har ingen disk-adgang. Main læser filen og giver en data-URL
  // tilbage (electron/billede.ts). Effekten kører først når rækken foldes ud,
  // fordi kroppen monteres der — så billedet koster intet før man ser det.
  useEffect(() => {
    setHentet(null)
    if (!src?.startsWith('/')) return
    const bro = (window as unknown as {
      jarvisDesk?: { billede?: { laes: (s: string) => Promise<string | null> } }
    }).jarvisDesk?.billede
    if (!bro) return // browser-fane: ingen bro, så navnet står alene
    let afbrudt = false
    void bro.laes(src).then((url) => { if (!afbrudt && url) setHentet(url) }).catch(() => { /* navnet står */ })
    return () => { afbrudt = true }
  }, [src])

  // En data-URL fra main er allerede betroet. Alt andet går gennem sanitizeren,
  // så et fjendtligt tool-resultat ikke kan smugle en kilde ind i <img>.
  const vis = src?.startsWith('/') ? hentet : safeImageSrc(src ?? '')
  return (
    <div className="rv-kort rv-bill">
      {vis && <img src={vis} alt={navn} />}
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
  inputRaa: Record<string, unknown>,
  resultRaa: string | undefined,
  fejl: boolean,
  config?: ApiConfig,
  live?: { partialJson?: string; running?: boolean },
): ReactNode {
  const input = { ...inputFraStroem(live?.partialJson), ...inputRaa }
  // Nudgen fra serveren er skrevet til MODELLEN, men gemmes med i turen (se
  // `udenHale`). Renser vi ikke her, lækker den ud i de otte steder der sender
  // resultatet råt videre til `Resultat` — og hvor JSON'en ikke kan parses,
  // dumper kroppen hele dokumentet i stedet for stdout.
  const result = resultRaa === undefined ? undefined : udenHale(resultRaa)
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
    const besked = fejltekst || streng(ramme?.message) || foersteLinje(ud)
    return <Resultat tekst={besked || 'The tool could not complete'} ind={ind} ud={result || ''} />
  }

  if (familie === 'terminal') {
    const cmd = streng(input.command) || streng(input.cmd) || kommandoFraStroem(live?.partialJson) || 'Klargør kommando…'
    return <Terminal cmd={cmd} ud={ud} exit={exitKode(result, fejl)} pending={live?.running} />
  }
  if (familie === 'diff') {
    const preview = objekt(værdi) ? streng(værdi.diff_preview) : ''
    // Operator-broen giver en reel diff_preview. Ellers bygger vi den af
    // kaldets EGNE par — samme kilde som `diffStat` regner «+N −M» af, så
    // linjen og kroppen ikke kan vise to forskellige ting om samme kald.
    //
    // Før ledte vi kun efter `old_string`/`old_text` på TOPNIVEAU og krævede
    // `ramme.status === 'ok'`. `multi_edit` bærer sine par i `edits[]`, og
    // `operator_*` sender ingen status i rammen — så grenen faldt i gennem
    // HVER gang og viste resultatets metadata (replacements, edits,
    // strategies) i stedet for ændringen. Bjørn 23/9-2026: «det er jo ikk
    // info jeg kan bruge til noget».
    //
    // Bekræftelsen er nu bredere (se `bekræftet`) — men den er der stadig.
    const par = diffPar(navn, input)
    const hunk = (p: { gammel: string; ny: string }) => [
      ...(p.gammel ? p.gammel.split('\n').map((s) => '-' + s) : []),
      ...(p.ny ? p.ny.split('\n').map((s) => '+' + s) : []),
    ].join('\n')
    const patch = preview || (par && bekræftet(ramme, værdi) ? par.map(hunk).join('\n\n') : '')
    if (!patch) return <Resultat tekst={oversigt(værdi, 'Edit pending')} ind={ind} ud={result || ''} />
    const linjer = patch.split('\n').filter((t) => !t.startsWith('--- ') && !t.startsWith('+++ ')).map((t) => ({
      k: t.startsWith('+') ? ('add' as const) : t.startsWith('-') ? ('del' as const) : ('ctx' as const),
      t: t.replace(/^[+-]/, ''),
    }))
    return <Diff linjer={linjer} path={streng(input.path) || streng(input.file_path) || streng(input.target_path) || streng(ramme?.path)} />
  }
  if (familie === 'fil') {
    const path = streng(input.path) || streng(input.file_path) || streng(ramme?.path)
    const tekst = typeof værdi === 'string' ? værdi : objekt(værdi) ? streng(værdi.content) || streng(værdi.text) : ''
    const harFiltekst = result !== undefined && (typeof værdi === 'string'
      || (objekt(værdi) && ('content' in værdi || 'text' in værdi)))
    return harFiltekst ? <Fil path={path} tekst={tekst} /> : <Resultat tekst={oversigt(værdi, 'No file content')} ind={ind} ud={result || ''} />
  }
  if (familie === 'skriv') {
    const path = streng(input.path) || streng(input.file_path) || streng(ramme?.path)
    const content = streng(input.content) || streng(input.file_text)
    const bytes = objekt(værdi) && typeof værdi.bytes_written === 'number' ? `${værdi.bytes_written} bytes` : ''
    // Et MINDES resultat baerer kun beviset — `{id}` for `remember_this`,
    // `{action}` for `memory_upsert_section`. Indholdet staar i argumenterne,
    // og uden denne gren faldt raekken til feltlisten og viste `id brn_…`.
    const mindeNavn = GAMLE_NAVNE[navn] ?? navn
    if (mindeNavn === 'remember_this' || mindeNavn === 'memory_upsert_section') {
      const titel = streng(input.title) || streng(input.heading)
      const tekst = streng(input.content) || streng(input.text)
      if (titel && tekst && bekræftet(ramme, værdi)) {
        const meta = [streng(input.kind), streng(input.domain)].filter(Boolean).join(' · ')
        return <Minde titel={titel} meta={meta} tekst={tekst} />
      }
    }
    // Samme smalle gate som diffen: `operator_write_file` sender ingen status
    // i rammen, så `status === 'ok'` holdt aldrig og filens indhold blev
    // aldrig vist — kun «1941 bytes» og rå metadata. `bekræftet` tager imod
    // `bytes_written` som bevis i stedet. Kravet om en STI holder
    // `publish_file` og `memory_upsert_section` ude: de bærer også `content`,
    // men skriver ikke en fil, og deres rigtige form er feltlisten.
    if (content && path && bekræftet(ramme, værdi)) return <Fil path={path} tekst={content} meta={bytes || 'Written'} />
    return <Resultat tekst={bytes || oversigt(værdi, 'Pending')} ind={ind} ud={result || ''} />
  }
  if (familie === 'liste') {
    const poster = foersteListe(værdi)
    if (poster) return <Liste raekker={poster.map((p) => objekt(p)
      ? { p: `${streng(p.file) || streng(p.path)}${typeof p.line === 'number' ? `:${p.line}` : ''}`, v: listeTekst(p) }
      : { v: visTekst(p) })} />
    // Tekst der ER en liste: `git log`, `git status --short` og `git diff`
    // sender én streng med linjer. Uden dette faldt de til feltlisten.
    const linjer = tekstLinjer(værdi)
    if (linjer) return <Liste raekker={linjer.map((v) => ({ v }))} />
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
    // Stien ligger i RESULTATET for fx `operator_screenshot` — ikke i input.
    // Læste vi kun input, faldt kroppen til et navn uden billede.
    const fraInput = String(input.path ?? input.image_path ?? '')
    const fraUd = objekt(værdi) ? streng(værdi.path) || streng(værdi.image_path) : ''
    const sti = fraInput || fraUd
    const maal = objekt(værdi) && typeof værdi.width === 'number' && typeof værdi.height === 'number'
      ? `${værdi.width} × ${værdi.height}` : ''
    const beskrivelse = objekt(værdi) ? streng(værdi.description) || streng(værdi.caption) : ''
    return <Billede src={sti} navn={sti || navn} meta={[maal, beskrivelse].filter(Boolean).join(' · ') || (objekt(værdi) ? 'Image analyzed' : ud.slice(0, 120))} />
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
