/**
 * Hvilken FORM et værktøjskald har — ikke hvilket værktøj det er.
 *
 * ## Hvorfor former og ikke visere
 *
 * Desk målte det 22/9-2026: 63 værktøjer, 17 med en dedikeret viser (~25 %),
 * og under dem kun 7 delte kort-primitiver. Vores værktøjskasse er 366 navne.
 * Skrev vi én krop pr. værktøj, ville det aldrig blive færdigt. Vi vælger
 * derfor krop pr. RESULTATFORM, og lader faldbacken bære halen.
 *
 * Familien følger resultatets form: et bash-kald giver stdout + exit-kode
 * (terminal), en fil-læsning giver linjer (fil), en skrivning giver en diff.
 * Alt andet falder til rå tekst — og det er ikke en fejl: for små
 * status-objekter ER den rå tekst den rigtige form.
 *
 * ## Navnene skal findes
 *
 * Desk havde otte navne i sin tabel der ikke fandtes i registret (målt
 * 23/9-2026). Det er værre end ubrugeligt — et navn der ikke findes giver en
 * form der LYVER, hvis navnet en dag tages i brug til noget andet. Kilden til
 * sandheden er `core/tools/simple_tools.py::get_tool_definitions`, og
 * vagt-testen i `krop.test.ts` holder denne liste mod den.
 */

export type KropFamilie = 'terminal' | 'fil' | 'diff' | 'liste' | 'fald'

const TERMINAL = new Set([
  'bash', 'operator_bash',
  'bash_session_run', 'operator_bash_session_run',
  'bash_session_open', 'operator_bash_session_open',
  'bash_session_close', 'operator_bash_output',
  'operator_run_in_background', 'operator_session_run',
  'phone_adb_shell',
])

const FIL = new Set(['read_file', 'operator_read_file'])

const DIFF = new Set([
  'edit_file', 'operator_edit_file', 'operator_multi_edit',
  'write_file', 'operator_write_file',
])

/**
 * Liste: hitlister, tabeller, oversigter.
 *
 * Familien følger RESULTATETS form — en søgning giver en hitliste, en
 * fil-søgning giver stier, `git_status` giver ændrede filer. Formen er den
 * samme uanset værktøjets emne, så de hører i én krop.
 *
 * ## Hvorfor navnene står her og ikke udledes af resultatet alene
 *
 * Det ville være nærliggende at lade formen afgøre alt. Men `search_chat_history`
 * svarer `{status, count, results, text}` — og `text` er en streng VED SIDEN AF
 * listen. Form-reglen (`listenErIndholdet`) afviser netop det tilfælde, fordi
 * `path`/`text` ved siden af en liste betyder at objektet er formen. Uden
 * navne-tabellen ville historik-søgningen altså falde til rå tekst, selv om
 * listen ligger lige der. Navnet er den viden resultatet ikke bærer.
 *
 * Navnene er verificeret mod `core/tools/simple_tools.py::get_tool_definitions`
 * (485 værktøjer) — se vagt-testen i `krop.test.ts`. Et navn der ikke findes
 * giver en form der LYVER, hvis navnet en dag bruges til noget andet.
 */
export const LISTE_NAVNE = [
  // Filer og indhold
  'find_files', 'operator_glob', 'operator_grep', 'operator_list_dir',
  // Søgning: hitlister
  'search', 'search_memory', 'search_sessions', 'search_chat_history',
  'search_jarvis_brain', 'semantic_search_code', 'load_more_tools',
  'recall', 'recall_memories', 'smart_outline',
  // Git og processer: `{changes}`, `{diff}`, `{branches}`, `{processes}`
  'git_log', 'git_status', 'git_diff', 'git_branch',
  'process_list', 'process_tail', 'tail_log',
  // Oversigter og lister fra Centralen
  'central_query', 'read_chronicles', 'read_memory_topic', 'eventbus_recent',
  'list_signal_surfaces', 'list_self_wakeups', 'list_agents',
  'list_scheduled_tasks', 'list_side_tasks',
] as const

const LISTE = new Set<string>(LISTE_NAVNE)

/**
 * Et gammelt navn skal pege videre, ikke dø.
 *
 * Desk fandt det med `explore` → `scout_agent` (omdøbt 17/9-2026): uden
 * opslaget faldt hver gemt spejder-tur til den generiske dump, selv om formen
 * stod klar. Vi har endnu ikke et omdøbt navn i disse fire familier — tabellen
 * står her fordi den skal kunne tage imod det uden at nogen skal huske hvor.
 */
const GAMLE: Record<string, string> = {}

/** `operator_read_file` og `read_file` er samme handling for læseren. */
export function kropFor(navn: string): KropFamilie {
  const nu = GAMLE[navn] ?? navn
  if (TERMINAL.has(nu)) return 'terminal'
  if (FIL.has(nu)) return 'fil'
  if (DIFF.has(nu)) return 'diff'
  if (LISTE.has(nu)) return 'liste'
  return 'fald'
}

/* ══ Udtræk af resultatet ═══════════════════════════════════════════════ */

type Data = Record<string, unknown>
const objekt = (v: unknown): v is Data => typeof v === 'object' && v !== null && !Array.isArray(v)
const streng = (v: unknown): string => (typeof v === 'string' ? v : '')

/**
 * Intern hale fra serveren.
 *
 * Hver runde hæfter serveren en kort instruks på det SIDSTE værktøjs-resultat
 * (`visible_followup_results._NUDGE` — statisk og append-only, så
 * prompt-cachen ikke ryger). Den er skrevet til MODELLEN, men gemmes med i
 * turen. Uden klip fejler `JSON.parse` på halen, og kroppen dumper hele JSON'en
 * råt i stedet for stdout — og exit-koden kunne ikke læses.
 *
 * Mærket er `⟳`-parentesen; den skrives ingen andre steder i systemet.
 */
const INTERN_HALE = /\s*\(⟳[\s\S]*\)\s*$/

export function udenHale(tekst: string): string {
  return tekst.replace(INTERN_HALE, '')
}

/** Serverens resultat kan være et JSON-objekt med en eller flere `result`-skaller. */
export function pakUd(result: string | undefined): { vaerdi: unknown; ramme: Data | null } {
  if (!result) return { vaerdi: '', ramme: null }
  const renset = udenHale(result)
  let vaerdi: unknown = renset
  try {
    vaerdi = JSON.parse(renset)
  } catch {
    return { vaerdi, ramme: null }
  }
  const ramme = objekt(vaerdi) ? vaerdi : null
  for (let i = 0; i < 3 && objekt(vaerdi) && 'result' in vaerdi; i++) {
    vaerdi = vaerdi.result
  }
  return { vaerdi, ramme }
}

export function visTekst(v: unknown): string {
  if (typeof v === 'string') return v
  if (v === undefined || v === null) return ''
  return JSON.stringify(v, null, 2)
}

/**
 * Stdout hvis resultatet er vores pakkede form; ellers hele strengen.
 *
 * Vores værktøjer er ikke enige om feltnavnet — `bash_session` har `exit_code`,
 * den almindelige `bash` pakker et objekt med `stdout`, og de fleste har slet
 * ingen. Vi leder efter flere navne frem for at gætte ét.
 */
export function udDel(result: string | undefined): string {
  if (!result) return ''
  const { vaerdi } = pakUd(result)
  if (objekt(vaerdi)) {
    const ud = [vaerdi.stdout, vaerdi.stderr]
      .filter((x) => typeof x === 'string' && x)
      .join('\n')
    if (ud) return ud
  }
  return visTekst(vaerdi)
}

/**
 * Exit-koden — eller 0 når ingen kan findes.
 *
 * Vi læser `exit_code`/`returncode`/`exit_status`/`code` fra JSON, og falder
 * tilbage på tekstmærket `[exit code: N]` som serveren skriver når resultatet
 * ikke er JSON.
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
      // ikke JSON — prøv tekstmærket, som serveren bruger
    }
    const m = /\[exit code: (\d+)\]\s*$/.exec(udenHale(result))
    if (m?.[1]) return Number(m[1])
  }
  return fejl ? 1 : 0
}

/**
 * Filens indhold ud af et resultat.
 *
 * `read_file` svarer med filens tekst — nogle gange råt, nogle gange pakket i
 * et objekt. Vi leder efter de feltnavne huset bruger og falder tilbage til
 * hele strengen, så en fil altid kan læses uanset indpakningen.
 */
export function filTekst(result: string | undefined): string {
  if (!result) return ''
  const { vaerdi } = pakUd(result)
  if (objekt(vaerdi)) {
    for (const k of ['content', 'text', 'indhold', 'indhold_tekst']) {
      const v = streng(vaerdi[k])
      if (v) return v
    }
  }
  return visTekst(vaerdi)
}

/** Sidste led af en sti — til filnavnet over linjenumrene. */
export function filnavn(sti: string): string {
  return sti.replace(/\\/g, '/').split('/').filter(Boolean).at(-1) || sti
}

/* ══ Liste: hitlister, tabeller, oversigter ═════════════════════════════ */

/**
 * Den første liste i et resultat — uanset hvilken nøgle den er pakket i.
 *
 * `search_chat_history` kalder den `results`, `find_files` kalder den `files`,
 * `list_self_wakeups` kalder den `wakeups`, og `central_query` gemmer den bag
 * `data`. Leder vi efter ét bestemt navn, falder resten til rå tekst selv om
 * listen ligger lige der. Ét niveau ned dækker `data`-indpakningen; vi graver
 * ikke dybere, for et vilkårligt dybt gennemsyn ville gøre enhver struktur til
 * en liste.
 */
export function foersteListe(v: unknown): unknown[] | null {
  if (Array.isArray(v)) return v.length ? v : null
  if (!objekt(v)) return null
  for (const felt of Object.values(v)) if (Array.isArray(felt) && felt.length) return felt
  for (const felt of Object.values(v)) {
    if (!objekt(felt)) continue
    for (const indre of Object.values(felt)) if (Array.isArray(indre) && indre.length) return indre
  }
  return null
}

/**
 * Én linje for et listepunkt.
 *
 * De kendte felter først — `text`, `name`, `summary`, `title`, `prompt`,
 * `content`, `path`, `value` — fordi de bærer meningen. Et punkt uden nogen af
 * dem skal vise SINE felter (`k=v · k=v`), ikke ordet «Result»: en liste der
 * ikke viser noget er værre end ingen liste.
 *
 * Vi klipper ved 300 tegn. Desk viser hele teksten og lader CSS'en klippe, men
 * på en telefon er et `content`-felt på 4.000 tegn hele skærmen for ét punkt i
 * en hitliste. Et punkt er et punkt.
 */
const PUNKT_KLIP = 300

export function listeTekst(p: unknown): string {
  if (!objekt(p)) return visTekst(p)
  const kendt = streng(p.text) || streng(p.name) || streng(p.summary) || streng(p.title)
    || streng(p.prompt) || streng(p.content) || streng(p.path) || streng(p.value)
  const linje = kendt || Object.entries(p)
    .filter(([k, felt]) => k !== 'status' && !Array.isArray(felt) && !objekt(felt))
    .slice(0, 4)
    .map(([k, felt]) => `${k}=${visTekst(felt)}`)
    .join(' · ')
  const s = linje || visTekst(p)
  return s.length > PUNKT_KLIP ? `${s.slice(0, PUNKT_KLIP)}…` : s
}

/**
 * En streng der ER en liste — én linje pr. element.
 *
 * `git_log` (`{log}`), `git_status` (`{changes}`) og `git_diff` (`{diff}`)
 * sender én streng med linjer, ikke et array. Formen er en liste; værdien er
 * tekst. Kræver mindst to linjer, så et enkelt svar (`{summary: "ok"}`) ikke
 * bliver en liste med ét punkt.
 */
export function tekstLinjer(v: unknown): string[] | null {
  if (!objekt(v)) return null
  for (const [k, felt] of Object.entries(v)) {
    if (k === 'status' || typeof felt !== 'string') continue
    const linjer = felt.split('\n').map((s) => s.trimEnd()).filter((s) => s.trim() !== '')
    if (linjer.length > 1) return linjer
  }
  return null
}

/** Rækkerne en liste-krop tegner: `p` er præfikset (fx `fil.ts:42`), `v` linjen. */
export function listePoster(result: string | undefined): { p?: string; v: string }[] | null {
  if (!result) return null
  const { vaerdi } = pakUd(result)
  const poster = foersteListe(vaerdi)
  if (poster) {
    return poster.map((p) => objekt(p)
      ? {
        p: `${streng(p.file) || streng(p.path)}${typeof p.line === 'number' ? `:${p.line}` : ''}` || undefined,
        v: listeTekst(p),
      }
      : { v: visTekst(p) })
  }
  const linjer = tekstLinjer(vaerdi)
  if (linjer) return linjer.map((v) => ({ v }))
  return null
}

/* ══ Formen af resultatet — når navnet ikke er kendt ════════════════════ */

const OPTAELLINGER = new Set(['count', 'total', 'n', 'length', 'size', 'antal'])

/**
 * Er listen HELE indholdet — eller står der meningsfulde felter ved siden af?
 *
 * `{count, goals:[…]}`: `goals` ER indholdet, `count` er en optælling.
 * `{count, path, items:[…]}`: `path` er indhold ved siden af listen, så
 * objektet er formen — ikke listen. Uden den skelnen blev et ukendt struktureret
 * resultat til en liste af sine `items` og tabte `count`/`path`.
 *
 * ## Hvorfor der IKKE er en `pakUdEnkelt` her
 *
 * Desk har en hjælper der pakker `{wakeup: {…}}` ud til det indre objekt, så
 * feltlisten viser de seks felter i stedet for «wakeup | 6 fields». Mobilen
 * havde den også — indtil mutationsprøven viste at den **ikke kunne slås fra**:
 * ingen test fangede den, fordi den ingen forskel gør her. Mobilens `fald` er rå
 * tekst, ikke en feltliste, så udpakningen har intet at udpakke TIL. Død kode
 * der ikke kan måles hører ikke hjemme, og `listenErIndholdet` ser gennem
 * `data`-indpakningen alligevel (`foersteListe` graver ét niveau ned).
 */
function listenErIndholdet(v: Data): unknown[] | null {
  const liste = foersteListe(v)
  if (!liste) return null
  const vedSidenAf = Object.entries(v).filter(([k, f]) =>
    k !== 'status' && !OPTAELLINGER.has(k) && typeof f !== 'object' && typeof f !== 'boolean')
  return vedSidenAf.length ? null : liste
}

/**
 * Formen af RESULTATET — når værktøjets navn ikke står i nogen tabel.
 *
 * Familien følger resultatets form, ikke værktøjets emne: en liste ER en liste
 * uanset hvilket værktøj der sendte den. Det er den regel der løfter de
 * værktøjer ingen har skrevet en krop til — målt i desk 23/9-2026 havde 71 af
 * 92 værktøjer slet ingen form, fordi tabellen ikke blev holdt ajour.
 *
 * Kun former der er entydige: en liste er en liste, og `stdout`/`stderr` er en
 * terminal. Et fladt status-objekt (`get_weather`, `set_flag`) forbliver den
 * rå feltliste — det ER dens form, og en gættet form ville være ringere.
 */
export function formFamilie(result: string | null | undefined): KropFamilie {
  const { vaerdi } = pakUd(result ?? undefined)
  if (!objekt(vaerdi)) return 'fald'
  if (typeof vaerdi.stdout === 'string' || typeof vaerdi.stderr === 'string') return 'terminal'
  if (listenErIndholdet(vaerdi)) return 'liste'
  return 'fald'
}

/**
 * Familien for et KALD — navnet først, så resultatets form.
 *
 * Rækkefølgen er ikke ligegyldig. `search_chat_history` svarer
 * `{status, count, results, text}`, og `text` er en streng ved siden af listen —
 * så form-reglen alene ville afvise den. Navnet er den viden resultatet ikke
 * bærer, og formen er den viden tabellen ikke kan nå.
 */
export function kropForResult(navn: string, result: string | null | undefined): KropFamilie {
  const fraNavn = kropFor(navn)
  return fraNavn !== 'fald' ? fraNavn : formFamilie(result)
}

/**
 * Kan kroppen FAKTISK tegne noget?
 *
 * Familien siger hvilken FORM kaldet har — ikke at der er noget at vise i den.
 * `central_query` er `liste`, men svarer den med ren tekst, finder `listePoster`
 * hverken en liste eller tekst-linjer, og `Krop` tegner ingenting. Uden denne
 * gate lovede kaldsstedet en krop og tegnede en TOM ramme — indholdet forsvandt
 * helt, hvilket er værre end rå tekst. Målt: det var præcis hvad testen «et
 * meget langt svar klippes» fangede.
 *
 * Er svaret nej, falder kaldsstedet til den rå tekst. Vi viser aldrig mindre
 * end vi gjorde før.
 */
export function kanTegneKrop(familie: KropFamilie, result: string | null | undefined): boolean {
  const rå = result ?? ''
  if (!rå.trim()) return false
  if (familie === 'terminal') return udDel(rå).trim().length > 0
  if (familie === 'fil') return filTekst(rå).trim().length > 0
  if (familie === 'liste') return listePoster(rå) !== null
  return false
}
